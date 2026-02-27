#!/usr/bin/env python3
"""
AI 对话协调器 v1.1 - 基于 iFlow 批注改进版

改进内容:
1. 文件锁机制 - 防止并发读写
2. 超时重试 - 避免死锁
3. 对话模式 - 支持严格/灵活/异步
4. 消息过滤器 - 去重和优先级处理
5. 动态超时 - 根据内容估计时间
6. 对话监控 - 记录性能指标
7. 异常处理 - 完整的错误处理
"""
from message_sdk import MessageBoardClient
import time
import json
import hashlib
import fcntl
from pathlib import Path
from enum import Enum
from typing import Optional, Dict, List
from datetime import datetime


# ==================== 状态常量 ====================

STATE_WAITING_FOR_PARTNER = "waiting_for_partner"
STATE_WAITING_FOR_REPLY = "waiting_for_reply"
STATE_MY_TURN = "my_turn"
STATE_DIALOGUE_END = "dialogue_end"
STATE_TIMEOUT = "dialogue_timeout"
STATE_ERROR = "dialogue_error"


# ==================== 异常类 ====================

class DialogueError(Exception):
    """对话异常基类"""
    pass


class TimeoutError(DialogueError):
    """超时异常"""
    pass


class PartnerNotRespondingError(DialogueError):
    """对方无响应异常"""
    pass


class StateFileCorruptedError(DialogueError):
    """状态文件损坏异常"""
    pass


# ==================== 枚举类 ====================

class DialogueMode(Enum):
    """对话模式"""
    STRICT = "strict"      # 严格一人一句
    FLEXIBLE = "flexible"  # 灵活模式
    ASYNC = "async"        # 异步模式


class TaskType(Enum):
    """任务类型"""
    QUICK = "quick"      # 快速回复 30 秒
    NORMAL = "normal"    # 普通回复 120 秒
    COMPLEX = "complex"  # 复杂任务 600 秒
    LONG = "long"        # 长任务 1800 秒


# ==================== 消息过滤器 ====================

class MessageFilter:
    """消息过滤器"""
    
    def __init__(self):
        self.last_seen = int(time.time())
        self.seen_hashes = set()
        self.priority_override = True
    
    def should_process(self, message: dict) -> bool:
        """判断是否应该处理消息"""
        # 高优先级消息始终处理
        if self.priority_override and message.get('priority') == 'urgent':
            self.last_seen = message['timestamp']
            return True
        
        # 时间戳过滤
        if message['timestamp'] <= self.last_seen:
            return False
        
        # 内容去重
        msg_hash = hashlib.md5(message['content'].encode()).hexdigest()
        if msg_hash in self.seen_hashes:
            return False
        
        # 更新状态
        self.last_seen = message['timestamp']
        self.seen_hashes.add(msg_hash)
        return True
    
    def save_state(self, filepath: Path):
        """保存过滤器状态"""
        data = {
            "last_seen": self.last_seen,
            "seen_hashes": list(self.seen_hashes)
        }
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    
    def load_state(self, filepath: Path):
        """加载过滤器状态"""
        if not filepath.exists():
            return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.last_seen = data.get('last_seen', int(time.time()))
                self.seen_hashes = set(data.get('seen_hashes', []))
        except (json.JSONDecodeError, IOError):
            pass


# ==================== 超时管理器 ====================

class TimeoutManager:
    """超时管理器"""
    
    TIMEOUTS = {
        'quick': 30,
        'normal': 120,
        'complex': 600,
        'long': 1800
    }
    
    def estimate_timeout(self, content: str) -> int:
        """根据消息内容估计超时时间"""
        base_timeout = 60  # 基础 1 分钟
        
        # 长度因子（每 100 字增加 1 分钟，最多 5 分钟）
        length_factor = min(len(content) / 100, 5)
        
        # 紧急关键词
        urgent_keywords = ['紧急', 'urgent', 'asap', '速回', '急']
        if any(kw in content.lower() for kw in urgent_keywords):
            base_timeout *= 0.5
        
        # 复杂任务关键词
        complex_keywords = ['分析', '设计', 'implement', 'analyze', '复杂', '研究']
        if any(kw in content.lower() for kw in complex_keywords):
            base_timeout *= 2
        
        return int(base_timeout + length_factor * 60)
    
    def get_timeout(self, content: str, task_type: str = 'normal') -> int:
        """获取超时时间"""
        base_timeout = self.TIMEOUTS.get(task_type, 120)
        estimated = self.estimate_timeout(content)
        return min(base_timeout * 2, estimated)


# ==================== 对话监控器 ====================

class DialogueMonitor:
    """对话监控器"""
    
    def __init__(self):
        self.metrics = {
            'total_turns': 0,
            'avg_response_time': 0.0,
            'total_messages': 0,
            'errors': 0,
            'start_time': time.time()
        }
        self.response_times = []
    
    def record_turn(self, response_time: float):
        """记录一轮对话"""
        self.metrics['total_turns'] += 1
        self.metrics['total_messages'] += 2
        self.response_times.append(response_time)
        
        # 更新平均响应时间
        n = self.metrics['total_turns']
        self.metrics['avg_response_time'] = (
            (self.metrics['avg_response_time'] * (n - 1) + response_time) / n
        )
    
    def record_error(self):
        """记录错误"""
        self.metrics['errors'] += 1
    
    def get_report(self) -> dict:
        """获取监控报告"""
        duration = time.time() - self.metrics['start_time']
        return {
            **self.metrics,
            'duration_seconds': int(duration),
            'messages_per_minute': round(
                self.metrics['total_messages'] / (duration / 60), 2
            ) if duration > 0 else 0,
            'error_rate': round(
                self.metrics['errors'] / self.metrics['total_turns'] * 100, 2
            ) if self.metrics['total_turns'] > 0 else 0
        }
    
    def print_report(self):
        """打印监控报告"""
        report = self.get_report()
        print("\n" + "=" * 60)
        print("📊 对话监控报告")
        print("=" * 60)
        print(f"总轮次：{report['total_turns']}")
        print(f"总消息：{report['total_messages']}")
        print(f"平均响应时间：{report['avg_response_time']:.1f}秒")
        print(f"持续时间：{report['duration_seconds']}秒")
        print(f"消息速率：{report['messages_per_minute']}条/分钟")
        print(f"错误率：{report['error_rate']}%")
        print("=" * 60)


# ==================== AI 对话协调器 ====================

class AIDialogue:
    """AI 对话协调器 v1.1"""
    
    def __init__(
        self,
        client_id: str,
        partner_id: str,
        db_path: str = "~/.message_board/board.db",
        mode: DialogueMode = DialogueMode.STRICT,
        wait_timeout: int = 300,
        max_turns: int = 20,
        max_retries: int = 3
    ):
        """
        初始化对话协调器
        
        Args:
            client_id: 我的客户端 ID
            partner_id: 对话伙伴 ID
            db_path: 数据库路径
            mode: 对话模式
            wait_timeout: 等待超时（秒）
            max_turns: 最大对话轮次
            max_retries: 最大重试次数
        """
        self.client_id = client_id
        self.partner_id = partner_id
        self.mode = mode
        self.wait_timeout = wait_timeout
        self.max_turns = max_turns
        self.max_retries = max_retries
        
        self.client = MessageBoardClient(client_id, db_path)
        self.state = STATE_WAITING_FOR_PARTNER
        self.turn_count = 0
        self.last_seen = int(time.time())
        self.dialogue_history = []
        
        # 状态文件
        self.state_file = Path(f"~/.message_board/{client_id}_state.json").expanduser()
        self.filter_file = Path(f"~/.message_board/{client_id}_filter.json").expanduser()
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 组件
        self.message_filter = MessageFilter()
        self.timeout_manager = TimeoutManager()
        self.monitor = DialogueMonitor()
        
        # 加载过滤器状态
        self.message_filter.load_state(self.filter_file)
    
    def save_state(self, state: str):
        """保存当前状态（带文件锁）"""
        data = {
            "client_id": self.client_id,
            "partner_id": self.partner_id,
            "state": state,
            "turn_count": self.turn_count,
            "last_seen": self.last_seen,
            "timestamp": int(time.time()),
            "version": "1.1",
            "mode": self.mode.value
        }
        
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(data, f, ensure_ascii=False, indent=2)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except IOError as e:
            print(f"⚠️ 保存状态失败：{e}")
            self.monitor.record_error()
    
    def load_partner_state(self) -> dict:
        """读取对方的状态（带共享锁）"""
        partner_state_file = Path(f"~/.message_board/{self.partner_id}_state.json").expanduser()
        
        if not partner_state_file.exists():
            return {}
        
        try:
            with open(partner_state_file, 'r', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                data = json.load(f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return data
        except (json.JSONDecodeError, IOError):
            return {}
    
    def check_turn(self) -> bool:
        """检查是否轮到我发言"""
        if self.mode == DialogueMode.ASYNC:
            return True
        
        partner_state = self.load_partner_state()
        
        if not partner_state:
            return True
        
        # 对方刚发过消息，等我回复
        if partner_state.get('state') == STATE_WAITING_FOR_REPLY:
            return True
        
        # 对方在等我发言
        if partner_state.get('state') == STATE_WAITING_FOR_PARTNER:
            return False
        
        # 默认情况
        return True
    
    def send_message(
        self,
        content: str,
        priority: str = "normal",
        reply_to: str = None
    ) -> str:
        """发送消息并更新状态"""
        try:
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
            self.message_filter.save_state(self.filter_file)
            
            print(f"📤 [第{self.turn_count}轮] 已发送：{content[:50]}...")
            return msg_id
            
        except Exception as e:
            print(f"❌ 发送消息失败：{e}")
            self.monitor.record_error()
            raise
    
    def wait_for_message(self) -> Optional[dict]:
        """等待对方消息（带重试）"""
        start_wait = time.time()
        
        for attempt in range(self.max_retries):
            try:
                print(f"⏳ 等待 {self.partner_id} 的回复（第{attempt + 1}/{self.max_retries}次尝试）...")
                
                result = self.client.wait_for_message(
                    timeout=self.wait_timeout,
                    last_seen=self.last_seen
                )
                
                if result.get('success'):
                    msg = result['message']
                    
                    # 跳过自己的消息
                    if msg['sender'] == self.client_id:
                        print("  ⚠️ 跳过自己的消息")
                        continue
                    
                    # 使用过滤器检查
                    if not self.message_filter.should_process(msg):
                        print("  ⚠️ 跳过重复或旧消息")
                        continue
                    
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
                    self.message_filter.save_state(self.filter_file)
                    
                    # 记录响应时间
                    response_time = time.time() - start_wait
                    self.monitor.record_turn(response_time)
                    
                    print(f"📥 收到：[{msg['sender']}] {msg['content'][:50]}...")
                    return msg
                
                # 重试逻辑
                if attempt < self.max_retries - 1:
                    wait_time = 10 * (attempt + 1)
                    print(f"⚠️ 等待超时，{wait_time}秒后重试...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                print(f"❌ 等待消息失败：{e}")
                self.monitor.record_error()
        
        # 所有重试失败
        print("❌ 对方无响应，对话终止")
        self.state = STATE_TIMEOUT
        self.save_state()
        return None
    
    def start_dialogue(self, initial_message: str = None, reply_generator=None):
        """开始对话循环"""
        print("=" * 60)
        print(f"🎙️ AI 对话开始 (v1.1)")
        print(f"   我：{self.client_id}")
        print(f"   对方：{self.partner_id}")
        print(f"   模式：{self.mode.value}")
        print(f"   最大轮次：{self.max_turns}")
        print(f"   等待超时：{self.wait_timeout}秒")
        print(f"   最大重试：{self.max_retries}")
        print("=" * 60)
        
        try:
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
            
            # 打印监控报告
            self.monitor.print_report()
            
        except Exception as e:
            print(f"❌ 对话异常：{e}")
            self.state = STATE_ERROR
            self.save_state()
            self.monitor.print_report()
            raise
    
    def print_history(self):
        """打印对话历史"""
        print("\n" + "=" * 60)
        print("📋 对话历史")
        print("=" * 60)
        
        for item in self.dialogue_history:
            sender = item['sender']
            content = item['content'][:60]
            turn = item['turn']
            timestamp = datetime.fromtimestamp(item['timestamp']).strftime('%H:%M:%S')
            print(f"[{turn:02d}] [{timestamp}] {sender}: {content}...")
        
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
AI 对话协调器 v1.1 - 基于 iFlow 批注改进版

用法:
    python3 ai_dialogue_v1_1.py <client_id> <partner_id> [options]

选项:
    --first         先发言（发送第一条消息）
    --wait          等待对方先发言（默认）
    --timeout N     等待超时 N 秒（默认 300）
    --turns N       最大对话轮次 N（默认 20）
    --retries N     最大重试次数 N（默认 3）
    --mode MODE     对话模式 (strict|flexible|async)
    --task TYPE     任务类型 (quick|normal|complex|long)

示例:
    # 严格模式，先发言
    python3 ai_dialogue_v1_1.py ai_a ai_b --first --mode strict

    # 灵活模式，等待对方
    python3 ai_dialogue_v1_1.py ai_b ai_a --wait --mode flexible

    # 异步模式，自定义超时
    python3 ai_dialogue_v1_1.py ai_a ai_b --timeout 60 --turns 5 --mode async
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
    retries = 3
    mode = DialogueMode.STRICT
    task_type = 'normal'
    
    for i, arg in enumerate(sys.argv):
        if arg == "--timeout" and i + 1 < len(sys.argv):
            timeout = int(sys.argv[i + 1])
        elif arg == "--turns" and i + 1 < len(sys.argv):
            turns = int(sys.argv[i + 1])
        elif arg == "--retries" and i + 1 < len(sys.argv):
            retries = int(sys.argv[i + 1])
        elif arg == "--mode" and i + 1 < len(sys.argv):
            mode_str = sys.argv[i + 1]
            if mode_str == "flexible":
                mode = DialogueMode.FLEXIBLE
            elif mode_str == "async":
                mode = DialogueMode.ASYNC
            else:
                mode = DialogueMode.STRICT
        elif arg == "--task" and i + 1 < len(sys.argv):
            task_type = sys.argv[i + 1]
    
    # 创建对话协调器
    dialogue = AIDialogue(
        client_id=client_id,
        partner_id=partner_id,
        mode=mode,
        wait_timeout=timeout,
        max_turns=turns,
        max_retries=retries
    )
    
    # 选择回复模式
    if task_type == "task":
        reply_gen = task_reply
    else:
        reply_gen = simple_reply
    
    # 开始对话
    initial_msg = "你好，开始对话吧" if first else None
    dialogue.start_dialogue(initial_message=initial_msg, reply_generator=reply_gen)
    
    # 打印历史
    dialogue.print_history()
