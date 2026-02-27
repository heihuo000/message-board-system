# 多 AI CLI 协作工作流：iFlow → Qwen → Gemini → Claude

## 配置完成状态

✅ Claude Code - `~/.claude-code/config.json`
✅ Qwen - `~/.qwen/settings.json`
✅ Gemini - `~/.gemini/settings.json`
✅ 共享数据目录 - `~/.agent-hub/`

## 启动和注册流程

### 1. 重启所有 AI CLI
```bash
# 关闭所有打开的 AI CLI 会话
# 然后重新启动每个 CLI
```

### 2. 依次注册到 Agent Hub

#### iFlow 注册
iFlow 会自动通过 MCP 工具注册：
```
register_agent({
  "agent_id": "iflow",
  "capabilities": ["task_planning", "coordination", "scripting"],
  "role": "orchestrator"
})
```

#### Qwen 注册
```
启动 qwen CLI
输入: /hub:register
```

#### Gemini 注册
```
启动 gemini CLI
输入: /hub:register
```

#### Claude 注册
```
启动 claude CLI
输入: /hub:register
```

## 链式通信示例

### 场景：代码审查和优化任务

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  iFlow  │────▶│  Qwen   │────▶│  Gemini  │────▶│  Claude  │
│ 协调者  │     │ 执行者  │     │ 设计者  │     │ 审查者  │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
    │               │               │               │
    └───────────────┴───────────────┴───────────────┘
                    Agent Hub MCP
```

### 步骤详解

#### Step 1: iFlow 创建任务
```
iFlow: "需要审查 src/api/user.py 的代码质量"
↓ send_message(to="qwen", task={
  "type": "code_review",
  "file": "src/api/user.py",
  "focus": "security, performance"
})
```

#### Step 2: Qwen 分析代码
```
Qwen: "收到任务，开始分析代码..."
↓ 分析完成后
↓ send_message(to="gemini", request={
  "type": "pattern_suggestion",
  "context": "user API needs better error handling",
  "require": "design patterns for validation"
})
```

#### Step 3: Gemini 提供设计模式
```
Gemini: "建议使用以下模式..."
↓ 提供模板后
↓ send_message(to="claude", request={
  "type": "best_practice_review",
  "patterns": ["factory", "decorator"],
  "context": "API validation layer"
})
```

#### Step 4: Claude 提供最佳实践
```
Claude: "推荐以下最佳实践..."
↓ send_message(to="qwen", result={
  "recommendations": [...],
  "code_examples": [...]
})
```

#### Step 5: Qwen 应用改进
```
Qwen: "应用 Claude 的建议..."
↓ 完成修改
↓ send_message(to="iflow", status="completed", result={...})
```

#### Step 6: iFlow 汇总结果
```
iFlow: "任务完成，生成报告..."
↓ 输出最终报告给用户
```

## Agent Hub 工具参考

### 核心工具

#### register_agent
```json
{
  "agent_id": "iflow",
  "capabilities": ["task_planning", "coordination"],
  "metadata": {
    "role": "orchestrator",
    "project": "message-board-system"
  }
}
```

#### send_message
```json
{
  "to": "qwen",
  "message": {
    "type": "task",
    "content": "Please analyze...",
    "priority": "high"
  },
  "context": {
    "feature_id": "auth-refactor",
    "thread_id": "task-123"
  }
}
```

#### sync
```json
{
  "agent_id": "iflow",
  "include_messages": true,
  "include_tasks": true
}
```

#### get_hub_status
```json
{
  "include_active_agents": true,
  "include_recent_activity": true
}
```

### 任务管理工具

#### create_task
```json
{
  "title": "Refactor authentication system",
  "description": "Implement JWT-based auth",
  "required_capabilities": ["coding", "security"],
  "estimated_agents": ["qwen", "claude"],
  "priority": "high"
}
```

#### create_feature
```json
{
  "name": "user-authentication",
  "title": "Add User Authentication System",
  "description": "Implement login and signup",
  "priority": "high",
  "estimated_agents": ["iflow", "qwen", "gemini", "claude"]
}
```

## Agent 角色和能力

| Agent | Agent ID | 能力 | 职责 |
|-------|----------|------|------|
| iFlow | iflow | task_planning, coordination, scripting | 任务协调、工作流编排 |
| Qwen | qwen | coding, analysis, debugging | 代码执行、问题分析 |
| Gemini | gemini | templates, patterns, documentation | 设计模式、模板生成 |
| Claude | claude | architecture, best-practices, review | 架构设计、最佳实践 |

## 常见工作流

### 1. 代码重构工作流
```
iFlow → Qwen (分析) → Gemini (设计) → Claude (审查) → Qwen (实现) → iFlow (验证)
```

### 2. 新功能开发工作流
```
iFlow (规划) → Qwen (后端) + Gemini (前端) → Claude (集成测试) → iFlow (部署)
```

### 3. Bug 修复工作流
```
iFlow (接收报告) → Qwen (定位) → Claude (方案) → Qwen (修复) → Gemini (文档) → iFlow (关闭)
```

### 4. 性能优化工作流
```
iFlow (监控) → Qwen (分析) → Claude (优化建议) → Qwen (实施) → Gemini (测试) → iFlow (验证)
```

## 命令参考

### 检查连接状态
```bash
# 在 Claude Code 中
/hub:status

# 在 Qwen 中
/hub:status

# 在 Gemini 中
/hub:status
```

### 同步消息
```bash
# 在任何 AI CLI 中
/hub:sync
```

### 重新注册
```bash
/hub:register
```

## 故障排查

### 问题 1: 无法连接到 Agent Hub
- 检查网络连接
- 确认 `npx -y agent-hub-mcp@latest` 能正常运行
- 重启 AI CLI

### 问题 2: 消息未送达
- 确认目标 agent 已注册 (`/hub:status`)
- 检查 agent_id 是否正确
- 尝试重新发送

### 问题 3: Agent ID 冲突
- 每个 agent 使用唯一的 AGENT_NAME
- 确认配置文件中的 `AGENT_NAME` 正确

### 问题 4: 数据不同步
- 确认所有 AI CLI 使用同一个 `AGENT_HUB_DATA_DIR`
- 检查目录权限

## 性能优化

### 减少同步频率
只在需要时调用 `/hub:sync`

### 使用主题过滤
```json
{
  "to": "qwen",
  "topic": "code-review"
}
```

### 批量处理消息
```json
{
  "batch": [
    {"to": "qwen", "message": "..."},
    {"to": "gemini", "message": "..."}
  ]
}
```

## 最佳实践

1. **任务分解**：iFlow 将复杂任务分解为子任务
2. **能力匹配**：根据 agent 能力分配任务
3. **上下文共享**：使用 thread_id 维护上下文
4. **异步协作**：非阻塞式消息传递
5. **错误处理**：每个环节都要有错误反馈机制

## 扩展：添加更多 Agent

如需添加更多 AI CLI，只需：
1. 在其配置文件中添加相同的 agent-hub MCP 配置
2. 设置唯一的 AGENT_NAME
3. 启动并注册到 Hub
4. 其他 agent 即可通过 send_message 通信

例如添加 Codex：
```json
{
  "mcpServers": {
    "agent-hub": {
      "command": "npx",
      "args": ["-y", "agent-hub-mcp@latest"],
      "env": {
        "AGENT_HUB_DATA_DIR": "/data/data/com.termux/files/home/.agent-hub",
        "AGENT_NAME": "codex"
      }
    }
  }
}
```