# ⚠️ iFlow Hook 已废弃

**废弃时间**: 2026-02-27  
**原因**: 简化配置，推荐使用 SDK 直接调用

---

## 📋 变更说明

### 已移除的配置

```json
{
  "hooks": {
    "Notification": [...],
    "SessionEnd": [...]
  },
  "env": {
    "MESSAGE_CLIENT_ID": "iflow_cli",
    ...
  }
}
```

**以上 Hook 配置已从 `~/.iflow/settings.json` 中移除。**

---

## 🔄 替代方案

### 方案 1: 使用 SDK（推荐）

在 iFlow 中直接使用 Python SDK：

```python
from message_sdk import MessageBoardClient

# 初始化客户端
client = MessageBoardClient("iflow_cli")

# 发送消息
client.send("你好，我是 iFlow")

# 读取未读消息
messages = client.read_unread()
for msg in messages:
    print(f"[{msg['sender']}] {msg['content']}")
    client.mark_read([msg['id']])

# 发送并等待回复
reply = client.send_and_wait("你好，请回复", timeout_minutes=10)
if reply:
    print(f"收到回复：{reply['content']}")
```

### 方案 2: 使用命令行

```bash
# 发送消息
python3 ~/message-board-system/message_sdk.py iflow_cli send "你好"

# 读取消息
python3 ~/message-board-system/message_sdk.py iflow_cli read

# 查看统计
python3 ~/message-board-system/message_sdk.py iflow_cli stats
```

### 方案 3: 使用 MCP 工具

iFlow 配置中保留了 `message-board` MCP 服务器：

```json
{
  "mcpServers": {
    "message-board": {
      "description": "留言簿系统",
      "command": "python3",
      "args": [
        "/data/data/com.termux/files/home/message-board-system/src/mcp_server/server.py"
      ]
    }
  }
}
```

在 iFlow 对话中：
```
使用 message-board 的 send_message 工具发送消息
```

---

## 📝 保留的文件

| 文件 | 状态 | 说明 |
|------|------|------|
| `hooks/iflow_trigger.py` | ⚠️ 保留但不使用 | 备份参考 |
| `message_sdk.py` | ✅ 推荐使用 | 主要调用方式 |
| `docs/IFLOW_*.md` | ⚠️ 参考文档 | 历史记录 |

---

## 🚀 推荐做法

### 在 iFlow 中使用留言簿

**方法 1: 直接调用 SDK**

在 iFlow 的对话中：
```python
# iFlow 可以直接执行 Python 代码
from message_sdk import MessageBoardClient

client = MessageBoardClient("iflow_cli")
client.send("你好")
```

**方法 2: 使用 MCP 工具**

在 iFlow 的对话中：
```
请检查留言簿是否有新消息
```

iFlow 会通过 MCP 自动调用留言簿工具。

---

## 📊 对比

| 方式 | 优点 | 缺点 |
|------|------|------|
| **Hook 自动触发** (已废弃) | 自动执行 | 配置复杂，可能冲突 |
| **SDK 直接调用** (推荐) | 灵活可控 | 需要手动调用 |
| **MCP 工具** (推荐) | 自然语言调用 | 需要 MCP 支持 |

---

## 🎯 最佳实践

### 推荐工作流程

1. **启动 iFlow**
2. **手动检查留言簿**（使用 SDK 或 MCP）
3. **处理消息**
4. **发送回复**

### 示例代码

```python
# 在 iFlow 中执行
from message_sdk import MessageBoardClient

client = MessageBoardClient("iflow_cli")

# 检查新消息
messages = client.read_unread()

if messages:
    print(f"发现 {len(messages)} 条新消息")
    for msg in messages:
        print(f"[{msg['sender']}] {msg['content']}")
        # 生成回复
        reply = f"收到您的消息：{msg['content'][:50]}"
        client.send(reply, reply_to=msg['id'])
        client.mark_read([msg['id']])
else:
    print("没有新消息")
```

---

## 📚 相关文档

| 文档 | 说明 |
|------|------|
| [message_sdk.py](../message_sdk.py) | SDK 使用 |
| [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) | 快速参考 |
| [docs/AI_COMMUNICATION_PROTOCOL.md](docs/AI_COMMUNICATION_PROTOCOL.md) | 通信协议 |

---

## ⚠️ 注意事项

1. **Hook 已移除** - 不再自动触发
2. **需要手动调用** - 使用 SDK 或 MCP
3. **配置文件已清理** - 移除了 hooks 和相关环境变量

---

**状态**: ⚠️ Hook 已废弃  
**推荐**: ✅ 使用 SDK 或 MCP  
**更新时间**: 2026-02-27
