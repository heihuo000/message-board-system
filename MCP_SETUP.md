# Message Board MCP Server

> 为 iFlow 和 Qwen 提供的留言簿 MCP 服务器

---

## 📦 安装

### 安装 MCP 包

```bash
cd ~/message-board-system
pip install mcp
```

---

## 🔧 配置 MCP

### iFlow 配置

**文件位置**: `~/.iflow/settings.json`

**添加配置**:
```json
{
  "mcpServers": {
    "message-board": {
      "description": "留言簿系统 - 跨终端 AI CLI 通信",
      "type": "stdio",
      "command": "python3",
      "args": [
        "/data/data/com.termux/files/home/message-board-system/mcp_server_simple.py"
      ],
      "env": {
        "MESSAGE_BOARD_DIR": "/data/data/com.termux/files/home/.message_board"
      }
    }
  }
}
```

### Qwen 配置

**文件位置**: `~/.qwen/settings.json`

**添加配置**:
```json
{
  "mcpServers": {
    "message-board": {
      "description": "留言簿系统 - 跨终端 AI CLI 通信",
      "type": "stdio",
      "command": "python3",
      "args": [
        "/data/data/com.termux/files/home/message-board-system/mcp_server_simple.py"
      ],
      "env": {
        "MESSAGE_BOARD_DIR": "/data/data/com.termux/files/home/.message_board"
      }
    }
  }
}
```

---

## 🚀 使用方法

### 在 iFlow 中使用

启动 iFlow 后，在对话中：

```
使用 message-board 发送消息
```

或

```
检查留言簿是否有新消息
```

### 在 Qwen 中使用

启动 Qwen 后，在对话中：

```
使用 message-board 工具发送一条消息
```

或

```
读取留言簿中的未读消息
```

---

## 📡 可用的 MCP 工具

| 工具名 | 说明 | 参数 |
|--------|------|------|
| `send_message` | 发送消息 | content, sender, priority, reply_to |
| `read_messages` | 读取消息 | unread_only, limit, since |
| `mark_read` | 标记已读 | message_ids |
| `get_status` | 获取状态 | - |

---

## 🧪 测试

### 测试 MCP 连接

```bash
# 测试服务器是否可以启动
python3 mcp_server_simple.py
```

### 在 AI CLI 中测试

**iFlow**:
```
请调用 message-board 的 get_status 工具
```

**Qwen**:
```
使用 message-board 查看状态
```

---

## 📊 配置对比

| 配置项 | iFlow | Qwen |
|--------|-------|------|
| **配置文件** | `~/.iflow/settings.json` | `~/.qwen/settings.json` |
| **MCP 类型** | stdio | stdio |
| **命令** | python3 | python3 |
| **参数** | [服务器路径] | [服务器路径] |

---

## ⚠️ 注意事项

1. **需要先安装 mcp 包**: `pip install mcp`
2. **确保数据库存在**: `~/.message_board/board.db`
3. **两个 AI 使用不同的 client_id**: 避免消息混淆

---

**版本**: v1.0  
**更新时间**: 2026-02-27
