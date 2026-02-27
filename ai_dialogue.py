#!/usr/bin/env python3
"""
AI 对话协调器 - 确保两边 AI 遵守相同的对话规则

功能：
1. 自动协商对话顺序（谁先发言）
2. 一人一句模式 - 发送后必须等待
3. 防止抢话 - 使用状态标记
4. 自动重试 - 超时后提醒
5. 对话历史 - 记录完整上下文
"""
from message_sdk import MessageBoardClient
import time
import json
from pathlib import Path

# 状态常量
STATE_WAITING_FOR_PARTNER = "waiting_for_partner"  # 等待对方发言
STATE_WAITING_FOR_REPLY = "waiting_for_reply"      # 已发送，等待回复
STATE_MY_TURN = "my_turn"                          # 轮到我发言
STATE_DIALOGUE_END = "dialogue_end"                # 对话结束


class AIDialogue:
    """AI 对话协调器"""
    
    def __init__(
        self,
        client_id: str,
        partner_id: str,
        db_path: str = "~/.message_board/board.db",
        wait_timeout: int = 300,
        max_turns: int = 20
    ):
        """
        初始化对话协调器
        
        Args:
            client_id: 我的客户端 ID
            partner_id: 对话伙伴 ID
            db_path: 数据库路径
            wait_timeout: 等待超时（秒）
            max_turns: 最大对话轮次
        """
        self.client_id = client_id
        self.partner_id = partner_id
        self.wait_timeout = wait_timeout
        self.max_turns = max_turns
        
        self.client = MessageBoardClient(client_id, db_path)
        self.state = STATE_WAITING_FOR_PARTNER
        self.turn_count = 0
        self.last_seen = int(time.time())
        self.dialogue_history = []
        
        # 状态文件路径（用于跨进程同步）
        self.state_file = Path(f"~/.message_board/{client_id}_state.json").expanduser()
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
    def save_state(self):
        """保存当前状态到文件"""
        state_data = {
            "client_id": self.client_id,
            "partner_id": self.partner_id,
            "state": self.state,
            "turn_count": self.turn_count,
            "last_seen": self.last_seen,
            "timestamp": int(time.time())
        }
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
    
    def load_partner_state(self) -> dict:
        """读取对方的状态"""
        partner_state_file = Path(f"~/.message_board/{self.partner_id}_state.json").expanduser()
        
        if partner_state_file.exists():
            with open(partner_state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def check_turn(self) -> bool:
        """
        检查是否轮到我发言
        
        规则：
        1. 如果对方状态是 waiting_for_reply，说明我刚发过，应该等待
        2. 如果对方状态是 waiting_for_partner，说明在等我发言
        3. 如果对方最后活跃时间很久，可能是我先发言
        """
        partner_state = self.load_partner_state()
        
        if not partner_state:
            # 对方没有状态文件，可能是第一次对话
            return True
        
        # 检查对方是否刚发过消息（等我回复）
        if partner_state.get('state') == STATE_WAITING_FOR_REPLY:
            return True
        
        # 检查对方是否在等我
        if partner_state.get('state') == STATE_WAITING_FOR_PARTNER:
            return False
        
        # 默认情况，检查时间戳
        my_last_active = self.last_seen
        partner_last_active = partner_state.get('last_seen', 0)
        
        # 如果对方最近活跃，说明对方刚发过，轮到我
        return partner_last_active > my_last_active - 60
    
    def send_message(
        self,
        content: str,
        priority: str = "normal",
        reply_to: str = None
    ) -> str:
        """
        发送消息并更新状态
        
        Args:
            content: 消息内容
            priority: 优先级
            reply_to: 回复的消息 ID
            
        Returns:
            消息 ID
        """
        # 发送消息
        msg_id = self.client.send(
            content=content,
            priority=priority,
            reply_to=reply_to
        )
        
        # 更新状态
        self.state = STATE_WAITING_FOR_REPLY
        self.turn_count += 1
        self.last_seen = int(time.time())
        
        # 保存到对话历史
        self.dialogue_history.append({
            "turn": self.turn_count,
            "sender": self.client_id,
            "content": content,
            "timestamp": self.last_seen,
            "message_id": msg_id
        })
        
        # 保存状态文件
        self.save_state()
        
        print(f"📤 [第{self.turn_count}轮] 已发送：{content[:50]}...")
        return msg_id
    
    def wait_for_message(self) -> dict:
        """
        等待对方消息
        
        Returns:
            消息字典，超时返回 None
        """
        print(f"⏳ 等待 {self.partner_id} 的回复（最多{self.wait_timeout}秒）...")
        
        result = self.client.wait_for_message(
            timeout=self.wait_timeout,
            last_seen=self.last_seen
        )
        
        if result.get('success'):
            msg = result['message']
            
            # 跳过自己的消息
            if msg['sender'] == self.client_id:
                print("  ⚠️ 跳过自己的消息")
                return self.wait_for_message()  # 继续等待
            
            # 更新状态
            self.state = STATE_MY_TURN
            self.last_seen = msg['timestamp']
            
            # 保存到对话历史
            self.dialogue_history.append({
                "turn": self.turn_count + 1,
                "sender": msg['sender'],
                "content": msg['content'],
                "timestamp": msg['timestamp'],
                "message_id": msg['id']
            })
            
            # 保存状态
            self.save_state()
            
            print(f"📥 收到：[{msg['sender']}] {msg['content'][:50]}...")
            return msg
        else:
            print("⏰ 等待超时")
            self.state = STATE_WAITING_FOR_PARTNER
            self.save_state()
            return None
    
    def start_dialogue(self, initial_message: str = None, reply_generator=None):
        """
        开始对话循环
        
        Args:
            initial_message: 第一条消息（可选，不传则等待对方先发言）
            reply_generator: 回复生成函数，接收消息字典，返回回复内容
        """
        print("=" * 60)
        print(f"🎙️ AI 对话开始")
        print(f"   我：{self.client_id}")
        print(f"   对方：{self.partner_id}")
        print(f"   最大轮次：{self.max_turns}")
        print(f"   等待超时：{self.wait_timeout}秒")
        print("=" * 60)
        
        # 发送第一条消息（如果有）
        if initial_message:
            self.send_message(initial_message)
        
        # 对话主循环
        while self.turn_count < self.max_turns:
            # 检查是否轮到我
            if self.state == STATE_MY_TURN or self.check_turn():
                # 等待对方消息
                msg = self.wait_for_message()
                
                if msg is None:
                    # 超时，发送提醒
                    reminder = f"@{self.partner_id} 还在吗？等待回复中..."
                    self.send_message(reminder, priority="low")
                    continue
                
                # 生成回复
                if reply_generator:
                    reply_content = reply_generator(msg)
                else:
                    reply_content = f"收到：{msg['content'][:50]}"
                
                # 发送回复
                if reply_content:
                    self.send_message(reply_content, reply_to=msg['id'])
            else:
                # 等待对方发言
                msg = self.wait_for_message()
                
                if msg:
                    # 收到消息，轮到我回复
                    if reply_generator:
                        reply_content = reply_generator(msg)
                    else:
                        reply_content = f"收到：{msg['content'][:50]}"
                    
                    if reply_content:
                        self.send_message(reply_content, reply_to=msg['id'])
        
        # 对话结束
        print("=" * 60)
        print(f"✅ 对话完成，共{self.turn_count}轮")
        print("=" * 60)
        
        # 发送结束消息
        self.send_message("对话结束，再见！", priority="low")
        self.state = STATE_DIALOGUE_END
        self.save_state()
    
    def print_history(self):
        """打印对话历史"""
        print("\n" + "=" * 60)
        print("📋 对话历史")
        print("=" * 60)
        
        for item in self.dialogue_history:
            sender = item['sender']
            content = item['content'][:60]
            turn = item['turn']
            print(f"[{turn:02d}] {sender}: {content}...")
        
        print("=" * 60)


# ==================== 示例回复生成器 ====================

def simple_reply(msg: dict) -> str:
    """简单回复"""
    content = msg['content']
    
    if '你好' in content:
        return "你好！很高兴与你对话。"
    elif '问题' in content or '?' in content or '？' in content:
        return "好问题！让我想想..."
    elif '谢谢' in content:
        return "不客气！"
    elif '再见' in content:
        return "再见！期待下次对话。"
    else:
        return f"收到：{content[:50]}"


def task_reply(msg: dict) -> str:
    """任务处理回复"""
    content = msg['content']
    
    if '分析' in content:
        return "分析完成，结果是..."
    elif '处理' in content:
        return "处理完成，结果是..."
    elif '任务' in content:
        return "收到任务，立即执行..."
    else:
        return f"收到任务：{content[:50]}"


# ==================== 命令行接口 ====================

if __name__ == "__main__":
    import sys
    
    def print_usage():
        print("""
AI 对话协调器 - 确保两边 AI 遵守对话规则

用法:
    python3 ai_dialogue.py <client_id> <partner_id> [options]

选项:
    --first         先发言（发送第一条消息）
    --wait          等待对方先发言（默认）
    --timeout N     等待超时 N 秒（默认 300）
    --turns N       最大对话轮次 N（默认 20）
    --mode MODE     回复模式 (simple|task|custom)

示例:
    # 先发言
    python3 ai_dialogue.py ai_a ai_b --first

    # 等待对方先发言
    python3 ai_dialogue.py ai_b ai_a --wait

    # 自定义超时和轮次
    python3 ai_dialogue.py ai_a ai_b --timeout 60 --turns 10
        """)
    
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)
    
    client_id = sys.argv[1]
    partner_id = sys.argv[2]
    
    # 解析选项
    first = "--first" in sys.argv
    timeout = 300
    turns = 20
    mode = "simple"
    
    for i, arg in enumerate(sys.argv):
        if arg == "--timeout" and i + 1 < len(sys.argv):
            timeout = int(sys.argv[i + 1])
        elif arg == "--turns" and i + 1 < len(sys.argv):
            turns = int(sys.argv[i + 1])
        elif arg == "--mode" and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1]
    
    # 创建对话协调器
    dialogue = AIDialogue(
        client_id=client_id,
        partner_id=partner_id,
        wait_timeout=timeout,
        max_turns=turns
    )
    
    # 选择回复模式
    if mode == "task":
        reply_gen = task_reply
    else:
        reply_gen = simple_reply
    
    # 开始对话
    initial_msg = "你好，开始对话吧" if first else None
    dialogue.start_dialogue(initial_message=initial_msg, reply_generator=reply_gen)
    
    # 打印历史
    dialogue.print_history()
