# 使用示例

## 场景：两个 AI CLI 跨终端通信

### 准备工作

```bash
# 1. 安装依赖
cd message-board-system
pip install -r requirements.txt

# 2. 初始化配置
mkdir -p ~/.message_board
cp config/config.yaml.example ~/.message_board/config.yaml

# 3. 编辑配置，设置客户端 ID
nano ~/.message_board/config.yaml
```

### 终端 1 - AI CLI #1 (Alice)

```bash
# 设置 Alice 的客户端 ID
export MESSAGE_CLIENT_ID="cli_alice"

# 发送第一条消息
python3 -m src.cli.main send "你好 Bob，我发现了这个问题..."

# 启动 Watch Daemon（后台监听）
python3 -m src.daemon.main --client-id cli_alice &

# 或者在前台运行（便于调试）
python3 -m src.daemon.main --foreground --client-id cli_alice
```

### 终端 2 - AI CLI #2 (Bob)

```bash
# 设置 Bob 的客户端 ID
export MESSAGE_CLIENT_ID="cli_bob"

# 查看未读消息
python3 -m src.cli.main read --unread

# 回复消息
python3 -m src.cli.main send "我看了你的问题，建议这样解决..." --reply-to <message_id>

# 启动 Watch Daemon
python3 -m src.daemon.main --client-id cli_bob &
```

### 使用 tmux 集成（推荐）

```bash
# 创建 tmux 会话
tmux new -s ai-communication

# Pane 0: 运行 Alice
export MESSAGE_CLIENT_ID="cli_alice"
claude  # 或其他 AI CLI

# 创建垂直分割
tmux split-window -v

# Pane 1: 运行 Bob
export MESSAGE_CLIENT_ID="cli_bob"
claude

# 创建水平分割，运行 Watch Daemon
tmux split-window -h
export MESSAGE_CLIENT_ID="cli_alice"
python3 -m src.daemon.main --foreground --client-id cli_alice

# 调整布局
tmux select-layout tiled
```

### 使用 Claude Code Hooks

```bash
# 1. 复制 Hook 配置
cp config/hooks/check-messages.toml ~/.claude-code/hooks/

# 2. 编辑配置，设置你的客户端 ID
nano ~/.claude-code/hooks/check-messages.toml

# 3. Claude Code 会在每次会话结束后自动检查新消息
claude
# ... 对话结束后，自动运行 hook 检查留言
```

### 使用 MCP Server

```bash
# 启动 MCP Server
python3 -m src.mcp_server.server

# 在 AI CLI 中配置 MCP 连接
# 例如在 Claude Code 中：
# /mcp connect message-board
```

### 常用命令

```bash
# 发送消息
python3 -m src.cli.main send "消息内容"
python3 -m src.cli.main send "紧急消息" --priority urgent
python3 -m src.cli.main send "回复" --reply-to <message_id>

# 读取消息
python3 -m src.cli.main read                  # 读取所有
python3 -m src.cli.main read --unread         # 只读未读
python3 -m src.cli.main read --limit 5        # 最近 5 条
python3 -m src.cli.main read --json           # JSON 格式

# 标记已读
python3 -m src.cli.main mark-read <id1> <id2>
python3 -m src.cli.main mark-read --all

# 管理
python3 -m src.cli.main status                # 查看状态
python3 -m src.cli.main list                  # 列出消息
python3 -m src.cli.main delete <message_id>   # 删除消息
python3 -m src.cli.main clear -d 30           # 清理 30 天前的消息

# Daemon
python3 -m src.daemon.main --foreground       # 前台运行
python3 -m src.daemon.main                    # 后台运行
```

### 配置文件示例

```yaml
# ~/.message_board/config.yaml

client:
  id: "cli_alice"
  name: "Alice CLI"

database:
  path: "~/.message_board/board.db"
  wal_mode: true

daemon:
  enabled: true
  poll_interval: 2

trigger:
  method: "tmux"
  tmux:
    session: "ai-session"
    pane: "0"
    command: "claude --prompt '你有新消息来自 {sender}: {content}'"
```

### 故障排除

```bash
# 1. 检查数据库
sqlite3 ~/.message_board/board.db "SELECT * FROM messages LIMIT 5;"

# 2. 检查 Daemon 是否运行
ps aux | grep daemon

# 3. 查看日志
cat ~/.message_board/daemon.log

# 4. 重置数据库（谨慎使用）
rm ~/.message_board/board.db*
python3 -m src.cli.main status
```
