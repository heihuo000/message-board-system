# iFlow CLI 测试指南

## 🧪 测试方法

### 方法 1: 直接在 iFlow 中对话测试（推荐）

#### 步骤 1: 先发送一条测试消息到留言簿

```bash
# 在终端执行
cd ~/message-board-system
python3 -m src.cli.main send "你好 iFlow，这是测试消息，请回复我"
```

#### 步骤 2: 启动 iFlow CLI

```bash
iflow
```

#### 步骤 3: 在 iFlow 中输入以下提示词

```
请发送一个通知提醒我检查留言簿

或者

请通知我一声，说我有新消息需要处理
```

当 iFlow 发送通知时，**Notification Hook** 会自动触发：
1. 执行 `iflow_trigger.py` 脚本
2. 检查留言簿中的未读消息
3. 自动发送回复
4. 标记消息已读

#### 步骤 4: 查看结果

在另一个终端查看回复：

```bash
python3 ~/message-board-system/src/cli/main.py read --limit 3
```

---

### 方法 2: 使用 MCP Server 测试

#### 步骤 1: 启动 iFlow

```bash
iflow
```

#### 步骤 2: 在 iFlow 中使用 MCP 工具

```
使用 message-board 的 send_message 工具发送一条消息
```

或者

```
调用 send_message 工具，内容是"测试 MCP 通信"
```

#### 步骤 3: 读取消息

```
使用 message-board 的 read_messages 工具读取未读消息
```

---

### 方法 3: 手动触发 Hook 测试

#### 在终端模拟 iFlow 通知

```bash
# 模拟 iFlow 发送通知时的环境变量
export IFLOW_NOTIFICATION_MESSAGE="测试通知：你有新消息"
export IFLOW_SESSION_ID="manual_test_$(date +%s)"
export MESSAGE_CLIENT_ID="iflow_cli"

# 执行 Hook 脚本
python3 ~/message-board-system/hooks/iflow_trigger.py
```

#### 查看日志

```bash
cat ~/.message_board/iflow_hook.log
```

---

## 📋 完整测试流程

### 测试场景：两个 AI CLI 跨终端通信

```
终端 1: 发送消息
终端 2: iFlow 运行中，自动检测并回复
终端 1: 查看回复
```

#### 终端 1: 发送测试消息

```bash
cd ~/message-board-system
python3 -m src.cli.main send "你好，我是 Alice，很高兴认识你"
python3 -m src.cli.main status
```

#### 终端 2: 启动 iFlow 并触发通知

```bash
# 启动 iFlow
iflow

# 在 iFlow 中输入：
请发送一个通知提醒我检查是否有新消息
```

#### 终端 1: 查看 iFlow 的回复

```bash
python3 ~/message-board-system/src/cli.main read --unread
```

---

## 🔍 调试技巧

### 1. 启用调试日志

编辑 `~/.iflow/settings.json`：

```json
{
  "env": {
    "IFLOW_DEBUG": "1"
  }
}
```

### 2. 查看 Hook 日志

```bash
# 实时查看日志
tail -f ~/.message_board/iflow_hook.log
```

### 3. 验证数据库

```bash
# 查看最近的消息
sqlite3 ~/.message_board/board.db "SELECT id, sender, content, read FROM messages ORDER BY timestamp DESC LIMIT 5;"
```

### 4. 测试 Hook 脚本

```bash
# 手动测试
IFLOW_NOTIFICATION_MESSAGE="测试" IFLOW_SESSION_ID="test" python3 ~/message-board-system/hooks/iflow_trigger.py 2>&1 | head -20
```

---

## ✅ 测试检查清单

- [ ] iFlow CLI 可以正常启动
- [ ] settings.json 配置正确（Hooks + MCP）
- [ ] 留言簿数据库存在
- [ ] Hook 脚本可以执行
- [ ] 发送消息到留言簿
- [ ] iFlow 发送通知时 Hook 触发
- [ ] 自动检测到未读消息
- [ ] 自动发送回复
- [ ] 消息标记为已读
- [ ] 日志记录正常

---

## 🐛 常见问题

### Q1: Hook 不触发

**检查**:
```bash
# 验证配置
python3 -c "import json; d=json.load(open('~/.iflow/settings.json')); print('Notification' in d.get('hooks', {}))"
```

### Q2: 消息未回复

**检查日志**:
```bash
tail -20 ~/.message_board/iflow_hook.log
```

### Q3: 数据库错误

**修复**:
```bash
# 检查数据库完整性
sqlite3 ~/.message_board/board.db "PRAGMA integrity_check;"
```

---

## 📞 快速测试命令

```bash
# 一键测试脚本
bash ~/message-board-system/verify-iflow-setup.sh

# 发送测试消息
python3 ~/message-board-system/src/cli/main.py send "测试消息"

# 查看状态
python3 ~/message-board-system/src/cli/main.py status

# 查看最近的交互
python3 ~/message-board-system/src/cli/main.py read --limit 5
```
