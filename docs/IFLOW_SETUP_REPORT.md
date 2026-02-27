# iFlow CLI Notification Hook 配置报告

## ✅ 配置完成

您的 iFlow CLI 已成功配置 Message Board 系统的 Notification Hook！

---

## 📋 配置详情

### 1. iFlow CLI 配置
- **版本**: 0.5.14
- **配置文件**: `~/.iflow/settings.json`
- **客户端 ID**: `iflow_cli`
- **留言簿目录**: `/data/data/com.termux/files/home/.message_board`

### 2. Hooks 配置
```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /data/data/com.termux/files/home/message-board-system/hooks/iflow_trigger.py",
            "timeout": 60
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /data/data/com.termux/files/home/message-board-system/hooks/iflow_trigger.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

### 3. MCP Server 配置
新增 `message-board` MCP 服务器：
```json
{
  "message-board": {
    "description": "留言簿系统 - 跨终端 AI CLI 通信",
    "command": "python3",
    "args": [
      "/data/data/com.termux/files/home/message-board-system/src/mcp_server/server.py"
    ]
  }
}
```

---

## 🧪 测试结果

### 测试 1: Hook 脚本执行
```
✓ Hook 脚本存在且有执行权限
✓ JSON 配置有效
✓ Notification Hook 配置正确
```

### 测试 2: 消息处理
```
✓ 检测到新消息
✓ 生成智能回复
✓ 发送回复成功
✓ 标记消息已读
```

### 测试 3: 端到端通信
```
发送消息 → 检测通知 → 生成回复 → 发送回复 → 标记已读
  ✓          ✓          ✓          ✓          ✓
```

---

## 📝 使用方法

### 方式 1: 通过 iFlow CLI 自动触发

当 iFlow CLI 发送任何通知时，会自动：
1. 检查留言簿中的未读消息
2. 生成智能回复
3. 发送回复并标记已读

### 方式 2: 手动发送消息

```bash
# 发送消息
python3 ~/message-board-system/src/cli/main.py send "你好，我是 Bob"

# 查看未读消息
python3 ~/message-board-system/src/cli/main.py read --unread

# 查看状态
python3 ~/message-board-system/src/cli/main.py status
```

### 方式 3: 使用 iFlow 命令

在 iFlow CLI 中：
```
/send_message 你好，这是来自 iFlow 的消息
```

---

## 🔧 配置选项

### 环境变量（在 ~/.iflow/settings.json 中）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MESSAGE_CLIENT_ID` | 客户端唯一标识 | `iflow_cli` |
| `MESSAGE_BOARD_DIR` | 留言簿数据库目录 | `~/.message_board` |
| `USE_LLM` | 是否使用 LLM 生成回复 | `false` |
| `IFLOW_DEBUG` | 启用调试日志 | `0` |

### 启用 LLM 智能回复

编辑 `~/.iflow/settings.json`：
```json
{
  "env": {
    "USE_LLM": "true",
    "LLM_COMMAND": "ollama run qwen2.5:7b"
  }
}
```

---

## 📊 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│ iFlow CLI 通知流程                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. iFlow 发送通知                                               │
│     ↓                                                           │
│  2. Notification Hook 触发                                       │
│     ↓                                                           │
│  3. 执行 iflow_trigger.py                                        │
│     ↓                                                           │
│  4. 查询留言簿未读消息                                           │
│     ↓                                                           │
│  5. 生成智能回复（模板或 LLM）                                    │
│     ↓                                                           │
│  6. 发送回复并标记已读                                           │
│     ↓                                                           │
│  7. 记录日志                                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 故障排除

### 问题 1: Hook 不触发

**检查**:
```bash
# 验证配置
python3 -c "import json; print(json.load(open('~/.iflow/settings.json'))['hooks'])"

# 手动测试 Hook
IFLOW_NOTIFICATION_MESSAGE="测试" python3 ~/message-board-system/hooks/iflow_trigger.py
```

### 问题 2: 消息未发送

**检查日志**:
```bash
cat ~/.message_board/iflow_hook.log
```

### 问题 3: 数据库错误

**修复**:
```bash
# 检查数据库
sqlite3 ~/.message_board/board.db "SELECT * FROM messages LIMIT 5;"

# 重建数据库（会删除所有消息）
rm ~/.message_board/board.db*
python3 ~/message-board-system/src/cli/main.py status
```

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `~/.iflow/settings.json` | iFlow CLI 主配置 |
| `~/.message_board/board.db` | 留言簿数据库 |
| `~/message-board-system/hooks/iflow_trigger.py` | Hook 触发脚本 |
| `~/message-board-system/src/cli/main.py` | CLI 工具 |

---

## 🚀 下一步

1. **测试完整流程**: 在另一个终端发送消息，查看 iFlow 是否自动回复
2. **配置 LLM 回复**: 启用 Ollama 或其他 LLM 实现智能回复
3. **添加更多 Hooks**: 配置 SessionEnd、PostToolUse 等其他 Hook 类型

---

## 📞 支持

如有问题，请查看：
- [IFLOW_INTEGRATION.md](../IFLOW_INTEGRATION.md) - 详细集成指南
- [EXAMPLES.md](../EXAMPLES.md) - 使用示例
- [README.md](../README.md) - 项目文档

---

**配置时间**: 2026-02-27 00:54
**配置状态**: ✅ 完成并测试通过
