"""消息处理器 - 过滤、去重、路由"""
import time
from typing import Set, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.database import Database
from src.models import Message


class MessageProcessor:
    """消息处理器"""
    
    def __init__(self, client_id: str, db_path: str = "~/.message_board/board.db"):
        self.client_id = client_id
        self.db = Database(db_path)
        self._processed_ids: Set[str] = set()
        self._max_history = 1000  # 最多保留的历史 ID 数
    
    def get_new_messages(self) -> List[Message]:
        """
        获取新的未读消息（排除自己发送的）
        
        Returns:
            新消息列表
        """
        # 获取所有未读消息
        unread = self.db.get_messages(unread_only=True, limit=100)
        
        # 过滤：排除自己发送的
        relevant = [m for m in unread if m.sender != self.client_id]
        
        # 去重：只保留未处理过的
        new_messages = [m for m in relevant if m.id not in self._processed_ids]
        
        # 标记为已处理
        for m in new_messages:
            self._processed_ids.add(m.id)
        
        # 清理历史 ID（防止内存泄漏）
        if len(self._processed_ids) > self._max_history:
            self._processed_ids = set(list(self._processed_ids)[-self._max_history:])
        
        return new_messages
    
    def mark_processed(self, message_ids: List[str]):
        """标记消息已处理"""
        for mid in message_ids:
            self._processed_ids.add(mid)
    
    def is_new_message(self, message_id: str) -> bool:
        """检查消息是否为新消息"""
        return message_id not in self._processed_ids
    
    def get_stats(self) -> dict:
        """获取处理器统计"""
        unread = self.db.get_messages(unread_only=True)
        new_count = len([m for m in unread if m.sender != self.client_id and m.id not in self._processed_ids])
        
        return {
            "client_id": self.client_id,
            "processed_count": len(self._processed_ids),
            "new_unread_count": new_count,
            "total_unread": len(unread)
        }
