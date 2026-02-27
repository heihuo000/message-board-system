"""SQLite 数据库层 - 使用 WAL 模式支持并发读写"""
import sqlite3
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager

from .models import Message, Client


class Database:
    """数据库管理类"""
    
    def __init__(self, db_path: str = "~/.message_board/board.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    @contextmanager
    def connect(self):
        """上下文管理器获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self):
        """初始化数据库表结构"""
        with self.connect() as conn:
            # 启用 WAL 模式
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")

            # 创建消息表（v2.0）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    read INTEGER DEFAULT 0,
                    reply_to TEXT,
                    priority TEXT DEFAULT 'normal',
                    metadata TEXT,
                    version TEXT DEFAULT '1.0',
                    session_id TEXT,
                    msg_type TEXT DEFAULT 'STATEMENT',
                    delivery_status TEXT DEFAULT 'pending'
                )
            """)

            # 创建客户端表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    last_seen INTEGER,
                    config TEXT
                )
            """)

            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_read ON messages(read)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(msg_type)")
    
    # ==================== Message 操作 ====================
    
    def add_message(self, message: Message) -> str:
        """添加消息"""
        import json
        with self.connect() as conn:
            conn.execute("""
                INSERT INTO messages (id, sender, content, timestamp, read, reply_to, priority, metadata, version, session_id, msg_type, delivery_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                message.sender,
                message.content,
                message.timestamp,
                1 if message.read else 0,
                message.reply_to,
                message.priority,
                json.dumps(message.metadata) if message.metadata else None,
                message.version,
                message.session_id,
                message.msg_type,
                message.delivery_status
            ))
        return message.id
    
    def get_message(self, message_id: str) -> Optional[Message]:
        """获取单条消息"""
        with self.connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM messages WHERE id = ?",
                (message_id,)
            )
            row = cursor.fetchone()
            return Message.from_row(tuple(row)) if row else None
    
    def get_messages(
        self,
        unread_only: bool = False,
        limit: int = 100,
        since: int = 0,
        sender: Optional[str] = None
    ) -> List[Message]:
        """获取消息列表"""
        with self.connect() as conn:
            query = "SELECT * FROM messages WHERE 1=1"
            params = []
            
            if unread_only:
                query += " AND read = 0"
            if since > 0:
                query += " AND timestamp >= ?"
                params.append(since)
            if sender:
                query += " AND sender = ?"
                params.append(sender)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [Message.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def mark_read(self, message_ids: List[str]) -> int:
        """标记消息已读"""
        with self.connect() as conn:
            placeholders = ",".join("?" * len(message_ids))
            cursor = conn.execute(
                f"UPDATE messages SET read = 1 WHERE id IN ({placeholders})",
                message_ids
            )
            return cursor.rowcount
    
    def mark_all_read(self, recipient: Optional[str] = None) -> int:
        """标记所有消息已读"""
        with self.connect() as conn:
            if recipient:
                cursor = conn.execute(
                    "UPDATE messages SET read = 1 WHERE sender = ?",
                    (recipient,)
                )
            else:
                cursor = conn.execute("UPDATE messages SET read = 1")
            return cursor.rowcount
    
    def delete_message(self, message_id: str) -> bool:
        """删除消息"""
        with self.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE id = ?",
                (message_id,)
            )
            return cursor.rowcount > 0
    
    def get_unread_count(self) -> int:
        """获取未读消息数量"""
        with self.connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM messages WHERE read = 0")
            return cursor.fetchone()[0]
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self.connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            unread = conn.execute("SELECT COUNT(*) FROM messages WHERE read = 0").fetchone()[0]
            latest = conn.execute(
                "SELECT MAX(timestamp) FROM messages"
            ).fetchone()[0]
            
            return {
                "total_messages": total,
                "unread_messages": unread,
                "latest_message_time": latest
            }
    
    # ==================== Client 操作 ====================
    
    def register_client(self, client: Client) -> bool:
        """注册客户端"""
        import json
        with self.connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO clients (id, name, last_seen, config)
                VALUES (?, ?, ?, ?)
            """, (
                client.id,
                client.name,
                client.last_seen,
                json.dumps(client.config) if client.config else None
            ))
            return True
    
    def get_client(self, client_id: str) -> Optional[Client]:
        """获取客户端信息"""
        with self.connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM clients WHERE id = ?",
                (client_id,)
            )
            row = cursor.fetchone()
            return Client.from_row(tuple(row)) if row else None
    
    def update_client_last_seen(self, client_id: str) -> bool:
        """更新客户端最后活跃时间"""
        import time
        with self.connect() as conn:
            cursor = conn.execute(
                "UPDATE clients SET last_seen = ? WHERE id = ?",
                (int(time.time()), client_id)
            )
            return cursor.rowcount > 0
    
    def get_all_clients(self) -> List[Client]:
        """获取所有客户端"""
        with self.connect() as conn:
            cursor = conn.execute("SELECT * FROM clients")
            return [Client.from_row(tuple(row)) for row in cursor.fetchall()]
    
    # ==================== 工具方法 ====================
    
    def clear_old_messages(self, older_than: int) -> int:
        """清理旧消息"""
        with self.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE timestamp < ?",
                (older_than,)
            )
            return cursor.rowcount
    
    def backup(self, backup_path: str) -> str:
        """备份数据库"""
        import shutil
        backup_file = Path(backup_path).expanduser()
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(self.db_path), str(backup_file))
        return str(backup_file)
