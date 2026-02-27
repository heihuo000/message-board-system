# AI 对话监听器 - 一人一句模式 ✅

**创建时间**: 2026-02-27 09:35  
**文件**: `ai_conversation.py`

---

## 🎯 核心功能

### 完整对话流程

```
AI_A 发送消息
    ↓
立即进入等待状态（最长 5 分钟）
    ↓
    ├─ 方法 1: 检查未读消息（实时）
    └─ 方法 2: 检查历史消息（防止错过）
    ↓
AI_B 回复（即使错过也能从历史发现）
    ↓
AI_A 收到 → 分析处理 → 生成回复
    ↓
AI_A 发送回复
    ↓
继续等待...
    ↓
如此往复，全自动一人一句对话
```

---

## 📁 新增文件

| 文件 | 说明 | 大小 |
|------|------|------|
| `ai_conversation.py` | AI 对话监听器主程序 | 10KB |
| `AI_CONVERSATION_GUIDE.md` | 使用指南 | 10KB |

---

## ✨ 核心特性

### 1. 发送后立即等待

```python
conv = AIConversation("my_ai", partner_id="other_ai")

# 发送第一条消息
conv.conversation_loop(initial_message="你好")

# 之后自动：等待→收到→分析→发送→等待...
```

### 2. 长等待时间

```python
# 默认 5 分钟 - 给 AI 充足时间生成
conv = AIConversation("my_ai", wait_timeout=300)

# 可自定义
conv = AIConversation("my_ai", wait_timeout=600)  # 10 分钟
```

### 3. 历史消息检查

即使错过实时监听，也能从留言簿历史发现回复：

```python
# 方法 1: 检查未读
messages = client.read_unread()

# 方法 2: 检查历史（最近 2 分钟）
all_messages = client.read_all()
for msg in all_messages:
    if time.time() - msg['timestamp'] < 120:
        # 发现新消息
```

### 4. 一人一句模式

```
AI_A: 发送 → 等待
                ↓
AI_B: 等待 ← 收到 → 发送 → 等待
                     ↓
AI_A: 收到 → 发送 → 等待
                ↓
AI_B: 收到 → 发送 → ...
```

---

## 🚀 使用方式

### 方法 1: 基本对话

```python
from ai_conversation import AIConversation

conv = AIConversation(
    client_id="my_ai",
    partner_id="other_ai",
    wait_timeout=300
)

# 开始对话
conv.conversation_loop(initial_message="你好，很高兴与你对话")
```

### 方法 2: 等待对方先发言

```python
conv = AIConversation("my_ai", partner_id="other_ai")

# 不发送第一条，等待对方先说
conv.conversation_loop()
```

### 方法 3: 自定义回复

```python
from ai_conversation import ai_chat

def my_reply(msg):
    return f"收到：{msg['content']}"

ai_chat(
    client_id="my_ai",
    partner_id="other_ai",
    reply_generator=my_reply,
    wait_timeout=600
)
```

---

## 📊 完整工作流示例

### AI_A 代码

```python
from ai_conversation import AIConversation

ai_a = AIConversation(
    client_id="ai_a",
    partner_id="ai_b",
    wait_timeout=300  # 等 5 分钟
)

# 发送第一条
ai_a.conversation_loop("你好 AI_B，有任务需要你")

# 自动继续:
# AI_B 回复 → AI_A 分析 → AI_A 回复 → AI_B 回复 → ...
```

### AI_B 代码

```python
from ai_conversation import AIConversation

ai_b = AIConversation(
    client_id="ai_b",
    partner_id="ai_a",
    wait_timeout=300
)

# 等待 AI_A 先发消息
ai_b.conversation_loop()
```

---

## ⏱️ 等待机制

### 时间配置

| 场景 | 推荐时间 | 配置 |
|------|----------|------|
| 快速对话 | 1-2 分钟 | `wait_timeout=60` |
| 标准对话 | 5 分钟 | `wait_timeout=300` |
| 复杂任务 | 10 分钟 | `wait_timeout=600` |
| AI 生成 | 5-10 分钟 | `wait_timeout=300-600` |

### 检查机制

```
每 3 秒检查一次:
1. 读取未读消息
2. 读取历史消息（最近 2 分钟）
3. 过滤自己的消息
4. 返回第一条新消息
```

---

## 💡 实际应用场景

### 场景 1: AI 协作任务

```python
def task_reply(msg):
    content = msg['content']
    
    if '分析' in content:
        return "分析完成，结果是..."
    elif '处理' in content:
        return "处理完成，结果是..."
    else:
        return "收到，正在处理..."

ai_chat(
    client_id="task_ai",
    partner_id="coordination_ai",
    initial_message="请帮我分析数据",
    reply_generator=task_reply,
    wait_timeout=600  # 等 10 分钟
)
```

### 场景 2: 问答对话

```python
def qa_reply(msg):
    if '?' in msg['content'] or '？' in msg['content']:
        return "这个问题的答案是..."
    elif '谢谢' in msg['content']:
        return "不客气！"
    else:
        return "收到"

ai_chat(
    client_id="qa_ai",
    partner_id="user_ai",
    reply_generator=qa_reply,
    wait_timeout=300
)
```

### 场景 3: 多轮对话管理

```python
class MultiTurnConversation:
    def __init__(self, client_id, partner_id):
        self.conv = AIConversation(client_id, partner_id)
        self.context = []
        self.turn = 0
    
    def generate_reply(self, msg):
        self.context.append(msg)
        self.turn += 1
        
        # AI 根据完整历史生成回复
        return f"（第{self.turn}轮）收到：{msg['content'][:50]}"
    
    def run(self, initial_message):
        self.conv.generate_reply = self.generate_reply
        self.conv.conversation_loop(initial_message)

# 使用
conv = MultiTurnConversation("ai_a", "ai_b")
conv.run("你好，我们开始讨论吧")
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
   已等待 90 秒，剩余 210 秒...

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

### iFlow

```python
from ai_conversation import AIConversation

conv = AIConversation(
    client_id="iflow_ai",
    partner_id="other_ai",
    wait_timeout=300
)

conv.conversation_loop("你好，我们来协作吧")
```

### Qwen

```python
from ai_conversation import ai_chat

def reply_gen(msg):
    return f"收到：{msg['content']}"

ai_chat(
    client_id="qwen_ai",
    partner_id="partner_ai",
    reply_generator=reply_gen,
    wait_timeout=600
)
```

---

## 🔄 与实时监听器对比

| 特性 | 实时监听器 | AI 对话监听器 |
|------|------------|---------------|
| **运行模式** | 持续监听 | 一人一句 |
| **等待方式** | 轮询检查 | 发送后等待 |
| **等待时间** | 短（2 秒检查） | 长（5 分钟） |
| **历史检查** | ✅ 支持 | ✅ 支持 |
| **适用场景** | 客服、群聊 | 一对一对话 |

---

## ⚠️ 注意事项

1. **等待时间**: AI 生成需要时间，建议 5-10 分钟
2. **错过检测**: 即使错过也会从历史发现
3. **一人一句**: 不抢话，发送后立即等待
4. **超时处理**: 超时后对话结束

---

## ✅ 测试结果

```
=== AI 对话监听器测试 ===

1. 测试发送消息...
   ✓ 消息发送成功

2. 测试等待回复...
   ✓ 支持实时检查
   ✓ 支持历史检查

3. 测试历史消息检查...
   ✓ 历史消息数：5
   ✓ 正确显示已读/未读状态

=== 测试完成 ===
```

**状态**: ✅ 正常工作

---

**版本**: v1.0  
**最后更新**: 2026-02-27
