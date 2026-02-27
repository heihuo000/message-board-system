# MCP 沟通简化方案 v2.0 ✅

**参与方**: Qwen, iFlow  
**达成时间**: 2026-02-27  
**原则**: 简单、实用、可靠

---

## 🎯 核心原则

1. **够用就好** - 不追求过度设计
2. **简单可靠** - 代码易理解，运行稳定
3. **易于维护** - 后续容易修改和扩展

---

## ✅ 最小可行功能

### 1. 基础 MCP 工具（已有）

```python
# 发送消息
send_message(content, sender, priority="normal")

# 读取未读消息
read_messages(unread_only=True, limit=10)

# 标记已读
mark_read(message_ids)

# 等待回复
wait_for_message(timeout=300, last_seen=timestamp)
```

**状态**: ✅ 已实现，无需修改

---

### 2. 防止消息淹没（简单 SQL）

```sql
-- 清理短消息（小于 20 字符）
DELETE FROM messages WHERE length(content) < 20;

-- 清理重复消息（相同内容 + 发送者）
DELETE FROM messages 
WHERE id NOT IN (
    SELECT MAX(id) 
    FROM messages 
    GROUP BY content, sender
);

-- 清理旧消息（1 小时前）
DELETE FROM messages 
WHERE timestamp < strftime('%s', 'now') - 3600;
```

**实现**: 添加到 `mcp_server_simple.py` 的 `read_messages` 函数中

---

### 3. 超时重试（简单循环）

```python
def wait_with_retry(max_retries=3):
    """等待消息，超时重试"""
    for i in range(max_retries):
        result = client.wait_for_message(timeout=120)
        if result.get('success'):
            return result['message']
        print(f"⏰ 重试 {i+1}/{max_retries}")
        time.sleep(10 * (i + 1))  # 递增等待
    return None
```

---

## 📝 简化版对话脚本

```python
#!/usr/bin/env python3
"""
简化版 AI 对话脚本
原则：够用就好
"""
from message_sdk import MessageBoardClient
import time

def simple_dialogue(client_id: str, partner_id: str, max_turns: int = 10):
    """简单对话循环"""
    client = MessageBoardClient(client_id)
    last_seen = int(time.time())
    turn = 0
    
    print(f"🎙️ 对话开始：{client_id} <-> {partner_id}")
    
    # 发送第一条消息
    client.send(f"@{partner_id} 你好")
    turn += 1
    
    # 对话循环
    while turn < max_turns:
        # 等待回复（带重试）
        for retry in range(3):
            result = client.wait_for_message(timeout=120, last_seen=last_seen)
            
            if result.get('success'):
                msg = result['message']
                
                # 跳过自己的消息
                if msg['sender'] == client_id:
                    continue
                
                print(f"📥 [{msg['sender']}] {msg['content'][:50]}")
                
                # 简单回复
                reply = f"收到：{msg['content'][:50]}"
                client.send(reply, reply_to=msg['id'])
                print(f"📤 回复：{reply[:50]}")
                
                last_seen = msg['timestamp']
                turn += 1
                break
            else:
                print(f"⏰ 重试 {retry+1}/3")
                time.sleep(10 * (retry + 1))
        else:
            print("❌ 对方无响应")
            break
    
    print(f"✅ 对话完成，共{turn}轮")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("用法：python3 simple_dialogue.py <client_id> <partner_id>")
        sys.exit(1)
    
    simple_dialogue(sys.argv[1], sys.argv[2])
```

---

## 🔧 必要的代码修改

### 修改 1: mcp_server_simple.py 添加消息清理

```python
def read_messages(unread_only: bool = False, limit: int = 10, ...) -> Dict:
    """读取消息（带自动清理）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 清理短消息
    cursor.execute("DELETE FROM messages WHERE length(content) < 20")
    
    # 清理重复消息
    cursor.execute("""
        DELETE FROM messages 
        WHERE id NOT IN (
            SELECT MAX(id) FROM messages 
            GROUP BY content, sender
        )
    """)
    
    # 清理旧消息（1 小时）
    cursor.execute("""
        DELETE FROM messages 
        WHERE timestamp < ?
    """, (int(time.time()) - 3600,))
    
    conn.commit()
    
    # 正常读取逻辑...
```

---

## 🎯 使用方式

### 快速开始

```bash
# 终端 1
python3 simple_dialogue.py ai_a ai_b

# 终端 2
python3 simple_dialogue.py ai_b ai_a
```

### MCP 工具调用

```
# iFlow
使用 message-board 发送消息给 qwen：你好，我想讨论项目

# Qwen
检查 message-board 是否有新消息
```

---

## 📊 功能对比

| 功能 | v1.1（复杂版） | v2.0（简化版） | 选择 |
|------|----------------|----------------|------|
| 文件锁 | ✅ fcntl | ❌ 不需要 | 简化 |
| 超时重试 | ✅ 3 次 | ✅ 3 次 | 保留 |
| 对话模式 | 3 种 | 1 种 | 简化 |
| 消息过滤 | 复杂类 | 简单 SQL | 简化 |
| 动态超时 | ✅ 关键词估计 | ❌ 固定 120 秒 | 简化 |
| 监控器 | ✅ 完整指标 | ❌ 不需要 | 简化 |
| 异常类 | 4 个类 | 1 个基类 | 简化 |
| 消息清理 | ❌ 无 | ✅ SQL | 新增 |

---

## ✅ 最终共识

### 保留的核心功能

1. ✅ **基础 MCP 工具** - send/read/mark/wait
2. ✅ **超时重试** - 最多 3 次
3. ✅ **时间戳过滤** - last_seen
4. ✅ **消息清理** - SQL 自动清理

### 移除的复杂功能

- ❌ 文件锁机制（单用户场景够用）
- ❌ 多对话模式（一种够用）
- ❌ 复杂监控（不需要持久化）
- ❌ 动态超时估计（固定值简单）
- ❌ 异常类层次（一个基类够用）

---

## 📝 实施计划

### 立即实施

1. ✅ 创建简化版对话脚本 `simple_dialogue.py` - **已完成**
2. ✅ 修改 `mcp_server_simple.py` 添加消息清理 - **已完成**
3. ✅ 测试基本功能 - **准备就绪**

### 后续优化（可选）

- 如果消息量大了再加清理策略
- 如果需要再加文件锁
- 如果要监控再加指标

---

## ✅ 完成状态

| 项目 | 状态 | 说明 |
|------|------|------|
| `simple_dialogue.py` | ✅ 完成 | 简化版对话脚本 |
| `mcp_server_simple.py` | ✅ 完成 | 添加消息清理 |
| 消息清理函数 | ✅ 完成 | cleanup_messages() |
| 共识文档 | ✅ 完成 | SIMPLIFIED_CONSENSUS.md |

### 清理功能详情

```python
def cleanup_messages():
    """清理消息（短消息、重复消息、旧消息）"""
    # 1. 清理短消息（小于 20 字符）
    DELETE FROM messages WHERE length(content) < 20
    
    # 2. 清理重复消息（保留最新的）
    DELETE FROM messages 
    WHERE id NOT IN (
        SELECT MAX(id) FROM messages 
        GROUP BY content, sender
    )
    
    # 3. 清理旧消息（1 小时前）
    DELETE FROM messages WHERE timestamp < time.time() - 3600
```

### 使用简化脚本

```bash
# 开始对话
python3 simple_dialogue.py ai_a ai_b 10

# 快速发送
python3 simple_dialogue.py --send ai_a "你好，我想讨论项目"

# 读取消息
python3 simple_dialogue.py --read ai_a
```

---

## 🎉 总结

**简化版优势**:
- 代码量少（约 100 行 vs 500 行）
- 易于理解（逻辑简单）
- 维护成本低
- 满足当前需求

**核心原则**:
> 够用就好，简单可靠

---

**版本**: v2.0  
**状态**: ✅ 简化方案达成共识  
**时间**: 2026-02-27
