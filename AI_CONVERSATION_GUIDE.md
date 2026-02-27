# AI 对话监听器使用指南

> 一人一句模式 - 发送后立即等待回复，错过时检查历史

---

## 🎯 核心特点

### 完整对话流程

```
AI_A 发送消息
    ↓
进入等待状态（最长 5 分钟）
    ↓
AI_B 回复（即使错过监听也能从历史发现）
    ↓
AI_A 收到回复 → 分析处理
    ↓
AI_A 发送新回复
    ↓
继续等待...
    ↓
如此往复，全自动对话
```

---

## 🚀 快速开始

### 方法 1: 基本对话

```python
from ai_conversation import AIConversation

# 创建对话监听器
conv = AIConversation(
    client_id="my_ai",
    partner_id="other_ai",  # 对话伙伴
    wait_timeout=300        # 等待 5 分钟
)

# 开始对话（第一条消息）
conv.conversation_loop(initial_message="你好，很高兴与你对话！")
```

### 方法 2: 等待对方先发言

```python
conv = AIConversation("my_ai", partner_id="other_ai")

# 不发送第一条消息，等待对方先说
conv.conversation_loop()
```

### 方法 3: 自定义回复逻辑

```python
from ai_conversation import ai_chat

def my_reply_generator(msg):
    """自定义回复逻辑"""
    content = msg['content']
    
    # AI 生成回复的逻辑
    if '问题' in content:
        return "让我分析一下这个问题..."
    elif '任务' in content:
        return "好的，我立即处理这个任务..."
    else:
        return f"收到：{content[:50]}"

# 开始对话
ai_chat(
    client_id="my_ai",
    partner_id="other_ai",
    initial_message="你好",
    reply_generator=my_reply_generator
)
```

---

## 📊 完整工作流示例

### AI_A 代码

```python
from ai_conversation import AIConversation

# 创建对话
ai_a = AIConversation(
    client_id="ai_a",
    partner_id="ai_b",
    wait_timeout=300  # 等 5 分钟
)

# 发送第一条消息
print("AI_A 开始对话...")
ai_a.conversation_loop(initial_message="你好 AI_B，有个任务需要你帮忙")

# 对话会自动继续
# AI_B 回复 → AI_A 分析 → AI_A 回复 → AI_B 回复 → ...
```

### AI_B 代码

```python
from ai_conversation import AIConversation

# 创建对话
ai_b = AIConversation(
    client_id="ai_b",
    partner_id="ai_a",
    wait_timeout=300
)

# 等待 AI_A 先发消息
print("AI_B 等待消息...")
ai_b.conversation_loop()  # 不传 initial_message，等待对方先说
```

---

## 💡 实际使用场景

### 场景 1: AI 协作完成任务

```python
from ai_conversation import AIConversation

def task_reply(msg):
    """任务处理回复"""
    content = msg['content']
    
    if '分析' in content:
        # AI 分析逻辑
        return "分析完成，结果是..."
    elif '处理' in content:
        return "处理完成，结果是..."
    elif '完成' in content:
        return "好的，下一步做什么？"
    else:
        return "收到，正在处理..."

# AI_A 发起任务
ai_chat(
    client_id="task_ai",
    partner_id="coordination_ai",
    initial_message="请帮我分析这个数据",
    reply_generator=task_reply,
    wait_timeout=600  # 等 10 分钟
)
```

### 场景 2: 问答对话

```python
def qa_reply(msg):
    """问答回复"""
    content = msg['content'].lower()
    
    if '?' in content or '？' in content:
        # AI 回答问题
        return "这个问题的答案是..."
    elif '谢谢' in content:
        return "不客气！还有其他问题吗？"
    elif '你好' in content:
        return "你好！有什么可以帮你？"
    else:
        return "明白了，请继续。"

ai_chat(
    client_id="qa_ai",
    partner_id="user_ai",
    reply_generator=qa_reply,
    wait_timeout=300
)
```

### 场景 3: 多轮对话

```python
class MultiTurnConversation:
    """多轮对话管理"""
    
    def __init__(self, client_id, partner_id):
        self.conv = AIConversation(
            client_id=client_id,
            partner_id=partner_id,
            wait_timeout=300
        )
        
        self.context = []  # 对话历史
        self.turn = 0
    
    def generate_contextual_reply(self, msg):
        """基于上下文的回复"""
        # 保存对话历史
        self.context.append({
            'sender': msg['sender'],
            'content': msg['content']
        })
        
        # AI 可以根据完整对话历史生成回复
        print(f"对话历史：{len(self.context)} 轮")
        
        # 生成回复
        return f"收到（第{len(self.context)}轮）：{msg['content'][:50]}"
    
    def run(self, initial_message):
        """运行对话"""
        self.conv.generate_reply = self.generate_contextual_reply
        self.conv.conversation_loop(initial_message=initial_message)

# 使用
conv = MultiTurnConversation("ai_a", "ai_b")
conv.run("你好，我们开始讨论吧")
```

---

## ⚙️ 配置选项

### 等待时间配置

```python
# 短等待（1 分钟）
conv = AIConversation("my_ai", wait_timeout=60)

# 标准等待（5 分钟）
conv = AIConversation("my_ai", wait_timeout=300)

# 长等待（10 分钟）
conv = AIConversation("my_ai", wait_timeout=600)

# 超长等待（30 分钟）
conv = AIConversation("my_ai", wait_timeout=1800)
```

### 对话伙伴配置

```python
# 指定对话伙伴（只接收该伙伴的消息）
conv = AIConversation("my_ai", partner_id="specific_ai")

# 监听所有人（接收所有非自己的消息）
conv = AIConversation("my_ai")  # 不指定 partner_id
```

### 检查间隔配置

```python
# 快速检查（1 秒）
conv = AIConversation("my_ai", check_interval=1)

# 标准检查（3 秒）
conv = AIConversation("my_ai", check_interval=3)

# 慢速检查（5 秒）
conv = AIConversation("my_ai", check_interval=5)
```

---

## 🔍 工作原理

### 消息检测机制

```python
# 方法 1: 检查未读消息
messages = client.read_unread(limit=20)
for msg in messages:
    if msg['sender'] != self.client_id:  # 排除自己
        return msg  # 发现新消息

# 方法 2: 检查历史消息（防止错过）
all_messages = client.read_all(limit=10)
for msg in all_messages:
    # 检查最近 2 分钟的消息
    if time.time() - msg['timestamp'] < 120:
        return msg  # 从历史发现
```

### 等待逻辑

```
开始等待
    ↓
每 3 秒检查一次
    ↓
检查未读消息 → 发现 → 返回
    ↓
检查历史消息 → 发现 → 返回
    ↓
继续等待...
    ↓
超时（5 分钟）→ 返回 None
```

---

## 📝 输出示例

```
============================================================
🎙️ AI 对话监听器启动
客户端 ID: ai_a
对话伙伴：ai_b
等待超时：300 秒
============================================================

[09:30:00] 📤 已发送：你好 AI_B，有个任务需要你帮忙
------------------------------------------------------------

[09:30:00] ⏳ 等待回复（最多 300 秒）...
------------------------------------------------------------
   已等待 30 秒，剩余 270 秒...
   已等待 60 秒，剩余 240 秒...

[09:32:15] 📥 收到回复：[ai_b] 好的，什么任务？
------------------------------------------------------------

[09:32:15] 🤔 分析回复内容并生成回应...

[09:32:16] 📤 已发送：请帮我分析这个数据...
------------------------------------------------------------

[09:32:16] 📊 对话轮次：1

[09:32:16] ⏳ 等待回复（最多 300 秒）...
...
```

---

## 🎯 在 AI 中使用

### iFlow 示例

```python
# 在 iFlow 对话中执行
from ai_conversation import AIConversation

conv = AIConversation(
    client_id="iflow_ai",
    partner_id="other_ai",
    wait_timeout=300
)

# 开始对话
conv.conversation_loop(initial_message="你好，我们来协作吧")
```

### Qwen 示例

```python
# 在 Qwen 对话中执行
from ai_conversation import ai_chat

def reply_gen(msg):
    # AI 生成回复的逻辑
    return f"收到：{msg['content']}"

ai_chat(
    client_id="qwen_ai",
    partner_id="partner_ai",
    reply_generator=reply_gen,
    wait_timeout=600
)
```

---

## ⚠️ 注意事项

1. **等待时间**: AI 生成需要时间，建议设置 5-10 分钟
2. **错过检测**: 即使错过实时检测，也会从历史发现
3. **一人一句**: 发送后立即等待，不抢话
4. **超时处理**: 超时后对话结束，可重新启动

---

## 📚 相关文档

| 文档 | 说明 |
|------|------|
| [REALTIME_LISTENER_GUIDE.md](REALTIME_LISTENER_GUIDE.md) | 实时监听器 |
| [message_sdk.py](message_sdk.py) | SDK 文档 |
| [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) | 快速参考 |

---

**版本**: v1.0  
**最后更新**: 2026-02-27
