# iFlow CLI Notification Hook 集成方案

## 方案概述

利用 iFlow CLI 的 **Notification Hook** 机制，当收到特定通知时自动触发 AI 回复，实现与留言簿系统的深度集成。

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                     iFlow CLI                                    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Notification Hook 配置 (~/.iflow/settings.json)          │   │
│  │  {                                                        │   │
│  │    "hooks": {                                             │   │
│  │      "Notification": [                                    │   │
│  │        {                                                  │   │
│  │          "matcher": ".*新消息.*",                          │   │
│  │          "hooks": [{                                      │   │
│  │            "type": "command",                             │   │
│  │            "command": "~/.message_board/hooks/iflow_trigger.py" │
│  │          }]                                               │   │
│  │        }                                                  │   │
│  │      ]                                                    │   │
│  │    }                                                      │   │
│  │  }                                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   触发脚本                                       │
│  ~/.message_board/hooks/iflow_trigger.py                        │
│                                                                  │
│  1. 读取环境变量 IFLOW_NOTIFICATION_MESSAGE                      │
│  2. 解析通知内容，提取消息信息                                   │
│  3. 调用留言簿 API 发送回复                                       │
│  4. 可选：调用 LLM 生成智能回复                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   留言簿系统                                     │
│  - SQLite 数据库存储                                             │
│  - MCP Server 提供工具接口                                       │
│  - Watch Daemon 持续监听                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 配置步骤

### 步骤 1：创建触发脚本

```python
#!/usr/bin/env python3
"""
iFlow Notification Hook 触发器
当 iFlow 发送特定通知时，自动检查留言簿并触发回复
"""
import os
import sys
import json
import subprocess
from pathlib import Path

# 获取通知消息
notification_message = os.environ.get('IFLOW_NOTIFICATION_MESSAGE', '')
session_id = os.environ.get('IFLOW_SESSION_ID', 'unknown')

# 配置
MESSAGE_BOARD_DIR = Path("~/.message_board").expanduser()
DB_PATH = MESSAGE_BOARD_DIR / "board.db"
CLIENT_ID = os.environ.get('MESSAGE_CLIENT_ID', 'iflow_cli')

def check_new_messages():
    """检查新消息"""
    if not DB_PATH.exists():
        print(f"[iFlow Hook] 数据库不存在：{DB_PATH}", file=sys.stderr)
        return []
    
    # 使用 sqlite3 查询未读消息
    try:
        result = subprocess.run(
            [
                'sqlite3', '-json', str(DB_PATH),
                "SELECT id, sender, content, timestamp, priority "
                "FROM messages WHERE read = 0 AND sender != ? "
                "ORDER BY timestamp DESC LIMIT 5",
                CLIENT_ID
            ],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            messages = json.loads(result.stdout)
            return messages
        return []
    except Exception as e:
        print(f"[iFlow Hook] 查询失败：{e}", file=sys.stderr)
        return []

def mark_as_read(message_ids):
    """标记消息已读"""
    if not message_ids:
        return
    
    try:
        placeholders = ','.join(['?' for _ in message_ids])
        subprocess.run(
            [
                'sqlite3', str(DB_PATH),
                f"UPDATE messages SET read = 1 WHERE id IN ({placeholders})",
                *message_ids
            ],
            capture_output=True,
            timeout=5
        )
    except Exception as e:
        print(f"[iFlow Hook] 标记已读失败：{e}", file=sys.stderr)

def send_reply(reply_content, reply_to=None):
    """发送回复到留言簿"""
    try:
        # 使用 message-cli 发送
        cmd = [
            'python3',
            str(MESSAGE_BOARD_DIR.parent / 'message-board-system' / 'src' / 'cli' / 'main.py'),
            'send',
            reply_content
        ]
        
        if reply_to:
            cmd.extend(['--reply-to', reply_to])
        
        subprocess.run(cmd, capture_output=True, timeout=10)
        print(f"[iFlow Hook] 回复已发送", file=sys.stderr)
    except Exception as e:
        print(f"[iFlow Hook] 发送回复失败：{e}", file=sys.stderr)

def generate_ai_reply(message_content):
    """调用 LLM 生成智能回复（可选）"""
    # 这里可以集成任何 LLM API
    # 示例：调用本地 Ollama
    try:
        result = subprocess.run(
            [
                'ollama', 'run', 'qwen2.5:7b',
                f'收到留言：{message_content}\n请简短回复。'
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip()
    except Exception:
        #  fallback 到简单回复
        return f"收到您的消息，我会尽快处理。"

def main():
    """主函数"""
    print(f"[iFlow Hook] 收到通知：{notification_message[:100]}...", file=sys.stderr)
    print(f"[iFlow Hook] 会话 ID: {session_id}", file=sys.stderr)
    
    # 检查新消息
    new_messages = check_new_messages()
    
    if new_messages:
        print(f"[iFlow Hook] 发现 {len(new_messages)} 条新消息", file=sys.stderr)
        
        for msg in new_messages:
            sender = msg.get('sender', 'unknown')
            content = msg.get('content', '')
            msg_id = msg.get('id')
            priority = msg.get('priority', 'normal')
            
            print(f"[iFlow Hook] [{sender}] {content[:50]}...", file=sys.stderr)
            
            # 生成智能回复
            reply = generate_ai_reply(content)
            print(f"[iFlow Hook] 生成回复：{reply[:50]}...", file=sys.stderr)
            
            # 发送回复
            send_reply(reply, reply_to=msg_id)
            
            # 标记已读
            mark_as_read([msg_id])
    else:
        print(f"[iFlow Hook] 没有新消息", file=sys.stderr)

if __name__ == "__main__":
    main()
```

### 步骤 2：配置 iFlow Hooks

编辑 `~/.iflow/settings.json`：

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.message_board/hooks/iflow_trigger.py",
            "timeout": 60
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "send_message",
        "hooks": [
          {
            "type": "command",
            "command": "echo '消息已发送' >> ~/.message_board/iflow.log",
            "timeout": 5
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.message_board/hooks/iflow_trigger.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

### 步骤 3：配置环境变量

编辑 `~/.bashrc` 或 `~/.zshrc`：

```bash
# Message Board 配置
export MESSAGE_CLIENT_ID="iflow_cli"
export MESSAGE_BOARD_DIR="$HOME/.message_board"

# iFlow 配置
export IFLOW_DEBUG=1  # 启用调试日志
```

---

## 使用场景

### 场景 1：任务完成自动通知

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": ".*任务完成.*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.message_board/hooks/iflow_trigger.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

### 场景 2：权限请求自动处理

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": ".*permission.*",
        "hooks": [
          {
            "type": "command",
            "command": "echo '[自动允许] ' >> ~/.message_board/permission.log",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### 场景 3：错误通知自动记录

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": ".*错误.*|.*error.*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.message_board/hooks/error_handler.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

---

## 高级功能

### 1. 智能回复生成

集成本地 LLM（如 Ollama）生成智能回复：

```python
def generate_ai_reply(message_content, context=None):
    """调用本地 LLM 生成回复"""
    prompt = f"""
你是一个 AI 助手，收到以下留言：

{message_content}

请生成简短、友好的回复。
"""
    
    result = subprocess.run(
        ['ollama', 'run', 'qwen2.5:7b', prompt],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    return result.stdout.strip()
```

### 2. 多客户端路由

根据发送者路由到不同的处理逻辑：

```python
def route_message(sender, content):
    """根据发送者路由消息"""
    routes = {
        'cli_alice': handle_alice_message,
        'cli_bob': handle_bob_message,
        'iflow_cli': handle_iflow_message,
    }
    
    handler = routes.get(sender, handle_default_message)
    return handler(content)
```

### 3. 优先级处理

根据消息优先级采用不同处理策略：

```python
def handle_by_priority(messages):
    """根据优先级处理消息"""
    urgent = [m for m in messages if m.get('priority') == 'urgent']
    normal = [m for m in messages if m.get('priority') == 'normal']
    
    # 紧急消息立即处理
    for msg in urgent:
        process_urgent_message(msg)
    
    # 普通消息批量处理
    if normal:
        process_normal_messages(normal)
```

---

## 调试技巧

### 1. 启用详细日志

```bash
export IFLOW_DEBUG=1
iflow
```

### 2. 查看 Hook 日志

```bash
tail -f ~/.message_board/iflow.log
```

### 3. 测试 Hook 配置

```bash
# 手动触发 Hook 脚本
IFLOW_NOTIFICATION_MESSAGE="测试通知" IFLOW_SESSION_ID="test" \
  python3 ~/.message_board/hooks/iflow_trigger.py
```

### 4. 验证数据库

```bash
sqlite3 ~/.message_board/board.db "SELECT * FROM messages LIMIT 5;"
```

---

## 最佳实践

1. **超时设置**：Hook 脚本设置合理的 `timeout`（建议 30-60 秒）
2. **错误处理**：确保脚本在失败时不会阻塞 iFlow
3. **日志记录**：记录所有 Hook 执行日志便于调试
4. **幂等性**：确保脚本可以安全重复执行
5. **安全审查**：审查所有 Hook 脚本，避免执行不受信任的代码

---

## 完整示例配置

`~/.iflow/settings.json`:

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.message_board/hooks/iflow_trigger.py",
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
            "command": "echo 'Session ended at $(date)' >> ~/.message_board/session.log",
            "timeout": 10
          }
        ]
      }
    ]
  },
  "env": {
    "MESSAGE_CLIENT_ID": "iflow_cli",
    "MESSAGE_BOARD_DIR": "/home/user/.message_board"
  }
}
```

---

## 总结

通过 iFlow CLI 的 **Notification Hook**，我们可以实现：

- ✅ 收到通知时自动检查留言簿
- ✅ 自动触发 AI 生成回复
- ✅ 多客户端路由和优先级处理
- ✅ 完整的日志和错误处理
- ✅ 与现有留言簿系统无缝集成

这个方案比独立的 Watch Daemon 更轻量，因为它是**事件驱动**的，只在 iFlow 发送通知时触发。
