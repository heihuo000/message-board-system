"""数据模型定义"""
from dataclasses import dataclass, field, asdict
from typing import Optional
import json
import time
import uuid


@dataclass
class Message:
    """留言数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    content: str = ""
    timestamp: int = field(default_factory=lambda: int(time.time()))
    read: bool = False
    reply_to: Optional[str] = None
    priority: str = "normal"
    metadata: Optional[dict] = field(default_factory=dict)
    # v2.0 新增字段
    version: str = "1.0"
    session_id: Optional[str] = None
    msg_type: str = "STATEMENT"
    delivery_status: str = "pending"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp,
            "read": 1 if self.read else 0,
            "reply_to": self.reply_to,
            "priority": self.priority,
            "metadata": json.dumps(self.metadata) if self.metadata else None,
            "version": self.version,
            "session_id": self.session_id,
            "msg_type": self.msg_type,
            "delivery_status": self.delivery_status
        }

    @classmethod
    def from_row(cls, row: tuple) -> "Message":
        """从数据库行创建"""
        return cls(
            id=row[0],
            sender=row[1],
            content=row[2],
            timestamp=row[3],
            read=bool(row[4]),
            reply_to=row[5],
            priority=row[6] or "normal",
            metadata=json.loads(row[7]) if row[7] else None,
            version=row[8] if len(row) > 8 else "1.0",
            session_id=row[9] if len(row) > 9 else None,
            msg_type=row[10] if len(row) > 10 else "STATEMENT",
            delivery_status=row[11] if len(row) > 11 else "pending"
        )

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps({
            "id": self.id,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp,
            "read": self.read,
            "reply_to": self.reply_to,
            "priority": self.priority,
            "metadata": self.metadata,
            "version": self.version,
            "session_id": self.session_id,
            "msg_type": self.msg_type,
            "delivery_status": self.delivery_status
        }, ensure_ascii=False, indent=2)


@dataclass
class Client:
    """客户端数据模型"""
    id: str = ""
    name: str = ""
    last_seen: int = field(default_factory=lambda: int(time.time()))
    config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "last_seen": self.last_seen,
            "config": json.dumps(self.config) if self.config else None
        }

    @classmethod
    def from_row(cls, row: tuple) -> "Client":
        """从数据库行创建"""
        return cls(
            id=row[0],
            name=row[1],
            last_seen=row[2],
            config=json.loads(row[3]) if row[3] else {}
        )
