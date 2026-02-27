# iFlow CLI 自动唤醒说明

## ⚠️ 重要说明

**Notification Hook 不会自动唤醒 iFlow 回复消息**

### 原因

iFlow CLI 的工作机制：
1. **请求 - 响应模式** - iFlow 只在用户输入后才会响应
2. **不会后台监听** - iFlow 不会在后台持续运行监听消息
3. **Hook 触发时机** - 只在 iFlow **主动发送通知时** 触发 Notification Hook

---

## 🔄 工作流程对比

### ❌ 当前无法实现的流程

```
其他 CLI 发送消息 → 数据库更新 → iFlow 自动唤醒 → 自动回复
                    (×) iFlow 不会监听数据库变化
```

### ✅ 可以实现的工作流程

#### 方式 1: 用户触发（当前可用）

```
用户启动 iFlow → 用户输入"检查留言簿" → Notification Hook 触发 → 检查并回复
```

#### 方式 2: Watch Daemon + tmux（需要配置）

```
其他 CLI 发送消息 → Watch Daemon 检测 → tmux 发送命令到 iFlow 会话 → iFlow 处理回复
```

#### 方式 3: 定时检查（需要配置）

```
定时任务 → 启动 iFlow → 检查留言簿 → 发送回复 → 退出
```

---

## 🛠️ 解决方案

### 方案 1: 在 iFlow 中手动检查（最简单）

在 iFlow 中输入：

```
请检查留言簿是否有新消息，如果有的话帮我回复
```

iFlow 会：
1. 查询数据库
2. 发现未读消息
3. 生成回复
4. 发送回复

### 方案 2: 配置 SessionStart Hook（推荐）

每次启动 iFlow 时自动检查留言簿。

#### 修改 `~/.iflow/settings.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /data/data/com.termux/files/home/message-board-system/hooks/iflow_trigger.py",
            "timeout": 60,
            "description": "启动时检查留言簿"
          }
        ]
      }
    ]
  }
}
```

这样每次启动 iFlow 时会自动检查并回复。

### 方案 3: Watch Daemon + tmux 集成（高级）

需要 tmux 环境支持：

```bash
# 1. 创建 tmux 会话
tmux new -s iflow-session

# 2. 在 tmux 中启动 iFlow
iflow

# 3. 配置 Watch Daemon 使用 tmux 触发
# 编辑 ~/.message_board/config.yaml
trigger:
  method: "tmux"
  tmux:
    session: "iflow-session"
    pane: "0"
    command: "echo '检查留言簿'"

# 4. 启动 Watch Daemon
python3 -m src.daemon.main --client-id daemon
```

当有新消息时，Watch Daemon 会通过 tmux 向 iFlow 发送命令。

---

## 📊 各方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| 手动检查 | 简单可靠 | 需要用户介入 | ⭐⭐⭐ |
| SessionStart Hook | 启动时自动检查 | 只在启动时触发 | ⭐⭐⭐⭐ |
| Watch Daemon + tmux | 真正的自动触发 | 配置复杂，需要 tmux | ⭐⭐⭐⭐⭐ |

---

## 🎯 推荐配置

### 最佳实践配置

结合多种方案：

1. **SessionStart Hook** - 每次启动时检查
2. **Notification Hook** - iFlow 发送通知时检查
3. **用户手动触发** - 随时可以检查

### 配置文件

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/message-board-system/hooks/iflow_trigger.py",
            "timeout": 60
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/message-board-system/hooks/iflow_trigger.py",
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
            "command": "echo '会话结束，留言簿检查完成' >> ~/.message_board/session.log",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

---

## 💬 在 iFlow 中快速检查

在 iFlow 中输入以下任一提示词：

```
检查留言簿
```

```
查看是否有新消息
```

```
留言簿里有未读消息吗？有的话回复它们
```

```
使用留言簿工具读取未读消息并回复
```

---

## 🔍 验证配置

### 检查当前配置

```bash
python3 -c "
import json
config = json.load(open('~/.iflow/settings.json'))
hooks = config.get('hooks', {})
print('SessionStart:', 'SessionStart' in hooks)
print('Notification:', 'Notification' in hooks)
print('SessionEnd:', 'SessionEnd' in hooks)
"
```

### 测试 SessionStart Hook

1. 退出 iFlow（如果正在运行）
2. 发送一条测试消息
3. 重新启动 iFlow
4. 查看日志确认 Hook 触发

```bash
# 发送测试消息
python3 ~/message-board-system/src/cli/main.py send "测试 SessionStart Hook"

# 启动 iFlow
iflow

# 查看 Hook 日志
tail -20 ~/.message_board/iflow_hook.log
```

---

## 📝 总结

**iFlow 不会自动被唤醒回复**，但可以通过以下方式实现类似效果：

1. ✅ **SessionStart Hook** - 启动时自动检查（推荐）
2. ✅ **手动触发** - 在 iFlow 中说"检查留言簿"
3. ✅ **Watch Daemon + tmux** - 真正的自动触发（需要额外配置）

选择适合您的方案即可！
