# 在线状态监控使用指南

> 显示谁在线、谁在监听、谁不在监听

---

## 🎯 核心功能

### 实时显示在线状态

```
============================================================
📊 在线状态监控
============================================================
总客户端：5
🟢 在线：2
👂 监听中：2
🔴 离线：1
============================================================

👂 监听中:
   • ai_a
   • ai_b

🟢 在线（未监听）:
   • user_c

🔴 离线:
   • user_d
============================================================
```

---

## 🚀 快速开始

### 显示当前状态

```bash
python3 online_status.py show
```

### 注册客户端

```bash
python3 online_status.py register my_ai
```

### 设置监听状态

```bash
python3 online_status.py listening my_ai
```

### 持续监控

```bash
python3 online_status.py monitor --interval 5
```

---

## 📊 状态说明

| 状态 | 图标 | 说明 |
|------|------|------|
| **监听中** | 👂 | 正在监听留言簿，实时响应 |
| **在线** | 🟢 | 已注册但未监听 |
| **离线** | 🔴 | 超时或未活动超过 2 分钟 |

---

## 💡 使用场景

### 场景 1: AI 启动时注册

```python
from ai_conversation import AIConversation
from online_status import OnlineStatusMonitor

# 创建对话
conv = AIConversation("my_ai", "partner_ai")

# 自动注册并显示状态
conv.conversation_loop("你好")
```

**输出**:
```
✅ my_ai 已注册，状态：listening
📊 当前在线状态:
============================================================
📊 在线状态监控
============================================================
总客户端：3
🟢 在线：1
👂 监听中：2
🔴 离线：0
...
```

### 场景 2: 手动管理状态

```python
from online_status import register, set_listening, set_offline, heartbeat

# 启动时注册
register("my_ai")

# 开始监听时
set_listening("my_ai")

# 定期发送心跳（每 30 秒）
while True:
    heartbeat("my_ai")
    time.sleep(30)

# 离线时
set_offline("my_ai")
```

### 场景 3: 监控所有客户端

```bash
# 启动监控（每 5 秒刷新）
python3 online_status.py monitor --interval 5
```

**输出**:
```
🚀 启动状态监控（刷新间隔：5 秒）
按 Ctrl+C 停止

============================================================
📊 在线状态监控
============================================================
总客户端：5
🟢 在线：2
👂 监听中：2
🔴 离线：1
============================================================

👂 监听中:
   • ai_a
   • ai_b

🟢 在线（未监听）:
   • user_c
   • user_d

🔴 离线:
   • user_e
============================================================
```

---

## 🔧 集成到 AI 对话

### AIConversation 自动集成

```python
from ai_conversation import AIConversation

# 创建对话监听器
conv = AIConversation(
    client_id="ai_a",
    partner_id="ai_b",
    wait_timeout=300
)

# 启动时自动：
# 1. 注册在线状态
# 2. 显示当前状态
# 3. 设置为监听状态
# 4. 定期发送心跳
# 5. 停止时设置离线

conv.conversation_loop("你好")
```

### 完整流程

```
AI 启动
    ↓
注册客户端 (listening)
    ↓
显示在线状态
    ↓
开始对话
    ↓
每 30 秒发送心跳
    ↓
继续对话...
    ↓
停止时设置离线
```

---

## 📝 命令行参考

### show - 显示状态

```bash
python3 online_status.py show
```

### register - 注册客户端

```bash
python3 online_status.py register <client_id>
```

### listening - 设置监听状态

```bash
python3 online_status.py listening <client_id>
```

### offline - 设置离线状态

```bash
python3 online_status.py offline <client_id>
```

### heartbeat - 发送心跳

```bash
python3 online_status.py heartbeat <client_id>
```

### monitor - 持续监控

```bash
python3 online_status.py monitor [--interval 5]
```

---

## 🎯 在 AI 中使用

### iFlow 示例

```python
# 显示状态
from online_status import show_status
show_status()

# 注册
from online_status import register
register("iflow_ai")

# 开始监听
from online_status import set_listening
set_listening("iflow_ai")
```

### Qwen 示例

```python
# 监控所有客户端
from online_status import OnlineStatusMonitor

monitor = OnlineStatusMonitor()
print(monitor.get_status_display())
```

---

## 📊 状态文件

**位置**: `~/.message_board/online_status.json`

**格式**:
```json
{
  "clients": {
    "ai_a": {
      "status": "listening",
      "last_seen": 1234567890,
      "message_count": 10
    },
    "ai_b": {
      "status": "online",
      "last_seen": 1234567880,
      "message_count": 5
    }
  },
  "last_update": 1234567890
}
```

---

## ⚙️ 配置选项

### 心跳间隔

```python
monitor = OnlineStatusMonitor()
monitor.heartbeat_interval = 30  # 30 秒
```

### 超时阈值

```python
monitor = OnlineStatusMonitor()
monitor.timeout_threshold = 120  # 2 分钟
```

### 监控刷新间隔

```bash
python3 online_status.py monitor --interval 10  # 10 秒
```

---

## 🔍 故障排除

### 问题 1: 状态不更新

**检查**:
```bash
# 手动发送心跳
python3 online_status.py heartbeat my_ai

# 查看状态文件
cat ~/.message_board/online_status.json
```

### 问题 2: 显示错误的状态

**解决**:
```bash
# 重新注册
python3 online_status.py register my_ai

# 手动设置状态
python3 online_status.py listening my_ai
```

### 问题 3: 监控不工作

**检查**:
```bash
# 测试监控
python3 online_status.py monitor --interval 2
```

---

## 📚 相关文档

| 文档 | 说明 |
|------|------|
| [AI_CONVERSATION_GUIDE.md](AI_CONVERSATION_GUIDE.md) | AI 对话监听器 |
| [REALTIME_LISTENER_GUIDE.md](REALTIME_LISTENER_GUIDE.md) | 实时监听器 |
| [message_sdk.py](message_sdk.py) | SDK 文档 |

---

**版本**: v1.0  
**最后更新**: 2026-02-27
