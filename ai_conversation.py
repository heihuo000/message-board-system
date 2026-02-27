#!/usr/bin/env python3
"""
AI 对话监听器 - 一人一句模式
专为 AI 对话设计，发送后立即等待回复，错过时检查历史消息

特点:
- 发送消息后立即进入等待
- 等待时间更长（默认 5 分钟）
- 错过时检查留言簿历史
- 一人一句，自动循环
- 适合 AI 全自动对话

使用方法:
    python3 ai_conversation.py --client-id my_ai --partner other_ai
"""
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))
from message_sdk import MessageBoardClient
from online_status import OnlineStatusMonitor


class AIConversation:
    """AI 对话监听器"""
    
    def __init__(
        self,
        client_id: str,
        partner_id: Optional[str] = None,
        wait_timeout: int = 300,
        check_interval: int = 3,
        db_path: Optional[str] = None
    ):
        """
        初始化对话监听器
        
        Args:
            client_id: 自己的客户端 ID
            partner_id: 对话伙伴 ID（可选，为空则监听所有人）
            wait_timeout: 等待超时时间（秒），默认 5 分钟
            check_interval: 检查间隔（秒）
            db_path: 数据库路径
        """
        if db_path:
            self.client = MessageBoardClient(client_id, db_path)
        else:
            self.client = MessageBoardClient(client_id)
        
        self.client_id = client_id
        self.partner_id = partner_id
        self.wait_timeout = wait_timeout
        self.check_interval = check_interval
        self.running = True
        self.last_sent_id: Optional[str] = None
        self.last_read_timestamp: int = int(time.time())
        
        # 在线状态监控
        self.status_monitor = OnlineStatusMonitor()
    
    def log(self, message: str, emoji: str = "💬"):
        """格式化输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] {emoji} {message}")
        print("-" * 60)
    
    def send_message(self, content: str, reply_to: Optional[str] = None) -> str:
        """
        发送消息并进入等待状态
        
        Args:
            content: 消息内容
            reply_to: 回复的消息 ID
        
        Returns:
            消息 ID
        """
        msg_id = self.client.send(content, reply_to=reply_to)
        self.last_sent_id = msg_id
        self.last_read_timestamp = int(time.time())
        
        self.log(f"已发送：{content[:50]}...", "📤")
        return msg_id
    
    def wait_for_reply(self, original_msg_id: Optional[str] = None) -> Optional[Dict]:
        """
        等待回复
        
        Args:
            original_msg_id: 原消息 ID（回复该消息）
        
        Returns:
            回复消息，超时返回 None
        """
        self.log(f"等待回复（最多{self.wait_timeout}秒）...", "⏳")
        
        start_time = time.time()
        checked_ids = set()
        
        # 进度显示
        last_progress = 0
        
        while self.running:
            elapsed = time.time() - start_time
            
            # 显示进度（每 30 秒）
            if int(elapsed) % 30 == 0 and int(elapsed) != last_progress:
                remaining = self.wait_timeout - int(elapsed)
                print(f"   已等待 {int(elapsed)}秒，剩余 {remaining}秒...", end='\r')
                last_progress = int(elapsed)
                
                # 发送心跳
                self.status_monitor.heartbeat(self.client_id)
            
            # 超时检查
            if elapsed > self.wait_timeout:
                print(f"\n⏰ 超时，未收到回复")
                return None
            
            try:
                # 方法 1: 检查未读消息
                messages = self.client.read_unread(limit=20)
                
                for msg in messages:
                    # 跳过自己的消息
                    if msg['sender'] == self.client_id:
                        continue
                    
                    # 如果有指定伙伴，只接收该伙伴的消息
                    if self.partner_id and msg['sender'] != self.partner_id:
                        continue
                    
                    # 检查是否是回复给最后发送的消息
                    if original_msg_id and msg.get('reply_to') == original_msg_id:
                        self.log(f"收到回复：[{msg['sender']}] {msg['content'][:50]}...", "📥")
                        self.client.mark_read([msg['id']])
                        return msg
                    
                    # 检查是否是新消息（时间戳在最后一次读取之后）
                    if msg['timestamp'] > self.last_read_timestamp:
                        if msg['id'] not in checked_ids:
                            checked_ids.add(msg['id'])
                            self.log(f"收到新消息：[{msg['sender']}] {msg['content'][:50]}...", "📥")
                            self.client.mark_read([msg['id']])
                            return msg
                
                # 方法 2: 检查最近的历史消息（防止错过）
                all_messages = self.client.read_all(limit=10)
                
                for msg in all_messages:
                    # 跳过自己的消息和已检查的消息
                    if msg['sender'] == self.client_id or msg['id'] in checked_ids:
                        continue
                    
                    # 检查时间戳（只检查最近 2 分钟的消息）
                    if int(time.time()) - msg['timestamp'] < 120:
                        if self.partner_id and msg['sender'] != self.partner_id:
                            continue
                        
                        checked_ids.add(msg['id'])
                        self.log(f"从历史发现：[{msg['sender']}] {msg['content'][:30]}...", "📥")
                        self.client.mark_read([msg['id']])
                        return msg
            
            except Exception as e:
                self.log(f"检查消息失败：{e}", "❌")
            
            # 等待下次检查
            time.sleep(self.check_interval)
        
        return None
    
    def conversation_loop(self, initial_message: Optional[str] = None):
        """
        对话循环

        Args:
            initial_message: 第一条消息（可选）
        """
        # 注册在线状态
        self.status_monitor.register_client(self.client_id, "listening")
        self.log("已注册在线状态", "✅")
        
        # 显示当前在线状态
        self.log("当前在线状态:", "📊")
        print(self.status_monitor.get_status_display())
        
        self.log("=" * 60)
        self.log("🎙️ AI 对话监听器启动")
        self.log(f"客户端 ID: {self.client_id}")
        if self.partner_id:
            self.log(f"对话伙伴：{self.partner_id}")
        self.log(f"等待超时：{self.wait_timeout}秒")
        self.log("=" * 60)
        
        # 发送第一条消息
        if initial_message:
            msg_id = self.send_message(initial_message)
        else:
            # 等待对方先发消息
            self.log("等待对方先发消息...", "⏳")
            msg = self.wait_for_reply()
            if not msg:
                self.log("超时，无人回应", "⚠️")
                return
            msg_id = msg['id']
        
        # 对话循环
        reply_count = 0
        while self.running:
            # 等待回复
            reply = self.wait_for_reply(original_msg_id=msg_id)
            
            if not reply:
                self.log("对话结束，未收到回复", "👋")
                break
            
            reply_count += 1
            
            # AI 处理回复并生成新回复
            self.log(f"分析回复内容并生成回应...", "🤔")
            
            # 这里可以由 AI 调用自己的逻辑生成回复
            # 现在使用默认回复逻辑
            new_reply = self.generate_reply(reply)
            
            # 发送回复
            msg_id = self.send_message(new_reply, reply_to=reply['id'])
            
            self.log(f"对话轮次：{reply_count}", "📊")
        
        self.log("=" * 60)
        self.log(f"对话结束，共回复 {reply_count} 轮")
        self.log("=" * 60)
    
    def generate_reply(self, message: Dict) -> str:
        """
        生成回复（默认逻辑，可被 AI 覆盖）
        
        Args:
            message: 消息字典
        
        Returns:
            回复内容
        """
        content = message['content'].lower()
        sender = message['sender']
        
        # 问候
        if any(kw in content for kw in ['你好', 'hello', 'hi', '早上好']):
            return f"你好 {sender}！很高兴与你对话！"
        
        # 感谢
        if any(kw in content for kw in ['谢谢', '感谢', 'thanks']):
            return "不客气！有其他问题随时问我。"
        
        # 再见
        if any(kw in content for kw in ['再见', 'bye', 'goodbye']):
            return "再见！下次再聊！"
        
        # 问题
        if '?' in content or '？' in content:
            return "好问题！让我想想... 我认为这个问题需要从多个角度考虑。"
        
        # 紧急
        if any(kw in content for kw in ['紧急', 'urgent', '急', 'help']):
            return "收到紧急消息！我会优先处理，请详细说明情况。"
        
        # 默认回复
        return f"收到你的消息：{message['content'][:50]}"
    
    def stop(self):
        """停止对话"""
        self.running = False
        # 设置离线状态
        self.status_monitor.set_offline(self.client_id)
        print(f"\n🔴 {self.client_id} 已离线")


# ==================== 便捷函数 ====================

def ai_chat(
    client_id: str,
    partner_id: Optional[str] = None,
    initial_message: Optional[str] = None,
    wait_timeout: int = 300,
    reply_generator=None
):
    """
    AI 对话 - 一人一句模式
    
    Args:
        client_id: 自己的客户端 ID
        partner_id: 对话伙伴 ID
        initial_message: 第一条消息
        wait_timeout: 等待超时（秒）
        reply_generator: 回复生成函数
    """
    conv = AIConversation(
        client_id=client_id,
        partner_id=partner_id,
        wait_timeout=wait_timeout
    )
    
    # 覆盖默认回复生成器
    if reply_generator:
        conv.generate_reply = lambda msg: reply_generator(msg)
    
    # 开始对话
    conv.conversation_loop(initial_message=initial_message)


# ==================== 命令行接口 ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AI 对话监听器 - 一人一句模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本对话
    python3 ai_conversation.py --client-id my_ai --partner other_ai
    
    # 发送第一条消息
    python3 ai_conversation.py --client-id my_ai --partner other_ai --message "你好"
    
    # 自定义等待时间
    python3 ai_conversation.py --client-id my_ai --wait-timeout 600
        """
    )
    
    parser.add_argument(
        "--client-id", "-c",
        required=True,
        help="自己的客户端 ID"
    )
    
    parser.add_argument(
        "--partner", "-p",
        help="对话伙伴 ID"
    )
    
    parser.add_argument(
        "--message", "-m",
        help="第一条消息"
    )
    
    parser.add_argument(
        "--wait-timeout", "-t",
        type=int,
        default=300,
        help="等待超时时间（秒），默认 300 秒"
    )
    
    args = parser.parse_args()
    
    conv = AIConversation(
        client_id=args.client_id,
        partner_id=args.partner,
        wait_timeout=args.wait_timeout
    )
    
    try:
        conv.conversation_loop(initial_message=args.message)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        conv.stop()
