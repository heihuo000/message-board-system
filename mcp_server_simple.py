#!/usr/bin/env python3
"""
简化的 Message Board MCP Server
不依赖 mcp 包，使用 JSON-RPC 2.0 协议

## 调用说明

### 1. 发送消息（非阻塞）
```python
send_message(content="你好", sender="iflow", priority="normal")
```

### 2. 进入等待并阻塞接收消息（推荐）
```python
# 自动注册等待状态 → 阻塞等待 → 收到消息自动取消 → 返回
result = wait_for_message(
    timeout=300,        # 超时时间（秒）
    client_id="qwen",   # 你的代理ID（必填）
    agent_type="qwen",  # 代理类型（可选，默认从client_id推断）
    capabilities='["code"]'  # 能力描述（可选）
)
```

### 3. 代理工作流程
```python
# 循环：等待 → 收到任务 → 执行 → 发送完成 → 继续等待
while True:
    # 步骤1：进入等待（自动注册）
    result = wait_for_message(timeout=300, client_id="qwen")
    
    if result.get("success"):
        # 步骤2：收到任务，执行
        message = result["message"]
        # ... 执行业务逻辑 ...
        
        # 步骤3：任务完成，发送通知
        send_message(content="任务完成", sender="qwen")
    
    # 步骤4：循环继续（自动重新注册）
```

### 4. 任务分配者流程
```python
# 步骤1：查询等待中的代理
waiting = get_waiting_agents()

# 步骤2：选择代理并创建任务
if waiting['waiting_agents']:
    agent = waiting['waiting_agents'][0]
    create_task(title="分析代码", assigned_to=agent['agent_id'], created_by="iflow")
    
    # 步骤3：发送任务通知
    send_message(content=f"新任务: {task_id}", sender="iflow")
```

## 重要提示
- ⚠️ 直接 SQL 插入消息时必须生成 UUID 作为 ID
- ⚠️ wait_for_message 会自动管理等待状态，无需手动调用 register_waiting
- ⚠️ 消息建议控制在 100 字以内，超过内容写到文件
- ⚠️ 必须使用固定的代理 ID：iflow, qwen, dnf-pvf-analyse, pvf-analyzer
"""
import sys
import json
import sqlite3
import uuid
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# 配置
DB_PATH = Path("~/.message_board/board.db").expanduser()


def get_db_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def send_message(content: str, sender: str = "unknown", priority: str = "normal", 
                 reply_to: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    发送消息
    
    Args:
        content: 消息内容
        sender: 发送者ID
        priority: 优先级
        reply_to: 回复的消息ID
        session_id: 会话ID（用于区分同一代理的不同实例）
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    message_id = str(uuid.uuid4())
    timestamp = int(time.time())
    
    # 如果没有提供session_id，自动生成一个
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # 将session_id存储到content前缀中（临时方案）
    # 更好的方案是修改数据库表添加session_id字段
    prefixed_content = f"[session:{session_id}] {content}"
    
    cursor.execute("""
        INSERT INTO messages (id, sender, content, timestamp, read, reply_to, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (message_id, sender, prefixed_content, timestamp, 0, reply_to, priority))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "message_id": message_id,
        "timestamp": timestamp,
        "session_id": session_id
    }


def cleanup_messages():
    """清理消息（短消息、重复消息、旧消息）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 清理短消息（小于 20 字符）
    cursor.execute("DELETE FROM messages WHERE length(content) < 20")
    short_count = cursor.rowcount
    
    # 清理重复消息（保留最新的）
    cursor.execute("""
        DELETE FROM messages 
        WHERE id NOT IN (
            SELECT MAX(id) FROM messages 
            GROUP BY content, sender
        )
    """)
    dup_count = cursor.rowcount
    
    # 清理旧消息（1 小时前）
    cutoff = int(time.time()) - 3600
    cursor.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff,))
    old_count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    return short_count, dup_count, old_count


def read_messages(unread_only: bool = False, limit: int = 10,
                  sender: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    读取消息（带自动清理）
    
    Args:
        unread_only: 是否只读取未读消息
        limit: 限制数量
        sender: 筛选发送者
        session_id: 筛选特定会话的消息
    """
    # 先清理
    cleanup_messages()
    
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM messages WHERE 1=1"
    params = []

    if unread_only:
        query += " AND read = 0"
    if sender:
        query += " AND sender = ?"
        params.append(sender)
    if session_id:
        query += " AND content LIKE ?"
        params.append(f"%[session:{session_id}]%")

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    messages = []
    for row in rows:
        content = row["content"]
        msg_session_id = None
        
        # 解析session_id
        if content.startswith("[session:"):
            try:
                session_start = content.index("[session:")
                session_end = content.index("]", session_start)
                msg_session_id = content[session_start + 9:session_end]
                content = content[session_end + 2:].strip()  # 移除session前缀
            except ValueError:
                pass  # 解析失败，保持原样
        
        messages.append({
            "id": row["id"],
            "sender": row["sender"],
            "content": content,
            "timestamp": row["timestamp"],
            "read": bool(row["read"]),
            "priority": row["priority"] or "normal",
            "session_id": msg_session_id
        })

    return {
        "success": True,
        "messages": messages,
        "count": len(messages)
    }


def wait_for_message(timeout: int = 300, last_seen: Optional[int] = None, client_id: Optional[str] = None,
                     session_id: Optional[str] = None, agent_type: Optional[str] = None,
                     capabilities: Optional[str] = None, status: str = "idle",
                     task_id: Optional[str] = None, progress: Optional[int] = None,
                     expected_wait: Optional[int] = None) -> Dict[str, Any]:
    """
    等待新消息（阻塞等待）

    Args:
        timeout: 超时时间（秒），默认 5 分钟
        last_seen: 最后看到的消息时间戳，只返回更新的消息
        client_id: 客户端ID，过滤掉自己的消息。如果提供，会自动注册等待状态
        session_id: 会话ID，只等待特定会话的消息（用于区分同一代理的不同实例）
        agent_type: 代理类型（iflow、qwen、dnf-pvf-analyse、pvf-analyzer）。如果未提供，会从 client_id 推断
        capabilities: 能力描述（JSON字符串）
        status: 状态（idle=空闲等待，working=任务执行中等待，waiting=任务中等待条件）
        task_id: 当前任务ID（可选，提供后管理者可以知道代理在处理哪个任务）
        progress: 任务进度 0-100（可选，提供后管理者可以了解任务完成度）
        expected_wait: 预期等待时间（秒，可选，提供后管理者可以判断是否超时）

    Returns:
        新消息或超时信息
    """
    start_time = time.time()
    checked_ids = set()

    # 自动注册等待状态（如果提供了 client_id）
    if client_id:
        # 如果没有提供 agent_type，从 client_id 推断
        if not agent_type:
            # 从 client_id 提取基础类型（如 iflow1 → iflow）
            import re
            match = re.match(r'^([a-z-]+)', client_id)
            if match:
                agent_type = match.group(1)
            else:
                agent_type = "generic"

        # 注册等待状态（包含完整上下文信息）
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            now = int(time.time())
            waiting_id = f"wait_{client_id}_{now}"
            
            cursor.execute("""
                INSERT OR REPLACE INTO waiting_agents 
                (id, agent_id, agent_type, waiting_since, capabilities, status, current_task_id, heartbeat, is_online)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (waiting_id, client_id, agent_type, now, capabilities, status, task_id, now))
            
            # 如果提供了任务ID和进度，更新任务
            if task_id and progress is not None:
                cursor.execute("""
                    UPDATE tasks SET progress = ?, updated_at = ? WHERE id = ?
                """, (progress, now, task_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            # 注册失败不影响等待功能
            pass
        except Exception as e:
            # 注册失败不影响等待功能
            pass
    
    try:
        while time.time() - start_time < timeout:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 查询未读消息
            query = "SELECT * FROM messages WHERE read = 0"
            params = []
            
            # 过滤发送者（不返回自己的消息）
            if client_id:
                query += " AND sender != ?"
                params.append(client_id)
            
            # 过滤会话ID（如果指定）
            if session_id:
                query += " AND content LIKE ?"
                params.append(f"%[session:{session_id}]%")
            
            if last_seen:
                query += " AND timestamp > ?"
                params.append(last_seen)
            
            # 排除已检查的消息
            if checked_ids:
                placeholders = ",".join(["?" for _ in checked_ids])
                query += f" AND id NOT IN ({placeholders})"
                params.extend(list(checked_ids))
            
            query += " ORDER BY timestamp ASC LIMIT 1"
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # 发现新消息
                checked_ids.add(row["id"])
                
                # 解析session_id
                content = row["content"]
                msg_session_id = None
                if content.startswith("[session:"):
                    try:
                        session_start = content.index("[session:")
                        session_end = content.index("]", session_start)
                        msg_session_id = content[session_start + 9:session_end]
                        content = content[session_end + 2:].strip()
                    except ValueError:
                        pass
                
                return {
                    "success": True,
                    "message": {
                        "id": row["id"],
                        "sender": row["sender"],
                        "content": content,
                        "timestamp": row["timestamp"],
                        "read": bool(row["read"]),
                        "priority": row["priority"] or "normal",
                        "session_id": msg_session_id
                    },
                    "wait_time": time.time() - start_time
                }
            
            # 动态轮询间隔策略
            # 前30秒：快速轮询（0.5秒）- 降低响应延迟
            # 30秒后：慢速轮询（5秒）- 降低资源消耗
            elapsed = time.time() - start_time
            if elapsed < 30:
                time.sleep(0.5)  # 快速响应
            else:
                time.sleep(5)    # 节省资源
        
        # 超时
        return {
            "success": False,
            "timeout": True,
            "wait_time": timeout
        }
    finally:
        # 取消等待状态（无论返回什么）
        if client_id:
            try:
                unregister_waiting(agent_id=client_id)
            except Exception as e:
                # 取消失败不影响返回结果
                pass


def mark_read(message_ids: List[str]) -> Dict[str, Any]:
    """标记消息已读"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    placeholders = ",".join(["?" for _ in message_ids])
    cursor.execute(
        f"UPDATE messages SET read = 1 WHERE id IN ({placeholders})",
        message_ids
    )
    
    count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "count": count
    }


def get_status() -> Dict[str, Any]:
    """获取状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages WHERE read = 0")
    unread = cursor.fetchone()[0]
    
    cursor.execute("SELECT MAX(timestamp) FROM messages")
    latest = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "success": True,
        "stats": {
            "total_messages": total,
            "unread_messages": unread,
            "latest_message_time": datetime.fromtimestamp(latest).strftime("%Y-%m-%d %H:%M:%S") if latest else None
        }
    }


def get_protocol() -> Dict[str, Any]:
    """获取协议文档"""
    protocol_path = Path(__file__).parent / "MCP_COMMUNICATION_PROTOCOL.md"
    if protocol_path.exists():
        with open(protocol_path, 'r', encoding='utf-8') as f:
            protocol_content = f.read()
        return {
            "success": True,
            "protocol": protocol_content,
            "length": len(protocol_content),
            "source": "MCP_COMMUNICATION_PROTOCOL.md"
        }
    else:
        return {
            "success": False,
            "error": "协议文档不存在",
            "expected_path": str(protocol_path)
        }


def create_task(title: str, description: str = "", assigned_to: str = "unknown", 
                created_by: str = "unknown", priority: str = "normal") -> Dict[str, Any]:
    """创建任务"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    task_id = str(uuid.uuid4())
    now = int(time.time())
    
    cursor.execute("""
        INSERT INTO tasks (id, title, description, status, assigned_to, created_by, priority, created_at, updated_at)
        VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?)
    """, (task_id, title, description, assigned_to, created_by, priority, now, now))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "task_id": task_id,
        "created_at": now
    }


def update_task(task_id: str, status: Optional[str] = None, result: Optional[str] = None) -> Dict[str, Any]:
    """更新任务状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = int(time.time())
    
    # 构建动态更新语句
    updates = []
    params = []
    
    if status:
        updates.append("status = ?")
        params.append(status)
        # 更新完成时间
        if status == "completed":
            updates.append("completed_at = ?")
            params.append(now)
    
    if result:
        updates.append("result = ?")
        params.append(result)
    
    if updates:
        updates.append("updated_at = ?")
        params.append(now)
        params.append(task_id)
        
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
    
    count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "updated": count > 0,
        "updated_at": now
    }


def get_tasks(assigned_to: Optional[str] = None, status: Optional[str] = None, 
              limit: int = 10) -> Dict[str, Any]:
    """获取任务列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    
    if assigned_to:
        query += " AND assigned_to = ?"
        params.append(assigned_to)
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    tasks = []
    for row in rows:
        tasks.append({
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "status": row["status"],
            "assigned_to": row["assigned_to"],
            "created_by": row["created_by"],
            "priority": row["priority"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "result": row["result"]
        })
    
    return {
        "success": True,
        "tasks": tasks,
        "count": len(tasks)
    }


def get_my_tasks(agent_id: str, status: Optional[str] = None, 
                 limit: int = 20) -> Dict[str, Any]:
    """
    查询自己的任务历史
    
    Args:
        agent_id: 代理ID
        status: 筛选状态（可选）
        limit: 返回数量
    
    Returns:
        自己的任务历史
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查询作为执行者的任务
    query = "SELECT * FROM tasks WHERE assigned_to = ?"
    params = [agent_id]
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    tasks = []
    for row in rows:
        tasks.append({
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "status": row["status"],
            "assigned_to": row["assigned_to"],
            "created_by": row["created_by"],
            "priority": row["priority"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "result": row["result"]
        })
    
    return {
        "success": True,
        "agent_id": agent_id,
        "tasks": tasks,
        "count": len(tasks)
    }


def register_waiting(agent_id: str, agent_type: str = "generic",
                     capabilities: Optional[str] = None, status: str = "idle") -> Dict[str, Any]:
    """
    注册等待状态（进入等待队列）

    Args:
        agent_id: 代理ID（如 iflow1、qwen2）
        agent_type: 代理类型（iflow、qwen、dnf-pvf-analyse、pvf-analyzer）
        capabilities: 能力描述（JSON字符串，如 ["code","test"]）
        status: 状态（idle=空闲等待, working=任务执行中等待）

    Returns:
        注册结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    waiting_id = f"wait_{agent_id}_{int(time.time())}"
    waiting_since = int(time.time())

    # 使用REPLACE实现"已存在则更新，不存在则插入"
    cursor.execute("""
        INSERT OR REPLACE INTO waiting_agents (id, agent_id, agent_type, waiting_since, capabilities, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (waiting_id, agent_id, agent_type, waiting_since, capabilities, status))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "agent_id": agent_id,
        "waiting_since": waiting_since,
        "status": status,
        "message": f"{agent_id} 已进入等待状态 ({status})"
    }


def unregister_waiting(agent_id: str) -> Dict[str, Any]:
    """
    取消等待状态（收到任务后调用）
    
    Args:
        agent_id: 代理ID
    
    Returns:
        取消结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM waiting_agents WHERE agent_id = ?", (agent_id,))
    
    count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "agent_id": agent_id,
        "removed": count > 0,
        "message": f"{agent_id} 已退出等待状态" if count > 0 else f"{agent_id} 不在等待状态"
    }


def report_status(agent_id: str, status: str, task_id: Optional[str] = None,
                 progress: Optional[str] = None) -> Dict[str, Any]:
    """
    报告代理工作状态

    Args:
        agent_id: 代理ID（必填）
        status: 状态（idle=空闲, working=工作中, waiting=任务中等待）
        task_id: 当前任务ID（可选，工作中时提供）
        progress: 进度描述（可选）

    Returns:
        报告结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 更新等待列表中的状态
    cursor.execute("""
        UPDATE waiting_agents SET status = ?, waiting_since = ?
        WHERE agent_id = ?
    """, (status, int(time.time()), agent_id))

    # 如果提供了任务ID，更新任务状态
    if task_id:
        task_status = "running" if status == "working" else "pending"
        cursor.execute("""
            UPDATE tasks SET status = ? WHERE id = ?
        """, (task_status, task_id))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "agent_id": agent_id,
        "status": status,
        "task_id": task_id,
        "progress": progress,
        "message": f"{agent_id} 状态已更新为 {status}"
    }


def heartbeat(agent_id: str, task_id: Optional[str] = None, progress: Optional[int] = None) -> Dict[str, Any]:
    """
    发送心跳信号，证明代理存活并更新进度

    Args:
        agent_id: 代理ID（必填）
        task_id: 当前任务ID（可选）
        progress: 任务进度 0-100（可选）

    Returns:
        心跳结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    now = int(time.time())

    # 更新等待列表中的心跳时间
    cursor.execute("""
        UPDATE waiting_agents SET heartbeat = ?, current_task_id = ?
        WHERE agent_id = ?
    """, (now, task_id, agent_id))

    # 如果提供了任务ID和进度，更新任务
    if task_id and progress is not None:
        cursor.execute("""
            UPDATE tasks SET progress = ?, updated_at = ? WHERE id = ?
        """, (progress, now, task_id))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "agent_id": agent_id,
        "heartbeat": now,
        "task_id": task_id,
        "progress": progress,
        "message": f"{agent_id} 心跳已更新"
    }


def cancel_task(task_id: str) -> Dict[str, Any]:
    """
    取消任务

    Args:
        task_id: 任务ID（必填）

    Returns:
        取消结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    now = int(time.time())

    # 更新任务状态为已取消
    cursor.execute("""
        UPDATE tasks SET status = 'failed', error_message = '任务已取消', completed_at = ? WHERE id = ?
    """, (now, task_id))

    count = cursor.rowcount
    conn.commit()
    conn.close()

    return {
        "success": True,
        "cancelled": count > 0,
        "task_id": task_id,
        "message": f"任务 {task_id} 已取消" if count > 0 else f"任务 {task_id} 不存在"
    }


def get_task_details(task_id: str) -> Dict[str, Any]:
    """
    获取任务详细信息

    Args:
        task_id: 任务ID（必填）

    Returns:
        任务详情
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "success": False,
            "error": "任务不存在"
        }

    row_dict = dict(row)
    return {
        "success": True,
        "task": {
            "id": row_dict["id"],
            "title": row_dict["title"],
            "description": row_dict["description"],
            "status": row_dict["status"],
            "assigned_to": row_dict["assigned_to"],
            "created_by": row_dict["created_by"],
            "priority": row_dict["priority"],
            "progress": row_dict.get("progress", 0),
            "created_at": row_dict["created_at"],
            "updated_at": row_dict["updated_at"],
            "started_at": row_dict.get("started_at"),
            "completed_at": row_dict.get("completed_at"),
            "error_message": row_dict.get("error_message"),
            "result": row_dict.get("result")
        }
    }


def get_agent_status(agent_id: str) -> Dict[str, Any]:
    """
    获取代理详细状态

    Args:
        agent_id: 代理ID（必填）

    Returns:
        代理状态
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 查询等待状态
    cursor.execute("SELECT * FROM waiting_agents WHERE agent_id = ?", (agent_id,))
    waiting_row = cursor.fetchone()

    # 查询任务
    cursor.execute("""
        SELECT id, title, status, progress, created_at FROM tasks
        WHERE assigned_to = ? AND status IN ('pending', 'running')
        ORDER BY created_at DESC
    """, (agent_id,))
    task_rows = cursor.fetchall()

    conn.close()

    return {
        "success": True,
        "agent_id": agent_id,
        "waiting": waiting_row is not None,
        "waiting_status": dict(waiting_row)["status"] if waiting_row else None,
        "current_task_id": dict(waiting_row)["current_task_id"] if waiting_row else None,
        "heartbeat": dict(waiting_row)["heartbeat"] if waiting_row else None,
        "active_tasks": len(task_rows),
        "tasks": [dict(row) for row in task_rows]
    }


def get_system_stats() -> Dict[str, Any]:
    """
    获取系统统计信息

    Returns:
        系统统计
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    now = int(time.time())

    # 消息统计
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM messages WHERE read = 0")
    unread_messages = cursor.fetchone()[0]

    # 任务统计
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
    pending_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'running'")
    running_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
    completed_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'")
    failed_tasks = cursor.fetchone()[0]

    # 代理统计
    cursor.execute("SELECT COUNT(*) FROM waiting_agents")
    waiting_agents = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM waiting_agents WHERE status = 'idle'")
    idle_agents = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM waiting_agents WHERE status = 'working'")
    working_agents = cursor.fetchone()[0]

    # 检查超时代理（心跳超过60秒）
    cursor.execute("SELECT COUNT(*) FROM waiting_agents WHERE heartbeat < ?", (now - 60,))
    timeout_agents = cursor.fetchone()[0]

    conn.close()

    return {
        "success": True,
        "timestamp": now,
        "messages": {
            "total": total_messages,
            "unread": unread_messages
        },
        "tasks": {
            "pending": pending_tasks,
            "running": running_tasks,
            "completed": completed_tasks,
            "failed": failed_tasks,
            "total": pending_tasks + running_tasks + completed_tasks + failed_tasks
        },
        "agents": {
            "waiting": waiting_agents,
            "idle": idle_agents,
            "working": working_agents,
            "timeout": timeout_agents
        }
    }


def check_offline_agents(timeout_seconds: int = 120) -> Dict[str, Any]:
    """
    检测并标记下线代理
    
    Args:
        timeout_seconds: 超时时间（秒），默认120秒
    
    Returns:
        下线代理信息和重新分配建议
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = int(time.time())
    
    # 查找超时的代理
    cursor.execute("""
        SELECT agent_id, current_task_id, status, heartbeat 
        FROM waiting_agents 
        WHERE heartbeat < ?
        ORDER BY heartbeat ASC
    """, (now - timeout_seconds,))
    
    offline_agents = []
    for row in cursor.fetchall():
        agent_id, current_task_id, status, heartbeat = row
        
        # 标记为下线
        cursor.execute("""
            UPDATE waiting_agents 
            SET is_online = 0, last_disconnect = ?
            WHERE agent_id = ?
        """, (now, agent_id))
        
        # 如果有正在执行的任务，标记为失败
        if current_task_id:
            cursor.execute("""
                UPDATE tasks 
                SET status = 'failed', error_message = '代理下线', completed_at = ?
                WHERE id = ? AND status = 'running'
            """, (now, current_task_id))
        
        offline_agents.append({
            "agent_id": agent_id,
            "current_task_id": current_task_id,
            "status": status,
            "last_heartbeat": heartbeat,
            "offline_duration": now - heartbeat
        })
    
    # 查找需要重新分配的任务
    cursor.execute("""
        SELECT id, title, assigned_to 
        FROM tasks 
        WHERE status = 'pending' OR status = 'failed'
        ORDER BY created_at ASC
    """)
    
    unassigned_tasks = []
    for row in cursor.fetchall():
        task_id, title, assigned_to = row
        unassigned_tasks.append({
            "task_id": task_id,
            "title": title,
            "assigned_to": assigned_to
        })
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "timestamp": now,
        "offline_agents": offline_agents,
        "offline_count": len(offline_agents),
        "unassigned_tasks": unassigned_tasks,
        "unassigned_count": len(unassigned_tasks)
    }


def get_waiting_agents(agent_type: Optional[str] = None) -> Dict[str, Any]:
    """
    获取等待中的代理列表（按等待时间排序）
    
    Args:
        agent_type: 筛选特定类型的代理（可选）
    
    Returns:
        等待中的代理列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM waiting_agents WHERE 1=1"
    params = []
    
    if agent_type:
        query += " AND agent_type = ?"
        params.append(agent_type)
    
    query += " ORDER BY waiting_since ASC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    agents = []
    for row in rows:
        row_dict = dict(row)
        now = int(time.time())
        heartbeat_age = now - row_dict.get("heartbeat", 0) if row_dict.get("heartbeat") else None
        agents.append({
            "id": row_dict["id"],
            "agent_id": row_dict["agent_id"],
            "agent_type": row_dict["agent_type"],
            "waiting_since": row_dict["waiting_since"],
            "waiting_duration": now - row_dict["waiting_since"],
            "capabilities": row_dict["capabilities"],
            "status": row_dict.get("status", "idle"),
            "current_task_id": row_dict.get("current_task_id"),
            "heartbeat": row_dict.get("heartbeat"),
            "heartbeat_age": heartbeat_age,
            "is_timeout": heartbeat_age > 60 if heartbeat_age else False
        })
    
    return {
        "success": True,
        "waiting_agents": agents,
        "count": len(agents),
        "agent_type": agent_type
    }


# 工具映射
TOOLS = {
    "send_message": {
        "description": "发送消息到留言簿。用于AI代理之间通信、发送任务通知、回复消息等。消息会被记录并可被其他代理读取。",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string", 
                    "description": "消息内容（建议100字以内，长内容请写到文件）"
                },
                "sender": {
                    "type": "string", 
                    "description": "发送者ID（必须使用固定ID：iflow/qwen/dnf-pvf-analyse/pvf-analyzer）"
                },
                "priority": {
                    "type": "string", 
                    "enum": ["normal", "high", "urgent"],
                    "description": "消息优先级：normal(普通), high(重要), urgent(紧急)"
                },
                "reply_to": {
                    "type": "string", 
                    "description": "回复的消息ID（可选，用于回复特定消息）"
                }
            },
            "required": ["content"]
        },
        "handler": send_message
    },
    "read_messages": {
        "description": "读取留言簿消息。用于获取未读消息、历史消息或特定发送者的消息。批量读取可避免漏读消息。",
        "parameters": {
            "type": "object",
            "properties": {
                "unread_only": {
                    "type": "boolean", 
                    "description": "是否只读取未读消息（true=仅未读，false=全部消息）"
                },
                "limit": {
                    "type": "integer", 
                    "description": "限制返回的消息数量（默认10，建议100）"
                },
                "sender": {
                    "type": "string", 
                    "description": "筛选特定发送者的消息（可选）"
                }
            }
        },
        "handler": read_messages
    },
    "wait_for_message": {
        "description": "进入等待状态并阻塞等待新消息。自动注册等待状态（包含状态和任务上下文），阻塞直到收到消息或超时。任务分配者可通过get_waiting_agents查询到代理的完整状态信息。收到消息后自动取消等待状态并返回。",
        "parameters": {
            "type": "object",
            "properties": {
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认300秒（5分钟）"
                },
                "last_seen": {
                    "type": "integer",
                    "description": "最后看到的消息时间戳（可选，只返回比此时间更新的消息）"
                },
                "client_id": {
                    "type": "string",
                    "description": "你的代理ID（必填，如 iflow、qwen。会自动注册到等待列表）"
                },
                "agent_type": {
                    "type": "string",
                    "description": "代理类型（iflow/qwen/dnf-pvf-analyse/pvf-analyzer。可选，默认从client_id推断）"
                },
                "capabilities": {
                    "type": "string",
                    "description": "能力描述（JSON字符串，如 [\"code\",\"test\"]。可选）"
                },
                "session_id": {
                    "type": "string",
                    "description": "会话ID（可选，只等待特定会话的消息）"
                },
                "status": {
                    "type": "string",
                    "enum": ["idle", "working", "waiting"],
                    "description": "等待状态：idle=空闲可接任务（默认），working=任务执行中等待，waiting=任务中等待条件或输入"
                },
                "task_id": {
                    "type": "string",
                    "description": "当前任务ID（可选，强烈建议提供。让管理者知道你在处理哪个任务）"
                },
                "progress": {
                    "type": "integer",
                    "description": "任务进度 0-100（可选，强烈建议提供。让管理者了解任务完成度）"
                },
                "expected_wait": {
                    "type": "integer",
                    "description": "预期等待时间（秒，可选。让管理者判断是否超时）"
                }
            },
            "required": ["client_id"]
        },
        "handler": wait_for_message
    },
    "mark_read": {
        "description": "标记消息为已读。用于标记已处理的消息，避免重复处理。批量标记提高效率。注意：message_ids 是消息的 UUID（如 'abc123-def456...'），不是 timestamp。",
        "parameters": {
            "type": "object",
            "properties": {
                "message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要标记为已读的消息ID列表（UUID格式，如 ['abc123-def456-...', 'xyz789-uvw012-...']）。注意：这是消息的 UUID，不是 timestamp。"
                }
            },
            "required": ["message_ids"]
        },
        "handler": mark_read
    },
    "get_status": {
        "description": "获取留言簿系统状态。包括总消息数、未读消息数、最新消息时间等统计信息。",
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "handler": get_status
    },
    "get_protocol": {
        "description": "获取MCP通信协议文档（最新版）。包含AI代理体系架构、分工调配原则、MCP工具调用顺序、协作流程等完整规范。新代理必须先调用此工具学习协议。",
        "parameters": {
          "type": "object",
          "properties": {}
        },
        "handler": get_protocol
    },
    "create_task": {
        "description": "创建新任务。用于任务分配者（iflow）将任务分配给其他代理。任务会被记录到数据库，可被查询和跟踪。",
        "parameters": {
          "type": "object",
          "properties": {
            "title": {
                "type": "string", 
                "description": "任务标题（简明扼要）"
            },
            "description": {
                "type": "string", 
                "description": "任务详细描述（可选）"
            },
            "assigned_to": {
                "type": "string", 
                "description": "任务分配给谁（必须使用固定ID：iflow/qwen/dnf-pvf-analyse/pvf-analyzer）"
            },
            "created_by": {
                "type": "string", 
                "description": "任务创建者（通常是iflow）"
            },
            "priority": {
                "type": "string", 
                "enum": ["urgent", "high", "normal", "low"],
                "description": "任务优先级"
            }
          },
          "required": ["title"]
        },
        "handler": create_task
    },
    "update_task": {
        "description": "更新任务状态。用于任务执行者更新任务进度和结果。必须提供task_id。",
        "parameters": {
          "type": "object",
          "properties": {
            "task_id": {
                "type": "string", 
                "description": "任务ID（必填）"
            },
            "status": {
                "type": "string", 
                "enum": ["pending", "running", "completed", "failed"],
                "description": "任务状态：pending(待处理), running(执行中), completed(已完成), failed(失败)"
            },
            "result": {
                "type": "string", 
                "description": "任务执行结果（可选，任务完成时填写）"
            }
          },
          "required": ["task_id"]
        },
        "handler": update_task
    },
    "get_tasks": {
        "description": "获取任务列表。用于查询特定条件下的任务，可按分配者、状态筛选。",
        "parameters": {
          "type": "object",
          "properties": {
            "assigned_to": {
                "type": "string", 
                "description": "筛选分配给谁的代理（可选）"
            },
            "status": {
                "type": "string", 
                "description": "筛选任务状态（可选）"
            },
            "limit": {
                "type": "integer", 
                "description": "返回任务数量（默认10）"
            }
          }
        },
        "handler": get_tasks
    },
    "get_my_tasks": {
        "description": "查询自己的任务历史。用于快速找到自己执行过的任务，查看任务状态和结果，了解工作负载。",
        "parameters": {
          "type": "object",
          "properties": {
            "agent_id": {
                "type": "string", 
                "description": "你的代理ID（必填，必须是：iflow/qwen/dnf-pvf-analyse/pvf-analyzer）"
            },
            "status": {
                "type": "string", 
                "description": "筛选任务状态（可选）"
            },
            "limit": {
                "type": "integer", 
                "description": "返回任务数量（默认20）"
            }
          },
          "required": ["agent_id"]
        },
        "handler": get_my_tasks
    },
    
    "unregister_waiting": {
        "description": "取消等待状态。收到任务开始执行时调用此工具，退出等待队列。任务完成后需重新注册等待状态。",
        "parameters": {
          "type": "object",
          "properties": {
            "agent_id": {
                "type": "string",
                "description": "你的代理ID（必填）"
            }
          },
          "required": ["agent_id"]
        },
        "handler": unregister_waiting
    },
    "get_waiting_agents": {
        "description": "获取等待中的代理列表。用于查询哪些代理正在等待任务，以便分配任务给空闲的代理。返回的信息包括代理状态（idle=空闲等待，working=任务执行中等待）。",
        "parameters": {
          "type": "object",
          "properties": {
            "agent_type": {
                "type": "string",
                "description": "筛选特定类型的代理（可选，如 'qwen'）"
            }
          }
        },
        "handler": get_waiting_agents
    },
    "report_status": {
        "description": "报告代理工作状态。用于代理主动更新自己的状态，让任务分配者了解当前工作进度。状态说明：idle=空闲可接任务，working=任务执行中，waiting=任务中等待条件或输入。",
        "parameters": {
          "type": "object",
          "properties": {
            "agent_id": {
                "type": "string",
                "description": "代理ID（必填，如 iflow、qwen）"
            },
            "status": {
                "type": "string",
                "enum": ["idle", "working", "waiting"],
                "description": "状态：idle=空闲可接任务，working=任务执行中，waiting=任务中等待条件或输入"
            },
            "task_id": {
                "type": "string",
                "description": "当前任务ID（可选，working或waiting状态时提供）"
            },
            "progress": {
                "type": "string",
                "description": "进度描述（可选，如 '正在分析文件...'）"
            }
          },
          "required": ["agent_id", "status"]
        },
        "handler": report_status
    },
    "heartbeat": {
        "description": "发送心跳信号，证明代理存活并更新进度。代理应该定期（如每30秒）发送心跳。心跳超过60秒未更新会被标记为超时。",
        "parameters": {
          "type": "object",
          "properties": {
            "agent_id": {
                "type": "string",
                "description": "代理ID（必填，如 iflow、qwen）"
            },
            "task_id": {
                "type": "string",
                "description": "当前任务ID（可选，如果正在执行任务）"
            },
            "progress": {
                "type": "integer",
                "description": "任务进度 0-100（可选）"
            }
          },
          "required": ["agent_id"]
        },
        "handler": heartbeat
    },
    "cancel_task": {
        "description": "取消任务。将任务状态设置为失败，标记为已取消。",
        "parameters": {
          "type": "object",
          "properties": {
            "task_id": {
                "type": "string",
                "description": "任务ID（必填）"
            }
          },
          "required": ["task_id"]
        },
        "handler": cancel_task
    },
    "get_task_details": {
        "description": "获取任务详细信息，包括进度、时间戳、错误信息等。",
        "parameters": {
          "type": "object",
          "properties": {
            "task_id": {
                "type": "string",
                "description": "任务ID（必填）"
            }
          },
          "required": ["task_id"]
        },
        "handler": get_task_details
    },
    "get_agent_status": {
        "description": "获取代理详细状态，包括是否在等待、当前任务、心跳时间、活跃任务列表等。",
        "parameters": {
          "type": "object",
          "properties": {
            "agent_id": {
                "type": "string",
                "description": "代理ID（必填，如 iflow、qwen）"
            }
          },
          "required": ["agent_id"]
        },
        "handler": get_agent_status
    },
    "get_system_stats": {
        "description": "获取系统统计信息，包括消息统计、任务统计、代理统计、超时代理数等。",
        "parameters": {
          "type": "object",
          "properties": {}
        },
        "handler": get_system_stats
    },
    "check_offline_agents": {
        "description": "检测并标记下线代理。心跳超时代理会被标记为下线，其正在执行的任务会被标记为失败。返回需要重新分配的任务列表。",
        "parameters": {
          "type": "object",
          "properties": {
            "timeout_seconds": {
                "type": "integer",
                "description": "超时时间（秒），默认120秒"
            }
          }
        },
        "handler": check_offline_agents
    }
}
# 资源映射
RESOURCES = {
    "protocol://current": {
        "name": "MCP 通信协议",
        "description": "当前版本的 MCP 通信协议文档",
        "mime_type": "text/plain",
        "handler": get_protocol
    }
}


def list_tools() -> Dict[str, Any]:
    """列出所有工具"""
    tools = []
    for name, info in TOOLS.items():
        tools.append({
            "name": name,
            "description": info["description"],
            "inputSchema": info["parameters"]
        })
    
    return {
        "jsonrpc": "2.0",
        "id": None,
        "result": {
            "tools": tools
        }
    }


def list_resources() -> Dict[str, Any]:
    """列出所有资源"""
    resources = []
    for uri, info in RESOURCES.items():
        resources.append({
            "uri": uri,
            "name": info["name"],
            "description": info["description"],
            "mimeType": info["mime_type"]
        })
    
    return {
        "jsonrpc": "2.0",
        "id": None,
        "result": {
            "resources": resources
        }
    }


def read_resource(uri: str) -> Dict[str, Any]:
    """读取资源"""
    if uri not in RESOURCES:
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32602,
                "message": f"Unknown resource: {uri}"
            }
        }
    
    try:
        handler = RESOURCES[uri]["handler"]
        result = handler()
        
        # get_protocol 现在返回工具格式，需要转换为资源格式
        if uri == "protocol://current":
            protocol_text = result.get("protocol", result.get("text", ""))
            return {
                "jsonrpc": "2.0",
                "id": None,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": RESOURCES[uri]["mime_type"],
                            "text": protocol_text
                        }
                    ]
                }
            }
        
        # 其他资源的处理
        return {
            "jsonrpc": "2.0",
            "id": None,
            "result": {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": RESOURCES[uri]["mime_type"],
                        "text": result.get("text", "")
                    }
                ]
            }
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }


def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """调用工具"""
    if name not in TOOLS:
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32601,
                "message": f"Unknown tool: {name}"
            }
        }
    
    try:
        handler = TOOLS[name]["handler"]
        result = handler(**arguments)
        
        return {
            "jsonrpc": "2.0",
            "id": None,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2)
                    }
                ]
            }
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }


def process_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """处理 JSON-RPC 请求"""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    if method == "tools/list":
        response = list_tools()
        response["id"] = request_id
        return response
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        response = call_tool(tool_name, arguments)
        response["id"] = request_id
        return response
    
    elif method == "resources/list":
        response = list_resources()
        response["id"] = request_id
        return response
    
    elif method == "resources/read":
        uri = params.get("uri")
        response = read_resource(uri)
        response["id"] = request_id
        return response
    
    elif method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "serverInfo": {
                    "name": "message-board-server",
                    "version": "1.0.0"
                }
            }
        }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


def main():
    """主循环"""
    # 确保数据库存在
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                read INTEGER DEFAULT 0,
                reply_to TEXT,
                priority TEXT DEFAULT 'normal'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_read ON messages(read)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
        
        # 创建任务表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                assigned_to TEXT NOT NULL,
                created_by TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                result TEXT,
                FOREIGN KEY (assigned_to) REFERENCES agents(id),
                FOREIGN KEY (created_by) REFERENCES agents(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")
        
        # 创建AI代理表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                description TEXT,
                created_at INTEGER NOT NULL
            )
        """)
        
        # 创建等待状态表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS waiting_agents (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                waiting_since INTEGER NOT NULL,
                capabilities TEXT,
                UNIQUE (agent_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_waiting_agents_agent_id ON waiting_agents(agent_id)")
        
        conn.commit()
        conn.close()
    
    # 主循环：读取 stdin，写入 stdout
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            response = process_request(request)
            print(json.dumps(response, ensure_ascii=False), flush=True)
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            print(json.dumps(error_response, ensure_ascii=False), flush=True)
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()