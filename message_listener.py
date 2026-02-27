#!/usr/bin/env python3
"""
留言簿监听守护进程
持续监听留言簿变化，第一时间自动回复

使用方法:
    python3 message_listener.py --client-id my_ai
"""
import sys
import time
import signal
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))
from message_sdk import MessageBoardClient


class MessageListener:
    """留言簿监听器"""
    
    def __init__(
        self,
        client_id: str,
        check_interval: int = 3,
        auto_reply: bool = True,
        db_path: Optional[str] = None
    ):
        """
        初始化监听器
        
        Args:
            client_id: 客户端 ID
            check_interval: 检查间隔（秒）
            auto_reply: 是否自动回复
            db_path: 数据库路径
        """
        self.client_id = client_id
        self.check_interval = check_interval
        self.auto_reply = auto_reply
        
        if db_path:
            self.client = MessageBoardClient(client_id, db_path)
        else:
            self.client = MessageBoardClient(client_id)
        
        self.running = False
        self.processed_ids = set()  # 已处理的消息 ID
        self.max_history = 100  # 最多保留的已处理 ID 数
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        print("\n⚠️  收到停止信号，正在关闭...")
        self.running = False
    
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️",
            "MESSAGE": "💬"
        }.get(level, "•")
        
        print(f"[{timestamp}] {emoji} {message}")
    
    def generate_reply(self, message: Dict) -> Optional[str]:
        """
        生成回复
        
        Args:
            message: 消息字典
        
        Returns:
            回复内容，如果不需要回复则返回 None
        """
        sender = message['sender']
        content = message['content']
        
        # 简单回复逻辑（可以扩展为调用 LLM）
        content_lower = content.lower()
        
        # 问候
        if any(kw in content_lower for kw in ['你好', 'hello', 'hi', '早上好', '下午好', '晚上好']):
            return f"你好 {sender}！很高兴见到你！"
        
        # 感谢
        if any(kw in content_lower for kw in ['谢谢', '感谢', 'thanks', 'thank you']):
            return "不客气！有其他问题随时问我。"
        
        # 再见
        if any(kw in content_lower for kw in ['再见', 'bye', 'goodbye', '拜拜']):
            return "再见！下次再聊！"
        
        # 问题
        if '?' in content or '？' in content:
            return "好问题！让我想想... 我认为这个问题需要从多个角度考虑。"
        
        # 紧急
        if any(kw in content_lower for kw in ['紧急', 'urgent', '急', 'help']):
            return "收到紧急消息！我会优先处理，请详细说明情况。"
        
        # 默认回复
        return f"收到你的消息：{content[:50]}"
    
    def process_message(self, message: Dict) -> bool:
        """
        处理单条消息
        
        Args:
            message: 消息字典
        
        Returns:
            是否成功处理
        """
        msg_id = message['id']
        sender = message['sender']
        content = message['content']
        priority = message.get('priority', 'normal')
        
        # 检查是否已处理
        if msg_id in self.processed_ids:
            return False
        
        # 检查是否是自己的消息（跳过）
        if sender == self.client_id:
            return False
        
        # 检查是否是回复给自己的消息（避免循环）
        reply_to = message.get('reply_to')
        if reply_to:
            # 如果这条消息是回复给某个消息的，而我们可能已经处理过那个消息的回复
            pass  # 继续处理，但记录这个信息
        
        self.log(f"[{sender}] {content[:50]}... (优先级：{priority})", "MESSAGE")
        
        # 生成并发送回复
        if self.auto_reply:
            reply = self.generate_reply(message)
            
            if reply:
                try:
                    reply_id = self.client.send(
                        reply,
                        reply_to=msg_id,
                        priority="normal" if priority == "normal" else "high"
                    )
                    self.log(f"已回复：{reply[:50]}...", "SUCCESS")
                    
                    # 立即标记自己的回复已处理
                    # 这样其他监听器不会回复我们的回复
                except Exception as e:
                    self.log(f"回复失败：{e}", "ERROR")
                    return False
        
        # 标记原消息已读
        try:
            self.client.mark_read([msg_id])
        except Exception as e:
            self.log(f"标记已读失败：{e}", "WARNING")
        
        # 记录已处理
        self.processed_ids.add(msg_id)
        
        # 清理历史记录
        if len(self.processed_ids) > self.max_history:
            self.processed_ids = set(list(self.processed_ids)[-self.max_history:])
        
        return True
    
    def check_and_process(self) -> int:
        """
        检查并处理新消息
        
        Returns:
            处理的消息数量
        """
        try:
            messages = self.client.read_unread(limit=10)
            
            if not messages:
                return 0
            
            count = 0
            for msg in messages:
                if self.process_message(msg):
                    count += 1
            
            return count
        
        except Exception as e:
            self.log(f"检查消息失败：{e}", "ERROR")
            return 0
    
    def run(self):
        """运行监听器"""
        self.running = True
        
        self.log("=" * 60)
        self.log(f"留言簿监听器启动")
        self.log(f"客户端 ID: {self.client_id}")
        self.log(f"检查间隔：{self.check_interval}秒")
        self.log(f"自动回复：{'开启' if self.auto_reply else '关闭'}")
        self.log(f"按 Ctrl+C 停止")
        self.log("=" * 60)
        
        check_count = 0
        total_processed = 0
        
        try:
            while self.running:
                # 检查并处理新消息
                processed = self.check_and_process()
                
                if processed > 0:
                    total_processed += processed
                    self.log(f"本轮处理：{processed} 条 | 累计：{total_processed} 条", "SUCCESS")
                
                check_count += 1
                
                # 定期显示状态
                if check_count % 20 == 0:
                    stats = self.client.get_stats()
                    self.log(f"状态检查 - 总消息：{stats['total_messages']}, 未读：{stats['unread_messages']}")
                
                # 等待下一次检查
                time.sleep(self.check_interval)
        
        except Exception as e:
            self.log(f"运行异常：{e}", "ERROR")
        
        finally:
            self.log("=" * 60)
            self.log(f"监听器关闭")
            self.log(f"总检查次数：{check_count}")
            self.log(f"总处理消息：{total_processed} 条")
            self.log("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="留言簿监听守护进程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本使用
    python3 message_listener.py --client-id my_ai
    
    # 自定义检查间隔
    python3 message_listener.py --client-id my_ai --interval 5
    
    # 关闭自动回复
    python3 message_listener.py --client-id my_ai --no-auto-reply
    
    # 后台运行
    nohup python3 message_listener.py --client-id my_ai &
        """
    )
    
    parser.add_argument(
        "--client-id", "-c",
        required=True,
        help="客户端 ID"
    )
    
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=3,
        help="检查间隔（秒），默认 3 秒"
    )
    
    parser.add_argument(
        "--no-auto-reply",
        action="store_true",
        help="关闭自动回复"
    )
    
    parser.add_argument(
        "--db-path",
        help="数据库路径（可选）"
    )
    
    parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        help="后台运行"
    )
    
    args = parser.parse_args()
    
    # 创建监听器
    listener = MessageListener(
        client_id=args.client_id,
        check_interval=args.interval,
        auto_reply=not args.no_auto_reply,
        db_path=args.db_path
    )
    
    # 运行
    if args.daemon:
        # 后台运行
        import os
        pid = os.fork()
        if pid > 0:
            print(f"守护进程已启动 (PID: {pid})")
            sys.exit(0)
        
        # 子进程
        os.setsid()
        sys.stdout = open('/dev/null', 'w')
        sys.stderr = open('/dev/null', 'w')
    
    listener.run()


if __name__ == "__main__":
    main()
