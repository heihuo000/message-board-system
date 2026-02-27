# Agent Hub MCP 配置指南

## 场景：iFlow → Qwen → Gemini → Claude 链式通信

## Claude Code 配置 ✓ 已完成

位置：`~/.claude-code/config.json`

```json
{
  "mcpServers": {
    "agent-hub": {
      "command": "npx",
      "args": ["-y", "agent-hub-mcp@latest"],
      "env": {
        "AGENT_HUB_DATA_DIR": "/data/data/com.termux/files/home/.agent-hub",
        "AGENT_NAME": "claude"
      }
    }
  }
}
```

## 其他 AI CLI 需要配置

### Qwen CLI 配置
```toml
[mcp_servers.agent-hub]
command = "npx"
args = ["-y", "agent-hub-mcp@latest"]

[mcp_servers.agent-hub.env]
AGENT_HUB_DATA_DIR = "/data/data/com.termux/files/home/.agent-hub"
AGENT_NAME = "qwen"
```

### Gemini CLI 配置
```toml
[mcp_servers.agent-hub]
command = "npx"
args = ["-y", "agent-hub-mcp@latest"]

[mcp_servers.agent-hub.env]
AGENT_HUB_DATA_DIR = "/data/data/com.termux/files/home/.agent-hub"
AGENT_NAME = "gemini"
```

### iFlow MCP 配置

在 iFlow 中注册到 Agent Hub，使用以下 MCP 工具：
- `register_agent` - 注册 iFlow agent
- `send_message` - 发送消息给其他 AI
- `sync` - 同步接收消息
- `get_hub_status` - 查看 hub 状态

## 使用流程

### 1. 各 AI CLI 注册到 Hub

**iFlow**:
```
使用 register_agent 工具：
{
  "agent_id": "iflow",
  "capabilities": ["task_planning", "coordination", "scripting"],
  "role": "orchestrator"
}
```

**Qwen**:
```
/hub:register
# Agent ID: qwen
# Capabilities: ["coding", "analysis", "debugging"]
```

**Gemini**:
```
/hub:register
# Agent ID: gemini
# Capabilities: ["templates", "patterns", "documentation"]
```

**Claude**:
```
/hub:register
# Agent ID: claude
# Capabilities: ["architecture", "best-practices", "review"]
```

### 2. 链式通信示例

**iFlow → Qwen → Gemini → Claude**:

```
iFlow: 创建任务并分配给 qwen
  ↓ send_message(to="qwen", task="analyze_code")
Qwen: 分析代码，转发给 gemini
  ↓ send_message(to="gemini", request="design_pattern")
Gemini: 设计模板，转发给 claude
  ↓ send_message(to="claude", request="review_best_practices")
Claude: 提供最佳实践建议
  ↓ send_message(to="qwen", result="final_recommendations")
Qwen: 收集结果，回复 iflow
  ↓ send_message(to="iflow", status="completed")
```

### 3. Agent Hub 命令

- `/hub:register` - 注册到 hub
- `/hub:sync` - 检查消息和工作负载
- `/hub:status` - 查看 hub 活动状态

## 共享数据目录

所有 AI CLI 使用同一个数据目录：
```
/data/data/com.termux/files/home/.agent-hub/
```

这样可以确保：
- 消息在所有 agent 间共享
- 任务状态同步
- Agent 列表一致

## 安装自定义命令（可选）

为 Claude Code 添加便捷命令：
```bash
git clone https://github.com/gilbarbara/agent-hub-mcp.git /tmp/agent-hub-mcp
mkdir -p ~/.claude/commands/hub
cp /tmp/agent-hub-mcp/commands/markdown/*.md ~/.claude/commands/hub/
```

## 测试连接

1. 启动 Claude Code，运行 `/hub:register`
2. 应该看到：`✅ Registered with Agent Hub as claude`
3. 运行 `/hub:status` 查看其他已注册的 agent

## 故障排查

- MCP 服务器未连接 → 重启 AI CLI
- 消息未收到 → 检查 AGENT_NAME 是否正确
- Agent ID 冲突 → 使用唯一的项目路径

## Agent 能力定义

| Agent | 能力 | 角色 |
|-------|------|------|
| iFlow | task_planning, coordination, scripting | 协调者 |
| Qwen | coding, analysis, debugging | 执行者 |
| Gemini | templates, patterns, documentation | 设计者 |
| Claude | architecture, best-practices, review | 审查者 |