#!/usr/bin/env python3
"""
批量消息清理工具
功能：
- 清理指定天数前的历史消息
- 支持按会话 ID 清理
- 支持按消息类型清理
- 提供确认提示
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


class MessageCleaner:
    """消息清理器"""
    
    def __init__(self, db_path: str = "~/.message_board/board.db"):
        self.db_path = Path(db_path).expanduser()
    
    def count_messages(self, days: int = None, session_id: str = None, 
                     msg_type: str = None) -> int:
        """统计符合条件的消息数量"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if days is not None:
            cutoff_time = int((datetime.now() - timedelta(days=days)).timestamp())
            conditions.append("timestamp < ?")
            params.append(cutoff_time)
        
        if session_id is not None:
            conditions.append("session_id = ?")
            params.append(session_id)
        
        if msg_type is not None:
            conditions.append("msg_type = ?")
            params.append(msg_type)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cursor.execute(f"SELECT COUNT(*) FROM messages WHERE {where_clause}", params)
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def clean_messages(self, days: int = None, session_id: str = None,
                     msg_type: str = None, dry_run: bool = True) -> int:
        """清理消息"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if days is not None:
            cutoff_time = int((datetime.now() - timedelta(days=days)).timestamp())
            conditions.append("timestamp < ?")
            params.append(cutoff_time)
        
        if session_id is not None:
            conditions.append("session_id = ?")
            params.append(session_id)
        
        if msg_type is not None:
            conditions.append("msg_type = ?")
            params.append(msg_type)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        if dry_run:
            cursor.execute(f"SELECT COUNT(*) FROM messages WHERE {where_clause}", params)
            count = cursor.fetchone()[0]
            conn.close()
            return count
        else:
            cursor.execute(f"DELETE FROM messages WHERE {where_clause}", params)
            count = cursor.rowcount
            conn.commit()
            conn.close()
            return count
    
    def cleanup_old_messages(self, days: int, dry_run: bool = True):
        """清理旧消息"""
        count = self.count_messages(days=days)
        
        print(f"找到 {count} 条超过 {days} 天的旧消息")
        
        if count == 0:
            print("没有需要清理的消息")
            return
        
        if dry_run:
            print(f"[预览] 将删除 {count} 条消息（实际不会删除）")
            print("使用 --confirm 确认删除")
        else:
            print(f"正在删除 {count} 条消息...")
            deleted = self.clean_messages(days=days, dry_run=False)
            print(f"✓ 已删除 {deleted} 条消息")


def main():
    parser = argparse.ArgumentParser(description="批量消息清理工具")
    parser.add_argument("--days", type=int, default=30,
                       help="清理指定天数前的消息（默认30天）")
    parser.add_argument("--session", type=str,
                       help="按会话 ID 清理")
    parser.add_argument("--type", type=str,
                       choices=["INIT", "REPLY", "QUESTION", "STATEMENT", "CLOSE"],
                       help="按消息类型清理")
    parser.add_argument("--confirm", action="store_true",
                       help="确认删除（默认只预览）")
    parser.add_argument("--db", type=str,
                       default="~/.message_board/board.db",
                       help="数据库路径")
    
    args = parser.parse_args()
    
    cleaner = MessageCleaner(args.db)
    
    print("=" * 50)
    print("批量消息清理工具")
    print("=" * 50)
    
    if args.session or args.type:
        # 自定义清理
        count = cleaner.count_messages(days=args.days, session_id=args.session,
                                     msg_type=args.type)
        print(f"找到 {count} 条符合条件的消息")
        
        if args.confirm:
            print(f"正在删除...")
            deleted = cleaner.clean_messages(days=args.days, session_id=args.session,
                                             msg_type=args.type, dry_run=False)
            print(f"✓ 已删除 {deleted} 条消息")
        else:
            print(f"[预览] 将删除 {count} 条消息")
            print("使用 --confirm 确认删除")
    else:
        # 标准清理：按天数
        cleaner.cleanup_old_messages(days=args.days, dry_run=not args.confirm)
    
    print("=" * 50)


if __name__ == "__main__":
    main()