#!/usr/bin/env python3
"""
简化的 Message Board MCP Server
不依赖 mcp 包，使用 JSON-RPC 2.0 协议
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
                     session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    等待新消息（阻塞等待）
    
    Args:
        timeout: 超时时间（秒），默认 5 分钟
        last_seen: 最后看到的消息时间戳，只返回更新的消息
        client_id: 客户端ID，过滤掉自己的消息
        session_id: 会话ID，只等待特定会话的消息（用于区分同一代理的不同实例）
    
    Returns:
        新消息或超时信息
    """
    start_time = time.time()
    checked_ids = set()
    
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
        
        # 等待一段时间后继续检查
        time.sleep(2)
    
    # 超时
    return {
        "success": False,
        "timeout": True,
        "wait_time": timeout
    }


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
    
    if status and result:
        cursor.execute("""
            UPDATE tasks SET status = ?, result = ?, updated_at = ? WHERE id = ?
        """, (status, result, now, task_id))
    elif status:
        cursor.execute("""
            UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?
        """, (status, now, task_id))
    elif result:
        cursor.execute("""
            UPDATE tasks SET result = ?, updated_at = ? WHERE id = ?
        """, (result, now, task_id))
    
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
                     capabilities: Optional[str] = None) -> Dict[str, Any]:
    """
    注册等待状态（进入等待队列）
    
    Args:
        agent_id: 代理ID（如 iflow1、qwen2）
        agent_type: 代理类型（iflow、qwen、dnf-pvf-analyse、pvf-analyzer）
        capabilities: 能力描述（JSON字符串，如 ["code","test"]）
    
    Returns:
        注册结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    waiting_id = f"wait_{agent_id}_{int(time.time())}"
    waiting_since = int(time.time())
    
    # 使用REPLACE实现"已存在则更新，不存在则插入"
    cursor.execute("""
        INSERT OR REPLACE INTO waiting_agents (id, agent_id, agent_type, waiting_since, capabilities)
        VALUES (?, ?, ?, ?, ?)
    """, (waiting_id, agent_id, agent_type, waiting_since, capabilities))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "agent_id": agent_id,
        "waiting_since": waiting_since,
        "message": f"{agent_id} 已进入等待状态"
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
        agents.append({
            "id": row["id"],
            "agent_id": row["agent_id"],
            "agent_type": row["agent_type"],
            "waiting_since": row["waiting_since"],
            "waiting_duration": int(time.time()) - row["waiting_since"],
            "capabilities": row["capabilities"]
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
        "description": "等待新消息（阻塞式）。用于接收其他代理发送的消息，会自动过滤自己的消息。收到消息后立即返回，超时返回超时信息。",
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
                    "description": "你的代理ID（用于过滤自己的消息，必须提供）"
                }
            }
        },
        "handler": wait_for_message
    },
    "mark_read": {
        "description": "标记消息为已读。用于标记已处理的消息，避免重复处理。批量标记提高效率。",
        "parameters": {
            "type": "object",
            "properties": {
                "message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要标记为已读的消息ID列表"
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
    "register_waiting": {
        "description": "注册等待状态。进入等待队列前调用此工具，表示自己已准备好接收任务。其他代理可以查询到你的等待状态并分配任务。",
        "parameters": {
          "type": "object",
          "properties": {
            "agent_id": {
                "type": "string",
                "description": "你的代理ID（必填，如 iflow1、qwen2）"
            },
            "agent_type": {
                "type": "string",
                "description": "代理类型（iflow/qwen/dnf-pvf-analyse/pvf-analyzer）"
            },
            "capabilities": {
                "type": "string",
                "description": "能力描述（JSON字符串，可选，如 '[\"code\",\"test\"]'）"
            }
          },
          "required": ["agent_id"]
        },
        "handler": register_waiting
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
        "description": "获取等待中的代理列表。用于查询哪些代理正在等待任务，以便分配任务给空闲的代理。",
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