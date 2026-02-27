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
                 reply_to: Optional[str] = None) -> Dict[str, Any]:
    """发送消息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    message_id = str(uuid.uuid4())
    timestamp = int(time.time())
    
    cursor.execute("""
        INSERT INTO messages (id, sender, content, timestamp, read, reply_to, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (message_id, sender, content, timestamp, 0, reply_to, priority))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "message_id": message_id,
        "timestamp": timestamp
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
                  sender: Optional[str] = None) -> Dict[str, Any]:
    """读取消息（带自动清理）"""
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

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    messages = [
        {
            "id": row["id"],
            "sender": row["sender"],
            "content": row["content"],
            "timestamp": row["timestamp"],
            "read": bool(row["read"]),
            "priority": row["priority"] or "normal"
        }
        for row in rows
    ]

    return {
        "success": True,
        "messages": messages,
        "count": len(messages)
    }


def wait_for_message(timeout: int = 300, last_seen: Optional[int] = None, client_id: Optional[str] = None) -> Dict[str, Any]:
    """
    等待新消息（阻塞等待）
    
    Args:
        timeout: 超时时间（秒），默认 5 分钟
        last_seen: 最后看到的消息时间戳，只返回更新的消息
        client_id: 客户端ID，过滤掉自己的消息
    
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
            return {
                "success": True,
                "message": {
                    "id": row["id"],
                    "sender": row["sender"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "read": bool(row["read"]),
                    "priority": row["priority"] or "normal"
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
            "uri": "protocol://current",
            "text": protocol_content
        }
    else:
        return {
            "uri": "protocol://current",
            "text": "协议文档不存在"
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


# 工具映射
TOOLS = {
    "send_message": {
        "description": "发送消息到留言簿",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "消息内容"},
                "sender": {"type": "string", "description": "发送者 ID"},
                "priority": {"type": "string", "enum": ["normal", "high", "urgent"]},
                "reply_to": {"type": "string", "description": "回复的消息 ID"}
            },
            "required": ["content"]
        },
        "handler": send_message
    },
    "read_messages": {
        "description": "读取留言簿消息",
        "parameters": {
            "type": "object",
            "properties": {
                "unread_only": {"type": "boolean", "description": "只读未读消息"},
                "limit": {"type": "integer", "description": "限制数量"},
                "sender": {"type": "string", "description": "发送者过滤"}
            }
        },
        "handler": read_messages
    },
    "wait_for_message": {
        "description": "等待新消息（阻塞等待，有消息立即返回）",
        "parameters": {
            "type": "object",
            "properties": {
                "timeout": {"type": "integer", "description": "超时时间（秒），默认 300"},
                "last_seen": {"type": "integer", "description": "最后看到的消息时间戳"}
            }
        },
        "handler": wait_for_message
    },
    "mark_read": {
        "description": "标记消息已读",
        "parameters": {
            "type": "object",
            "properties": {
                "message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "消息 ID 列表"
                }
            },
            "required": ["message_ids"]
        },
        "handler": mark_read
    },
    "get_status": {
        "description": "获取系统状态",
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "handler": get_status
    },
    "get_protocol": {
            "description": "获取 MCP 通信协议文档",
            "parameters": {
              "type": "object",
              "properties": {}
            },
            "handler": get_protocol
        },
        "create_task": {
            "description": "创建新任务",
            "parameters": {
              "type": "object",
              "properties": {
                "title": {"type": "string", "description": "任务标题"},
                "description": {"type": "string", "description": "任务描述"},
                "assigned_to": {"type": "string", "description": "分配给谁"},
                "created_by": {"type": "string", "description": "创建者"},
                "priority": {"type": "string", "enum": ["urgent", "high", "normal", "low"]}
              },
              "required": ["title"]
            },
            "handler": create_task
        },
        "update_task": {
            "description": "更新任务状态",
            "parameters": {
              "type": "object",
              "properties": {
                "task_id": {"type": "string", "description": "任务ID"},
                "status": {"type": "string", "enum": ["pending", "running", "completed", "failed"]},
                "result": {"type": "string", "description": "执行结果"}
              },
              "required": ["task_id"]
            },
            "handler": update_task
        },
        "get_tasks": {
                "description": "获取任务列表",
                "parameters": {
                  "type": "object",
                  "properties": {
                    "assigned_to": {"type": "string", "description": "筛选分配给谁的任务"},
                    "status": {"type": "string", "description": "筛选状态"},
                    "limit": {"type": "integer", "description": "限制数量"}
                  }
                },
                "handler": get_tasks
            },
            "get_my_tasks": {
                "description": "查询自己的任务历史",
                "parameters": {
                  "type": "object",
                  "properties": {
                    "agent_id": {"type": "string", "description": "你的代理ID（iflow/qwen/dnf-pvf-analyse/pvf-analyzer）"},
                    "status": {"type": "string", "description": "筛选状态（可选）"},
                    "limit": {"type": "integer", "description": "返回数量，默认20"}
                  },
                  "required": ["agent_id"]
                },
                "handler": get_my_tasks
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
        
        return {
            "jsonrpc": "2.0",
            "id": None,
            "result": {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": RESOURCES[uri]["mime_type"],
                        "text": result["text"]
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