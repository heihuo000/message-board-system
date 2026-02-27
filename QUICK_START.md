# 🚀 Agent Hub MCP 快速启动指南

## ✅ 配置已完成

| AI CLI | 配置文件 | Agent ID | 状态 |
|--------|----------|----------|------|
| Claude Code | `~/.claude-code/config.json` | `claude` | ✅ |
| Qwen | `~/.qwen/settings.json` | `qwen` | ✅ |
| Gemini | `~/.gemini/settings.json` | `gemini` | ✅ |
| iFlow | 通过 MCP 工具 | `iflow` | ⏳ |

**共享数据目录**: `~/.agent-hub/`

---

## 📋 下一步操作

### 1. 重启所有 AI CLI

关闭当前所有打开的 AI CLI 会话，然后重新启动：
```bash
# 重启 Claude Code
claude

# 重启 Qwen
qwen

# 重启 Gemini
gemini
```

### 2. 依次注册到 Agent Hub

#### Claude Code 注册
```
启动 claude CLI
输入: /hub:register

预期输出: ✅ Registered with Agent Hub as claude
```

#### Qwen 注册
```
启动 qwen CLI
输入: /hub:register

预期输出: ✅ Registered with Agent Hub as qwen
```

#### Gemini 注册
```
启动 gemini CLI
输入: /hub:register

预期输出: ✅ Registered with Agent Hub as gemini
```

#### iFlow 注册
iFlow 会自动通过 MCP 工具注册，无需手动操作。

### 3. 验证连接

在任何 AI CLI 中运行：
```
/hub:status
```

预期看到所有已注册的 agent：
- iflow
- qwen
- gemini
- claude

### 4. 测试通信

**从 Claude Code 发送消息给 Qwen**:
```
/hub:sync
send_message({
  "to": "qwen",
  "message": {
    "type": "test",
    "content": "Hello from Claude!"
  }
})
```

**在 Qwen 中检查**:
```
/hub:sync
```

应该收到来自 Claude 的消息。

---

## 🔄 链式通信示例

### 场景：代码审查流程

**Step 1 - iFlow 创建任务**:
```
iFlow: "审查 src/api/user.py"
↓ 发送到 qwen
```

**Step 2 - Qwen 分析**:
```
qwen: "分析代码..."
↓ 发送到 gemini
```

**Step 3 - Gemini 设计**:
```
gemini: "提供设计模式..."
↓ 发送到 claude
```

**Step 4 - Claude 审查**:
```
claude: "提供最佳实践..."
↓ 发送到 qwen
```

**Step 5 - Qwen 应用**:
```
qwen: "应用改进..."
↓ 发送到 iflow
```

**Step 6 - iFlow 完成**:
```
iFlow: "任务完成"
```

---

## 🛠️ 常用命令

| 命令 | 功能 |
|------|------|
| `/hub:register` | 注册到 Agent Hub |
| `/hub:sync` | 同步消息和工作负载 |
| `/hub:status` | 查看 Hub 状态和活动 |

---

## 📝 Agent Hub 工具

在 iFlow 或支持 MCP 的 AI CLI 中，可以使用这些工具：

### register_agent
注册 agent 到 Hub
```json
{
  "agent_id": "iflow",
  "capabilities": ["task_planning", "coordination"],
  "role": "orchestrator"
}
```

### send_message
发送消息给其他 agent
```json
{
  "to": "qwen",
  "message": {
    "type": "task",
    "content": "请分析代码..."
  }
}
```

### sync
同步消息
```json
{
  "agent_id": "iflow",
  "include_messages": true
}
```

### get_hub_status
获取 Hub 状态
```json
{
  "include_active_agents": true
}
```

---

## 🔧 故障排查

### 问题：无法连接 Agent Hub
**解决方案**:
1. 检查网络连接
2. 重启 AI CLI
3. 确认配置文件正确

### 问题：消息未送达
**解决方案**:
1. 运行 `/hub:status` 确认目标 agent 已注册
2. 检查 agent_id 是否正确
3. 尝试 `/hub:sync` 同步消息

### 问题：Agent ID 冲突
**解决方案**:
1. 确认每个 AI CLI 的 `AGENT_NAME` 唯一
2. 检查配置文件中的环境变量设置

---

## 📚 详细文档

- [Agent Hub 配置指南](./AGENT_HUB_SETUP.md)
- [多 AI 工作流](./MULTI_AI_WORKFLOW.md)

---

## 🎯 下一步

1. ✅ 重启所有 AI CLI
2. ✅ 使用 `/hub:register` 注册每个 agent
3. ✅ 使用 `/hub:status` 验证连接
4. ✅ 使用 `/hub:sync` 测试通信
5. ✅ 开始使用链式通信工作流

祝使用愉快！🎉