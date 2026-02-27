"""MCP Tools 实现"""
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.database import Database
from src.models import Message


def get_db() -> Database:
    """获取数据库实例"""
    return Database()


def send_message(
    content: str,
    sender: str = "unknown",
    priority: str = "normal",
    reply_to: Optional[str] = None
) -> dict:
    """
    发送消息
    
    Args:
        content: 消息内容
        sender: 发送者 ID
        priority: 优先级 (normal/urgent)
        reply_to: 回复的消息 ID
    
    Returns:
        {"success": bool, "message_id": str, "error": str}
    """
    try:
        db = get_db()
        message = Message(
            sender=sender,
            content=content,
            priority=priority,
            reply_to=reply_to
        )
        message_id = db.add_message(message)
        return {
            "success": True,
            "message_id": message_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def read_messages(
    unread_only: bool = False,
    limit: int = 100,
    since: int = 0,
    sender: Optional[str] = None
) -> dict:
    """
    读取消息
    
    Args:
        unread_only: 只读取未读消息
        limit: 限制返回数量
        since: 起始时间戳
        sender: 发送者过滤
    
    Returns:
        {"success": bool, "messages": list, "error": str}
    """
    try:
        db = get_db()
        messages = db.get_messages(
            unread_only=unread_only,
            limit=limit,
            since=since,
            sender=sender
        )
        return {
            "success": True,
            "messages": [m.to_dict() for m in messages]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def mark_read(message_ids: List[str]) -> dict:
    """
    标记消息已读
    
    Args:
        message_ids: 消息 ID 列表
    
    Returns:
        {"success": bool, "count": int, "error": str}
    """
    try:
        db = get_db()
        count = db.mark_read(message_ids)
        return {
            "success": True,
            "count": count
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_status() -> dict:
    """
    获取系统状态
    
    Returns:
        {"success": bool, "stats": dict, "error": str}
    """
    try:
        db = get_db()
        stats = db.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def register_client(client_id: str, name: str) -> dict:
    """
    注册客户端
    
    Args:
        client_id: 客户端 ID
        name: 客户端名称
    
    Returns:
        {"success": bool, "error": str}
    """
    try:
        db = get_db()
        from src.models import Client
        client = Client(id=client_id, name=name)
        db.register_client(client)
        return {
            "success": True
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def delete_message(message_id: str) -> dict:
    """
    删除消息
    
    Args:
        message_id: 消息 ID
    
    Returns:
        {"success": bool, "deleted": bool, "error": str}
    """
    try:
        db = get_db()
        deleted = db.delete_message(message_id)
        return {
            "success": True,
            "deleted": deleted
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def clear_old_messages(older_than_seconds: int = 2592000) -> dict:
    """
    清理旧消息
    
    Args:
        older_than_seconds: 清理早于指定秒数的消息（默认 30 天）
    
    Returns:
        {"success": bool, "count": int, "error": str}
    """
    try:
        db = get_db()
        import time
        cutoff = int(time.time()) - older_than_seconds
        count = db.clear_old_messages(cutoff)
        return {
            "success": True,
            "count": count
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
