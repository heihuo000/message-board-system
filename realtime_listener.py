#!/usr/bin/env python3
"""
留言簿实时监听器 - 前台运行
用于 AI 在前台监听留言簿变化，第一时间获取新消息并回复

特点:
- 前台运行，AI 可以直接控制
- 检测到新消息立即返回
- 支持交互式回复
- 类似交流群的实时体验

使用方法:
    python3 realtime_listener.py --client-id my_ai
"""
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))
from message_sdk import MessageBoardClient


class RealtimeListener:
    """实时监听器 - 前台运行"""
    
    def __init__(self, client_id: str, db_path: Optional[str] = None):
        """
        初始化监听器
        
        Args:
            client_id: 客户端 ID
            db_path: 数据库路径
        """
        if db_path:
            self.client = MessageBoardClient(client_id, db_path)
        else:
            self.client = MessageBoardClient(client_id)
        
        self.client_id = client_id
        self.running = True
        self.check_interval = 2  # 2 秒检查一次
        self.processed_ids = set()
    
    def log(self, message: str, emoji: str = "💬"):
        """格式化输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] {emoji} {message}")
        print("-" * 60)
    
    def check_new_messages(self) -> List[Dict]:
        """
        检查新消息
        
        Returns:
            新消息列表
        """
        try:
            messages = self.client.read_unread(limit=10)
            
            # 过滤：排除自己的消息和已处理的消息
            new_messages = [
                msg for msg in messages 
                if msg['sender'] != self.client_id 
                and msg['id'] not in self.processed_ids
            ]
            
            return new_messages
        
        except Exception as e:
            print(f"❌ 检查消息失败：{e}")
            return []
    
    def format_message(self, msg: Dict) -> str:
        """格式化消息用于显示"""
        priority_emoji = {
            "urgent": "🔴",
            "high": "🟠",
            "normal": "⚪"
        }.get(msg.get('priority', 'normal'), "⚪")
        
        time_str = datetime.fromtimestamp(msg['timestamp']).strftime("%H:%M:%S")
        
        return (
            f"{priority_emoji} [{time_str}] {msg['sender']}:\n"
            f"   {msg['content']}\n"
            f"   ID: {msg['id'][:8]}..."
        )
    
    def wait_for_reply(self, original_msg_id: str, timeout: int = 60) -> Optional[Dict]:
        """
        等待特定消息的回复
        
        Args:
            original_msg_id: 原消息 ID
            timeout: 超时时间（秒）
        
        Returns:
            回复消息，超时返回 None
        """
        print(f"\n⏳ 等待回复（最多{timeout}秒）...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            messages = self.client.read_unread(limit=10)
            
            for msg in messages:
                if msg.get('reply_to') == original_msg_id:
                    return msg
            
            time.sleep(1)
        
        return None
    
    def run_interactive(self):
        """
        交互式运行模式
        
        AI 可以在这个循环中：
        1. 接收新消息
        2. 生成回复
        3. 发送回复
        4. 继续监听
        """
        print("=" * 60)
        print("📡 留言簿实时监听器")
        print("=" * 60)
        print(f"客户端 ID: {self.client_id}")
        print("按 Ctrl+C 停止")
        print("=" * 60)
        
        while self.running:
            try:
                # 检查新消息
                new_messages = self.check_new_messages()
                
                if new_messages:
                    print("\n" + "=" * 60)
                    print(f"📬 收到 {len(new_messages)} 条新消息:")
                    print("=" * 60)
                    
                    for msg in new_messages:
                        # 显示消息
                        print(self.format_message(msg))
                        
                        # 标记为已处理
                        self.processed_ids.add(msg['id'])
                    
                    print("\n💡 提示：现在可以回复这些消息")
                    print("   使用 client.send(reply, reply_to=msg_id) 发送回复")
                    print("=" * 60)
                
                # 短暂等待后继续检查
                time.sleep(self.check_interval)
            
            except KeyboardInterrupt:
                print("\n\n⚠️  用户中断，停止监听")
                self.running = False
                break
            
            except Exception as e:
                print(f"\n❌ 错误：{e}")
                time.sleep(5)
        
        print("\n" + "=" * 60)
        print("👋 监听器已停止")
        print("=" * 60)
    
    def run_once(self, timeout: int = 30) -> Optional[Dict]:
        """
        运行一次检查，等待新消息
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            第一条新消息，超时返回 None
        """
        print(f"⏳ 等待新消息（最多{timeout}秒）...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            new_messages = self.check_new_messages()
            
            if new_messages:
                msg = new_messages[0]
                print(f"\n✅ 收到新消息:")
                print(self.format_message(msg))
                return msg
            
            time.sleep(1)
        
        print("\n⏰ 超时，未收到新消息")
        return None


# ==================== 便捷函数 ====================

def listen_and_reply(
    client_id: str,
    reply_generator=None,
    timeout: int = 300
):
    """
    监听并自动回复
    
    Args:
        client_id: 客户端 ID
        reply_generator: 回复生成函数，接收消息字典，返回回复字符串
        timeout: 总超时时间（秒）
    """
    listener = RealtimeListener(client_id)
    
    print(f"🚀 开始监听并自动回复（超时：{timeout}秒）")
    
    start_time = time.time()
    reply_count = 0
    
    while time.time() - start_time < timeout:
        msg = listener.run_once(timeout=60)
        
        if msg:
            # 生成回复
            if reply_generator:
                reply = reply_generator(msg)
            else:
                # 默认回复逻辑
                content = msg['content'].lower()
                if any(kw in content for kw in ['你好', 'hello', 'hi']):
                    reply = f"你好 {msg['sender']}！"
                elif '?' in msg['content'] or '？' in msg['content']:
                    reply = "好问题！让我想想..."
                elif any(kw in content for kw in ['谢谢', '感谢']):
                    reply = "不客气！"
                else:
                    reply = f"收到：{msg['content'][:50]}"
            
            # 发送回复
            reply_id = listener.client.send(reply, reply_to=msg['id'])
            print(f"✅ 已回复：{reply[:50]}...")
            reply_count += 1
    
    print(f"\n📊 统计：共回复 {reply_count} 条消息")


# ==================== 命令行接口 ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="留言簿实时监听器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 交互式监听
    python3 realtime_listener.py --client-id my_ai
    
    # 监听并自动回复
    python3 realtime_listener.py --client-id my_ai --auto-reply
    
    # 等待单条消息
    python3 realtime_listener.py --client-id my_ai --once
        """
    )
    
    parser.add_argument(
        "--client-id", "-c",
        required=True,
        help="客户端 ID"
    )
    
    parser.add_argument(
        "--auto-reply", "-a",
        action="store_true",
        help="自动回复模式"
    )
    
    parser.add_argument(
        "--once", "-o",
        action="store_true",
        help="只等待一条消息"
    )
    
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=300,
        help="超时时间（秒）"
    )
    
    args = parser.parse_args()
    
    listener = RealtimeListener(args.client_id)
    
    if args.once:
        # 只等待一条消息
        msg = listener.run_once(timeout=args.timeout)
        if msg:
            print("\n💡 可以使用以下代码回复:")
            print(f"   client.send('你的回复', reply_to='{msg['id']}')")
    elif args.auto_reply:
        # 自动回复模式
        listen_and_reply(args.client_id, timeout=args.timeout)
    else:
        # 交互式模式
        listener.run_interactive()
