"""MCP Resources 实现"""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.database import Database
from src.models import Message


def get_db() -> Database:
    """获取数据库实例"""
    return Database()


def get_unread_messages() -> dict:
    """
    获取未读消息资源
    
    Returns:
        {"uri": str, "text": str, "messages": list}
    """
    try:
        db = get_db()
        messages = db.get_messages(unread_only=True, limit=100)
        
        text_content = "\n\n".join([
            f"[{m.sender}] ({m.priority})\n{m.content}"
            for m in messages
        ])
        
        return {
            "uri": "messages://unread",
            "text": text_content if text_content else "没有未读消息",
            "messages": [m.to_dict() for m in messages]
        }
    except Exception as e:
        return {
            "uri": "messages://unread",
            "text": f"错误：{e}"
        }


def get_all_messages() -> dict:
    """
    获取所有消息资源
    
    Returns:
        {"uri": str, "text": str, "messages": list}
    """
    try:
        db = get_db()
        messages = db.get_messages(limit=100)
        
        text_content = "\n\n".join([
            f"[{m.sender}] {'📭' if m.read else '📬'} ({m.priority})\n{m.content}"
            for m in reversed(messages)
        ])
        
        return {
            "uri": "messages://all",
            "text": text_content if text_content else "没有消息",
            "messages": [m.to_dict() for m in messages]
        }
    except Exception as e:
        return {
            "uri": "messages://all",
            "text": f"错误：{e}"
        }


def get_sent_messages(client_id: str) -> dict:
    """
    获取发送给指定客户端的消息
    
    Returns:
        {"uri": str, "text": str, "messages": list}
    """
    try:
        db = get_db()
        messages = db.get_messages(sender=client_id, limit=100)
        
        text_content = "\n\n".join([
            f"[{m.sender}] {'📭' if m.read else '📬'}\n{m.content}"
            for m in reversed(messages)
        ])
        
        return {
            "uri": f"messages://sent/{client_id}",
            "text": text_content if text_content else f"没有发送给 {client_id} 的消息",
            "messages": [m.to_dict() for m in messages]
        }
    except Exception as e:
        return {
            "uri": f"messages://sent/{client_id}",
            "text": f"错误：{e}"
        }


def get_current_status() -> dict:
    """
    获取当前系统状态资源
    
    Returns:
        {"uri": str, "text": str}
    """
    try:
        db = get_db()
        stats = db.get_stats()
        clients = db.get_all_clients()
        
        import time
        text_content = (
            f"=== Message Board Status ===\n\n"
            f"📬 Unread messages: {stats['unread_messages']}\n"
            f"📭 Total messages: {stats['total_messages']}\n"
            f"🕐 Latest message: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats['latest_message_time'])) if stats['latest_message_time'] else 'None'}\n"
            f"👥 Registered clients: {len(clients)}\n"
        )
        
        if clients:
            text_content += "\n=== Clients ===\n"
            for c in clients:
                last_seen = time.strftime('%Y-%m-%d %H:%M', time.localtime(c.last_seen))
                text_content += f"  - {c.name} ({c.id}): last seen {last_seen}\n"
        
        return {
            "uri": "status://current",
            "text": text_content
        }
    except Exception as e:
        return {
            "uri": "status://current",
            "text": f"错误：{e}"
        }


def get_protocol() -> dict:
    """
    获取 MCP 通信协议文档
    
    Returns:
        {"uri": str, "text": str}
    """
    try:
        # 读取协议文档
        protocol_path = Path(__file__).parent.parent.parent / "MCP_COMMUNICATION_PROTOCOL.md"
        
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
                "text": "协议文档未找到"
            }
    except Exception as e:
        return {
            "uri": "protocol://current",
            "text": f"错误：{e}"
        }


# Resource 模板
RESOURCE_TEMPLATES = {
    "messages://unread": {
        "name": "未读消息",
        "description": "所有未读的消息",
        "mime_type": "text/plain",
        "handler": get_unread_messages
    },
    "messages://all": {
        "name": "所有消息",
        "description": "所有消息列表",
        "mime_type": "text/plain",
        "handler": get_all_messages
    },
    "messages://sent/{client_id}": {
        "name": "发送的消息",
        "description": "发送给指定客户端的消息",
        "mime_type": "text/plain",
        "handler": get_sent_messages
    },
    "status://current": {
        "name": "系统状态",
        "description": "当前系统状态统计",
        "mime_type": "text/plain",
        "handler": get_current_status
    },
    "protocol://current": {
        "name": "MCP 通信协议",
        "description": "当前版本的 MCP 通信协议文档",
        "mime_type": "text/plain",
        "handler": get_protocol
    }
}
