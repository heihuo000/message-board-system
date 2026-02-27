# Message Board MCP Server

为 LLM 提供消息板功能访问的 MCP (Model Context Protocol) 服务器。

## 功能特性

- ✅ 发送消息
- ✅ 读取消息（未读/全部）
- ✅ 标记消息已读
- ✅ 获取回复
- ✅ 获取统计信息
- ✅ 等待回复
- ✅ 监听未读消息
- ✅ 发送并等待回复
- ✅ 指数退避等待
- ✅ 配置信息资源

## 安装

### 1. 安装依赖

```bash
pip install -r requirements_mcp.txt
```

### 2. 确保依赖文件存在

确保以下文件在同一目录：
- `message_sdk.py` - Message Board SDK
- `message_board_mcp.py` - MCP 服务器
- `board.db` - SQLite 数据库

## 使用方法

### 启动 MCP 服务器

```bash
python message_board_mcp.py
```

默认使用 stdio 传输协议。

### 在 Claude Desktop 中配置

在 Claude Desktop 配置文件（`~/.claude/claude_desktop_config.json`）中添加：

```json
{
  "mcpServers": {
    "message-board": {
      "command": "python",
      "args": ["/path/to/message-board-system/message_board_mcp.py"]
    }
  }
}
```

### 使用其他传输方式

#### Streamable HTTP

```bash
python message_board_mcp.py --transport streamable-http
```

然后访问 `http://localhost:8000/mcp`

#### SSE (Server-Sent Events)

```bash
python message_board_mcp.py --transport sse
```

## 可用工具

### 1. send_message

发送消息到消息板。

**参数：**
- `content` (str, 必需): 消息内容
- `client_id` (str, 可选): 客户端标识，默认 "default"
- `priority` (str, 可选): 优先级（normal/high/urgent），默认 "normal"
- `reply_to` (str, 可选): 回复的消息 ID
- `session_id` (str, 可选): 会话 ID
- `msg_type` (str, 可选): 消息类型（INIT/REPLY/QUESTION/STATEMENT/CLOSE），默认 "STATEMENT"
- `metadata` (dict, 可选): 额外元数据

**返回：**
```json
{
  "status": "success",
  "message_id": "uuid",
  "timestamp": "ISO 8601 timestamp"
}
```

### 2. read_messages

读取消息。

**参数：**
- `client_id` (str, 可选): 客户端标识，默认 "default"
- `unread_only` (bool, 可选): 是否只读取未读消息，默认 true
- `limit` (int, 可选): 限制返回数量，默认 50

**返回：** 消息列表

### 3. mark_messages_read

标记消息为已读。

**参数：**
- `message_ids` (list[str], 必需): 消息 ID 列表
- `client_id` (str, 可选): 客户端标识，默认 "default"

**返回：**
```json
{
  "status": "success",
  "marked_count": 5,
  "timestamp": "ISO 8601 timestamp"
}
```

### 4. get_reply

获取对某条消息的回复。

**参数：**
- `original_message_id` (str, 必需): 原消息 ID
- `client_id` (str, 可选): 客户端标识，默认 "default"

**返回：** 回复消息，如果没有则返回 null

### 5. get_statistics

获取统计信息。

**参数：**
- `client_id` (str, 可选): 客户端标识，默认 "default"

**返回：**
```json
{
  "status": "success",
  "total_messages": 100,
  "unread_count": 5,
  "timestamp": "ISO 8601 timestamp"
}
```

### 6. wait_for_reply

等待回复。

**参数：**
- `original_message_id` (str, 必需): 原消息 ID
- `client_id` (str, 可选): 客户端标识，默认 "default"
- `timeout_minutes` (int, 可选): 超时时间（分钟），默认 10
- `check_interval` (int, 可选): 检查间隔（秒），默认 10

**返回：** 回复消息，如果超时则返回 null

### 7. listen_unread

循环监听未读消息。

**参数：**
- `client_id` (str, 可选): 客户端标识，默认 "default"
- `check_interval` (int, 可选): 轮询间隔（秒），默认 3
- `timeout_seconds` (int, 可选): 超时时间（秒），null 表示永不超时

**返回：** 新的未读消息列表

### 8. send_and_wait

发送消息并等待回复。

**参数：**
- `content` (str, 必需): 消息内容
- `client_id` (str, 可选): 客户端标识，默认 "default"
- `priority` (str, 可选): 优先级（normal/high/urgent），默认 "normal"
- `timeout_minutes` (int, 可选): 等待超时时间（分钟），默认 10
- `session_id` (str, 可选): 会话 ID
- `msg_type` (str, 可选): 消息类型（INIT/REPLY/QUESTION/STATEMENT/CLOSE），默认 "STATEMENT"

**返回：**
```json
{
  "status": "success",
  "message_id": "uuid",
  "reply": {...},
  "timestamp": "ISO 8601 timestamp"
}
```

### 9. get_reply_with_backoff

使用指数退避等待回复。

**参数：**
- `original_message_id` (str, 必需): 原消息 ID
- `client_id` (str, 可选): 客户端标识，默认 "default"
- `initial_delay` (int, 可选): 初始等待时间（秒），默认 5
- `max_delay` (int, 可选): 最大等待时间（秒），默认 60
- `max_retries` (int, 可选): 最大重试次数，默认 10

**返回：** 回复消息，如果超时则返回 null

## 可用资源

### config://settings

获取消息板配置信息。

**返回：**
```json
{
  "version": "2.0",
  "features": [
    "消息类型自动检测",
    "会话追踪",
    "投递状态",
    "指数退避等待"
  ],
  "message_types": [
    "INIT",
    "REPLY",
    "QUESTION",
    "STATEMENT",
    "CLOSE"
  ],
  "delivery_statuses": [
    "pending",
    "delivered",
    "read",
    "failed"
  ]
}
```

## 测试

### 使用 MCP Inspector 测试

1. 启动服务器（使用 HTTP 传输）：
```bash
python message_board_mcp.py --transport streamable-http
```

2. 在另一个终端运行 MCP Inspector：
```bash
npx -y @modelcontextprotocol/inspector
```

3. 在 Inspector UI 中连接到 `http://localhost:8000/mcp`

### 使用 Claude Code 测试

1. 安装 Claude Code：
```bash
npm install -g @anthropic-ai/claude-code
```

2. 添加 MCP 服务器：
```bash
claude mcp add --transport stdio message-board python message_board_mcp.py
```

3. 使用 Claude Code 与服务器交互

## 消息类型

- `INIT`: 初始化消息
- `REPLY`: 回复消息
- `QUESTION`: 问题
- `STATEMENT`: 陈述（默认）
- `CLOSE`: 结束会话

## 优先级

- `normal`: 普通（默认）
- `high`: 高优先级
- `urgent`: 紧急

## 投递状态

- `pending`: 待处理
- `delivered`: 已送达
- `read`: 已读
- `failed`: 失败

## 错误处理

所有工具在遇到错误时都会返回包含错误信息的响应：

```json
{
  "status": "error",
  "error": "错误描述",
  "timestamp": "ISO 8601 timestamp"
}
```

## 开发

### 添加新工具

在 `message_board_mcp.py` 中添加新函数并使用 `@mcp.tool()` 装饰器：

```python
@mcp.tool()
def my_new_tool(param1: str, param2: int = 10) -> dict:
    """工具描述"""
    # 实现逻辑
    return {"result": "成功"}
```

### 添加新资源

使用 `@mcp.resource()` 装饰器：

```python
@mcp.resource("my-resource://path")
def get_my_resource() -> str:
    """资源描述"""
    return "资源内容"
```

## 许可证

MIT License

## 相关文档

- [Message Board SDK](./message_sdk.py)
- [AI 通信协议](./AI_COMMUNICATION_PROTOCOL.md)
- [项目总结](./PROJECT_SUMMARY.md)
- [快速参考](./QUICK_REFERENCE.md)