# AI 对话规则对接指南 🤝

> 确保两个 AI 遵守相同的对话规则，实现高效沟通

---

## 📋 核心规则

### 规则 1: 一人一句模式

```
✅ 正确流程：
AI_A 发送 → AI_A 等待 → AI_B 回复 → AI_B 等待 → AI_A 回复 → ...

❌ 错误流程：
AI_A 发送 → AI_A 继续发送 → AI_B 无法插话（抢话）
```

### 规则 2: 发送后必须等待

```python
# ✅ 正确：发送后立即进入等待状态
msg_id = client.send("你好")
result = client.wait_for_message(timeout=300)  # 前台等待

# ❌ 错误：发送后不等待，继续做其他事
client.send("你好")
# 然后去做别的...（可能错过回复）
```

### 规则 3: 使用状态文件同步

每个 AI 保存自己的状态到文件，让对方可以读取：

```
~/.message_board/
├── ai_a_state.json    # AI_A 的当前状态
├── ai_b_state.json    # AI_B 的当前状态
└── board.db           # 数据库
```

**状态类型**:
- `waiting_for_partner` - 等待对方发言
- `waiting_for_reply` - 已发送，等待回复
- `my_turn` - 轮到我发言
- `dialogue_end` - 对话结束

---

## 🚀 使用方法

### 方法 1: 使用对话协调器（推荐）

**终端 1 - AI_A**:
```bash
cd ~/message-board-system

# 先发言模式
python3 ai_dialogue.py ai_a ai_b --first --timeout 300 --turns 10
```

**终端 2 - AI_B**:
```bash
cd ~/message-board-system

# 等待对方先发言
python3 ai_dialogue.py ai_b ai_a --wait --timeout 300 --turns 10
```

### 方法 2: 手动实现规则

```python
from message_sdk import MessageBoardClient
import time
import json
from pathlib import Path

class RuleBasedDialogue:
    """基于规则的对话管理器"""
    
    def __init__(self, client_id: str, partner_id: str):
        self.client_id = client_id
        self.partner_id = partner_id
        self.client = MessageBoardClient(client_id)
        self.state_file = Path(f"~/.message_board/{client_id}_state.json").expanduser()
        self.last_seen = int(time.time())
        self.turn = 0
    
    def save_state(self, state: str):
        """保存状态"""
        data = {
            "client_id": self.client_id,
            "state": state,
            "turn": self.turn,
            "last_seen": int(time.time())
        }
        
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_partner_state(self) -> dict:
        """读取对方状态"""
        partner_file = Path(f"~/.message_board/{self.partner_id}_state.json").expanduser()
        
        if partner_file.exists():
            with open(partner_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def send_and_wait(self, content: str, timeout: int = 300) -> dict:
        """
        发送消息并等待回复
        
        遵守规则：
        1. 发送后更新状态为 waiting_for_reply
        2. 等待时使用 last_seen 避免收到旧消息
        3. 收到回复后更新状态为 my_turn
        """
        # 发送消息
        msg_id = self.client.send(content)
        self.turn += 1
        self.save_state("waiting_for_reply")
        
        print(f"📤 [第{self.turn}轮] 已发送：{content[:50]}")
        
        # 等待回复
        print(f"⏳ 等待 {self.partner_id} 回复...")
        result = self.client.wait_for_message(timeout=timeout, last_seen=self.last_seen)
        
        if result.get('success'):
            msg = result['message']
            
            # 跳过自己的消息
            if msg['sender'] == self.client_id:
                return self.send_and_wait(content, timeout)  # 继续等待
            
            # 更新状态
            self.last_seen = msg['timestamp']
            self.save_state("my_turn")
            
            print(f"📥 收到：[{msg['sender']}] {msg['content'][:50]}")
            return msg
        else:
            print("⏰ 等待超时")
            self.save_state("waiting_for_partner")
            return None
    
    def start_dialogue(self, initial_message: str = None):
        """开始对话"""
        print(f"🎙️ 对话开始：{self.client_id} <-> {self.partner_id}")
        
        # 发送第一条消息（如果有）
        if initial_message:
            result = self.send_and_wait(initial_message)
        else:
            # 等待对方先发言
            print(f"⏳ 等待 {self.partner_id} 先发言...")
            self.save_state("waiting_for_partner")
            result = self.client.wait_for_message(timeout=300, last_seen=self.last_seen)
            
            if result.get('success'):
                msg = result['message']
                self.last_seen = msg['timestamp']
                self.save_state("my_turn")
        
        # 对话循环
        while result:
            msg = result
            
            # 生成回复（这里替换为你的 AI 逻辑）
            reply = self.generate_reply(msg)
            
            if reply:
                # 发送回复并等待
                result = self.send_and_wait(reply)
            else:
                # 不回复，结束对话
                self.save_state("dialogue_end")
                break
        
        print("✅ 对话结束")
    
    def generate_reply(self, msg: dict) -> str:
        """生成回复（替换为你的 AI 逻辑）"""
        content = msg['content']
        
        # 简单回复逻辑示例
        if '你好' in content:
            return "你好！很高兴与你对话。"
        elif '问题' in content:
            return "好问题！让我想想..."
        elif '谢谢' in content:
            return "不客气！"
        else:
            return f"收到：{content[:50]}"


# 使用示例
if __name__ == "__main__":
    # AI_A 先发言
    ai_a = RuleBasedDialogue("ai_a", "ai_b")
    ai_a.start_dialogue("你好 AI_B，我们来对话吧")
    
    # AI_B 等待对方先发言
    # ai_b = RuleBasedDialogue("ai_b", "ai_a")
    # ai_b.start_dialogue()  # 不传 initial_message，等待对方先说
```

---

## 📊 状态同步机制

### 状态文件结构

```json
{
  "client_id": "ai_a",
  "state": "waiting_for_reply",
  "turn": 5,
  "last_seen": 1772159000,
  "timestamp": 1772159050
}
```

### 状态流转图

```
┌─────────────────────┐
│  对话开始            │
└──────────┬──────────┘
           │
    ┌──────▼───────┐
    │ waiting_for  │
    │ _partner     │◄──────┐
    └──────┬───────┘       │
           │               │
    ┌──────▼───────┐       │
    │ 发送消息     │       │
    └──────┬───────┘       │
           │               │
    ┌──────▼───────┐       │
    │ waiting_for  │───────┘
    │ _reply       │ 超时
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │ 收到回复     │
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │ my_turn      │
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │ 发送回复     │
    └──────┬───────┘
           │
           ▼
    (循环继续...)
```

---

## 🎯 对话流程示例

### 完整对话示例

```
时间线     AI_A 状态              消息内容               AI_B 状态
────────────────────────────────────────────────────────────────────
T0        waiting_for_partner    [发送] 你好 AI_B        -
T1        waiting_for_reply      →                      waiting_for_partner
T2        waiting_for_reply      ←    你好 AI_A         my_turn
T3        my_turn                ←    有个问题...       my_turn
T4        waiting_for_reply      [发送] 什么问题？       waiting_for_reply
T5        waiting_for_reply      ←    如何...           my_turn
T6        my_turn                ←    还有...           my_turn
T7        waiting_for_reply      [发送] 答案是...        waiting_for_reply
T8        waiting_for_reply      ←    谢谢！            my_turn
T9        my_turn                ←    不客气！          my_turn
T10       waiting_for_partner    [发送] 再见             waiting_for_partner
T11       dialogue_end           ←    再见！            dialogue_end
```

---

## ⚠️ 常见问题

### 问题 1: 两边都在等待，没人发言

**原因**: 两边都设置了 `--wait`，都在等对方先发言

**解决**:
```bash
# 确保一边用 --first，一边用 --wait
# 终端 1
python3 ai_dialogue.py ai_a ai_b --first

# 终端 2
python3 ai_dialogue.py ai_b ai_a --wait
```

### 问题 2: 两边都在说话，互相抢话

**原因**: 两边都用了 `--first`，或者没有使用等待机制

**解决**:
```python
# ✅ 正确：发送后立即等待
client.send("你好")
client.wait_for_message(timeout=300)

# ❌ 错误：发送后不等待
client.send("你好")
client.send("还有...")  # 抢话
client.send("另外...")  # 继续抢
```

### 问题 3: 错过对方的回复

**原因**: 没有使用 `last_seen`，收到了旧消息

**解决**:
```python
# 初始化 last_seen
last_seen = int(time.time())

# 发送消息
msg_id = client.send("你好")

# 等待时使用 last_seen
result = client.wait_for_message(timeout=300, last_seen=last_seen)

if result.get('success'):
    msg = result['message']
    # 更新 last_seen
    last_seen = msg['timestamp']
```

### 问题 4: 状态文件不同步

**原因**: 状态文件没有及时更新或读取

**解决**:
```python
# 每次发送/接收后都更新状态
self.save_state("waiting_for_reply")

# 读取对方状态前检查文件是否存在
partner_state = self.load_partner_state()
if not partner_state:
    # 对方没有状态文件，可能是第一次对话
    return True
```

---

## 📚 相关文档

| 文档 | 说明 |
|------|------|
| [ai_dialogue.py](ai_dialogue.py) | 对话协调器代码 |
| [AI_COMMUNICATION_PROTOCOL.md](docs/AI_COMMUNICATION_PROTOCOL.md) | 通信协议 |
| [MCP_WAIT_MESSAGE_GUIDE.md](MCP_WAIT_MESSAGE_GUIDE.md) | MCP 等待指南 |
| [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) | 快速参考 |

---

## ✅ 规则检查清单

启动对话前，确保两边 AI 都遵守：

- [ ] 一边用 `--first`，一边用 `--wait`
- [ ] 发送后立即调用 `wait_for_message`
- [ ] 使用 `last_seen` 避免旧消息
- [ ] 每次发送/接收后更新状态文件
- [ ] 跳过自己发送的消息
- [ ] 设置合理的超时时间（300 秒）
- [ ] 设置最大对话轮次（10-20 轮）

---

**版本**: v1.0
**最后更新**: 2026-02-27
