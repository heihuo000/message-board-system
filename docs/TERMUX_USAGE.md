# Termux 使用指南 - Message Board System

## 📦 一、安装与配置

### 1. 安装依赖

```bash
cd ~/message-board-system
pip install -r requirements.txt
```

### 2. 初始化配置

```bash
# 创建配置目录
mkdir -p ~/.message_board

# 复制配置文件
cp config/config.yaml.example ~/.message_board/config.yaml

# 编辑配置（设置你的客户端 ID）
nano ~/.message_board/config.yaml
```

**config.yaml 最小配置：**
```yaml
client:
  id: "my_ai"              # 你的客户端 ID

database:
  path: "~/.message_board/board.db"

trigger:
  method: "command"        # Termux 推荐用 command
  command: "echo '新消息：{content}'"
```

### 3. 初始化数据库

```bash
# 运行一次 CLI 自动创建数据库
python3 -m src.cli.main status
```

---

## 🚀 二、基本使用

### 发送消息

```bash
# 方式 1：使用 CLI
python3 -m src.cli.main send "你好，这是测试消息"

# 方式 2：使用 SDK 命令行
python3 message_sdk.py my_ai send "你好"

# 方式 3：指定优先级
python3 -m src.cli.main send "紧急问题" --priority urgent

# 方式 4：回复特定消息
python3 -m src.cli.main send "这是我的回复" --reply-to <message_id>
```

### 读取消息

```bash
# 读取未读消息
python3 -m src.cli.main read --unread

# 读取所有消息（最近 10 条）
python3 -m src.cli.main read

# JSON 格式输出
python3 -m src.cli.main read --json

# 使用 SDK
python3 message_sdk.py my_ai read
```

### 标记已读

```bash
# 标记单条
python3 -m src.cli.main mark-read <message_id>

# 标记全部
python3 -m src.cli.main mark-read --all
```

### 查看状态

```bash
python3 -m src.cli.main status
```

---

## 🔔 三、守护进程（自动监听）

### 前台运行（推荐调试用）

```bash
# 前台运行，可以看到日志
python3 -m src.daemon.main --foreground --client-id my_ai
```

### 后台运行

```bash
# 后台运行
python3 -m src.daemon.main --client-id my_ai

# 查看 PID
cat ~/.message_board/daemon.pid

# 停止守护进程
kill $(cat ~/.message_board/daemon.pid)
```

### 使用 nohup 后台运行

```bash
nohup python3 -m src.daemon.main --client-id my_ai > /tmp/daemon.log 2>&1 &

# 查看日志
tail -f /tmp/daemon.log
```

---

## 🤖 四、AI CLI 集成（Termux 环境）

### 方式 1：简单命令触发

编辑 `~/.message_board/config.yaml`：

```yaml
trigger:
  method: "command"
  command: "termux-notification --title '新消息' --content '{content}'"
```

需要安装 termux-api：
```bash
pkg install termux-api
```

### 方式 2：执行脚本触发

创建触发脚本：
```bash
cat > ~/.message_board/trigger.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
echo "收到消息：$MESSAGE_CONTENT"
# 这里可以调用 AI CLI
EOF
chmod +x ~/.message_board/trigger.sh
```

配置文件：
```yaml
trigger:
  method: "hook"
  hook:
    path: "~/.message_board/trigger.sh"
```

### 方式 3：手动检查（最简单）

不配置自动触发，手动检查消息：

```bash
# 在 AI CLI 会话中定期执行
python3 ~/message-board-system/src/cli/main.py read --unread
```

---

## 📱 五、Termux 特定场景

### 场景 1：两个 Termux 会话通信

**会话 1 - Alice：**
```bash
# 设置客户端 ID
export MESSAGE_CLIENT_ID="alice"

# 发送消息
python3 ~/message-board-system/src/cli/main.py send "你好 Bob"

# 启动守护进程
python3 -m src.daemon.main --client-id alice
```

**会话 2 - Bob：**
```bash
export MESSAGE_CLIENT_ID="bob"
python3 ~/message-board-system/src/cli/main.py send "你好 Alice"
python3 -m src.daemon.main --client-id bob
```

### 场景 2：Termux + 桌面端通信

**Termux 端：**
```bash
# 发送消息
python3 ~/message-board-system/src/cli/main.py send "我在手机上发的消息"
```

**桌面端：**
```bash
# 读取消息
python3 ~/message-board-system/src/cli/main.py read --unread
```

### 场景 3：系统通知集成

```bash
# 安装 termux-api
pkg install termux-api

# 配置触发器
cat > ~/.message_board/config.yaml << 'EOF'
trigger:
  method: "command"
  command: "termux-notification --title 'Message Board' --content '新消息：{content}' --on-delete 'python3 ~/message-board-system/src/cli/main.py mark-read --all'"
EOF
```

---

## 🧪 六、测试与调试

### 检查数据库

```bash
# 查看数据库文件
ls -lh ~/.message_board/

# 使用 sqlite3 查看
sqlite3 ~/.message_board/board.db "SELECT sender, content, timestamp FROM messages ORDER BY timestamp DESC LIMIT 5;"
```

### 查看守护进程状态

```bash
# 检查进程
ps aux | grep daemon

# 查看 PID 文件
cat ~/.message_board/daemon.pid

# 检查日志
cat ~/.message_board/daemon.log 2>/dev/null || echo "无日志文件"
```

### 测试消息流程

```bash
# 1. 发送消息
python3 -m src.cli.main send "测试消息 1"

# 2. 切换客户端 ID
export MESSAGE_CLIENT_ID="other_user"

# 3. 读取消息
python3 -m src.cli.main read --unread

# 4. 回复
python3 -m src.cli.main send "收到你的消息" --reply-to <msg_id>
```

---

## ⚠️ 七、常见问题

### 问题 1：数据库锁定

```bash
# 检查 WAL 模式
sqlite3 ~/.message_board/board.db "PRAGMA journal_mode;"

# 如果不是 WAL，手动设置
sqlite3 ~/.message_board/board.db "PRAGMA journal_mode=WAL;"
```

### 问题 2：守护进程不工作

```bash
# 1. 检查配置文件
cat ~/.message_board/config.yaml

# 2. 前台运行查看错误
python3 -m src.daemon.main --foreground --client-id my_ai

# 3. 检查数据库路径
ls -la ~/.message_board/board.db
```

### 问题 3：Termux 后台被杀

```bash
# 1. 获取 Termux 后台保护
pm grant com.termux android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS

# 2. 使用 nohup
nohup python3 -m src.daemon.main --client-id my_ai &

# 3. 或使用 tmux
pkg install tmux
tmux new -s daemon
python3 -m src.daemon.main --client-id my_ai
# 按 Ctrl+b 然后 d 分离会话
```

---

## 🔧 八、快捷命令

### 添加到 ~/.bashrc

```bash
# Message Board 快捷命令
alias mb-send='python3 ~/message-board-system/src/cli/main.py send'
alias mb-read='python3 ~/message-board-system/src/cli/main.py read --unread'
alias mb-status='python3 ~/message-board-system/src/cli/main.py status'
alias mb-daemon='python3 -m src.daemon.main --client-id'

# 使用示例
mb-send "你好"
mb-read
mb-status
mb-daemon my_ai
```

### 一键启动脚本

```bash
cat > ~/mb-start.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd ~/message-board-system

# 设置客户端 ID
export MESSAGE_CLIENT_ID="${1:-default}"

# 启动守护进程
echo "启动守护进程 (客户端：$MESSAGE_CLIENT_ID)..."
python3 -m src.daemon.main --client-id $MESSAGE_CLIENT_ID &

# 显示状态
python3 -m src.cli.main status
EOF

chmod +x ~/mb-start.sh

# 使用
~/mb-start.sh my_ai
```

---

## 📊 九、完整示例

### 完整工作流程

```bash
# === 终端 1 ===
# 设置 Alice
export MESSAGE_CLIENT_ID="alice"

# 启动守护进程
python3 -m src.daemon.main --client-id alice &

# 发送消息
python3 -m src.cli.main send "你好，我是 Alice"


# === 终端 2 ===
# 设置 Bob
export MESSAGE_CLIENT_ID="bob"

# 启动守护进程
python3 -m src.daemon.main --client-id bob &

# 读取消息
python3 -m src.cli.main read --unread

# 回复
python3 -m src.cli.main send "你好 Alice，我是 Bob" --reply-to <msg_id>


# === 终端 1 ===
# 查看回复
python3 -m src.cli.main read --unread
```

---

## 📚 十、相关文档

- [README.md](README.md) - 项目总览
- [EXAMPLES.md](EXAMPLES.md) - 使用示例
- [AI_COMMUNICATION_PROTOCOL.md](AI_COMMUNICATION_PROTOCOL.md) - 通信协议
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 项目总结

---

**最后更新**: 2026-02-27
**适用版本**: Termux 0.118+
