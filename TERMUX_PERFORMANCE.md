# Termux 环境性能优化指南

## 问题
在 Termux 环境中启动 3-4 个 AI 代理时容易出现终端崩溃或异常，通常是资源占用过高导致。

## 解决方案

### 1. 降低数据库连接数
已将默认连接数从 5 降低到 3，减少内存占用。

### 2. 优化数据库设置
```python
# 已在 connection_pool.py 中应用
PRAGMA journal_mode=WAL          # 写前日志模式
PRAGMA synchronous=NORMAL        # 平衡性能和安全性
PRAGMA cache_size=-2000          # 2MB 缓存
PRAGMA temp_store=MEMORY         # 临时表使用内存
PRAGMA mmap_size=268435456       # 256MB 内存映射
PRAGMA page_size=4096            # 4KB 页面大小
```

### 3. 监控资源使用
```bash
# 查看当前进程资源使用
python3 resource_monitor.py stats

# 查看系统资源
python3 resource_monitor.py system

# 持续监控
python3 resource_monitor.py monitor

# 检查警告
python3 resource_monitor.py check
```

### 4. 限制代理数量
建议在 Termux 环境中最多同时运行 2-3 个代理。

### 5. 使用轻量级配置
```bash
# 在 ~/.iflow/settings.json 中配置
"mcpServers": {
  "message-board": {
    "command": "python3",
    "args": [
      "/path/to/mcp_server_simple.py",
      "--max-connections", "2"  # 限制连接数
    ],
    "env": {
      "MESSAGE_BOARD_DIR": "/path/to/.message_board"
    }
  }
}
```

### 6. 定期清理资源
```bash
# 清理旧消息（1小时前）
python3 message_sdk.py cleanup 1

# 清理已完成任务
python3 message_sdk.py cleanup-tasks completed

# 清理等待代理（5分钟未活动）
python3 message_sdk.py cleanup-waiting 300
```

### 7. Termux 优化建议

#### 增加 Termux 内存限制
```bash
# 在 Termux 中运行
pkg install proot
proot -0
```

#### 关闭不必要的服务
```bash
# 检查运行的进程
ps aux

# 停止不必要的服务
# （根据实际情况操作）
```

#### 使用 zsh 替代 bash
```bash
pkg install zsh
chsh -s zsh
```

### 8. 性能基准

在标准 Termux 环境下（2GB RAM）：

| 代理数量 | 内存占用 | CPU占用 | 稳定性 |
|---------|---------|---------|--------|
| 1       | ~50MB   | 5-10%   | ✅ 稳定 |
| 2       | ~100MB  | 10-20%  | ✅ 稳定 |
| 3       | ~150MB  | 15-30%  | ⚠️ 可能卡顿 |
| 4       | ~200MB  | 20-40%  | ❌ 容易崩溃 |

### 9. 故障排除

#### 终端崩溃
1. 检查内存使用：`python3 resource_monitor.py stats`
2. 减少代理数量
3. 降低数据库连接数
4. 清理旧数据

#### 响应慢
1. 检查 CPU 占用
2. 清理等待列表
3. 优化查询索引

#### 连接失败
1. 检查数据库锁
2. 清理 WAL 文件
3. 重启代理

### 10. 最佳实践

1. **启动顺序**：先启动 iflow，再启动其他代理
2. **资源监控**：定期运行 `python3 resource_monitor.py check`
3. **数据清理**：每天清理旧数据
4. **优雅退出**：使用 Ctrl+C 而不是强制关闭
5. **日志管理**：定期清理日志文件

### 11. 应急方案

如果系统崩溃：

```bash
# 1. 检查残留进程
ps aux | grep python3

# 2. 杀死残留进程
pkill -f mcp_server_simple.py

# 3. 清理数据库锁
rm -f ~/.message_board/board.db-wal
rm -f ~/.message_board/board.db-shm

# 4. 重启系统（如果需要）
reboot
```

### 12. 进阶优化

#### 使用 SQLite 内存数据库（测试环境）
```python
# 仅用于测试，生产环境不推荐
DB_PATH = ":memory:"
```

#### 使用连接池缓存
```python
# 已在 connection_pool.py 中实现
# 自动缓存连接，减少创建开销
```

#### 批量操作优化
```python
# 批量插入
cursor.executemany("INSERT INTO ...", data)

# 批量更新
cursor.executemany("UPDATE ...", updates)
```

### 13. 监控指标

需要关注的关键指标：

- **内存占用** < 200MB
- **CPU占用** < 50%
- **线程数** < 50
- **打开文件数** < 100
- **数据库连接数** < 3

### 14. 性能测试

运行性能测试：
```bash
python3 performance_test.py
```

（需要创建 performance_test.py）

## 总结

在 Termux 环境中，资源有限是主要瓶颈。通过以下优化可以显著提升稳定性：

1. ✅ 降低数据库连接数（3个）
2. ✅ 优化数据库设置
3. ✅ 限制代理数量（2-3个）
4. ✅ 定期清理资源
5. ✅ 监控资源使用
6. ✅ 使用轻量级配置

遵循这些指南，可以在 Termux 环境中稳定运行多个 AI 代理。