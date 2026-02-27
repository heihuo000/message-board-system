#!/usr/bin/env python3
"""
消息统计和报告工具
功能：
- 统计消息总数、未读消息数
- 按消息类型统计
- 按会话统计
- 按发送者统计
- 生成详细报告
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter


class MessageStats:
    """消息统计器"""
    
    def __init__(self, db_path: str = "~/.message_board/board.db"):
        self.db_path = Path(db_path).expanduser()
    
    def get_overall_stats(self) -> dict:
        """获取总体统计"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 总消息数
        cursor.execute("SELECT COUNT(*) FROM messages")
        total = cursor.fetchone()[0]
        
        # 未读消息数
        cursor.execute("SELECT COUNT(*) FROM messages WHERE read = 0")
        unread = cursor.fetchone()[0]
        
        # 最新消息时间
        cursor.execute("SELECT MAX(timestamp) FROM messages")
        latest = cursor.fetchone()[0]
        
        # 最早消息时间
        cursor.execute("SELECT MIN(timestamp) FROM messages")
        earliest = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_messages": total,
            "unread_messages": unread,
            "latest_message_time": datetime.fromtimestamp(latest).isoformat() if latest else None,
            "earliest_message_time": datetime.fromtimestamp(earliest).isoformat() if earliest else None
        }
    
    def get_stats_by_type(self) -> dict:
        """按消息类型统计"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT msg_type, COUNT(*) as count
            FROM messages
            GROUP BY msg_type
            ORDER BY count DESC
        """)
        
        stats = dict(cursor.fetchall())
        conn.close()
        
        return stats
    
    def get_stats_by_session(self, limit: int = 10) -> list:
        """按会话统计"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, COUNT(*) as count
            FROM messages
            WHERE session_id IS NOT NULL
            GROUP BY session_id
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        
        stats = cursor.fetchall()
        conn.close()
        
        return stats
    
    def get_stats_by_sender(self, limit: int = 10) -> list:
        """按发送者统计"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sender, COUNT(*) as count
            FROM messages
            GROUP BY sender
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        
        stats = cursor.fetchall()
        conn.close()
        
        return stats
    
    def get_daily_stats(self, days: int = 7) -> list:
        """按日期统计"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff_time = int((datetime.now() - timedelta(days=days)).timestamp())
        
        cursor.execute("""
            SELECT 
                date(timestamp, 'unixepoch', 'localtime') as date,
                COUNT(*) as count
            FROM messages
            WHERE timestamp >= ?
            GROUP BY date
            ORDER BY date DESC
        """, (cutoff_time,))
        
        stats = cursor.fetchall()
        conn.close()
        
        return stats
    
    def generate_report(self) -> str:
        """生成详细报告"""
        report = []
        report.append("=" * 60)
        report.append("消息统计报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 总体统计
        overall = self.get_overall_stats()
        report.append("【总体统计】")
        report.append(f"  总消息数: {overall['total_messages']}")
        report.append(f"  未读消息: {overall['unread_messages']}")
        report.append(f"  最新消息: {overall['latest_message_time'] or '无'}")
        report.append(f"  最早消息: {overall['earliest_message_time'] or '无'}")
        report.append("")
        
        # 按消息类型统计
        type_stats = self.get_stats_by_type()
        report.append("【按消息类型统计】")
        for msg_type, count in type_stats.items():
            report.append(f"  {msg_type}: {count}")
        report.append("")
        
        # 按会话统计
        session_stats = self.get_stats_by_session()
        report.append("【按会话统计（前10）】")
        for session_id, count in session_stats:
            report.append(f"  {session_id}: {count}")
        report.append("")
        
        # 按发送者统计
        sender_stats = self.get_stats_by_sender()
        report.append("【按发送者统计（前10）】")
        for sender, count in sender_stats:
            report.append(f"  {sender}: {count}")
        report.append("")
        
        # 按日期统计
        daily_stats = self.get_daily_stats()
        report.append("【按日期统计（最近7天）】")
        for date, count in daily_stats:
            report.append(f"  {date}: {count}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="消息统计和报告工具")
    parser.add_argument("--db", type=str,
                       default="~/.message_board/board.db",
                       help="数据库路径")
    parser.add_argument("--report", action="store_true",
                       help="生成详细报告")
    parser.add_argument("--by-type", action="store_true",
                       help="按消息类型统计")
    parser.add_argument("--by-session", action="store_true",
                       help="按会话统计")
    parser.add_argument("--by-sender", action="store_true",
                       help="按发送者统计")
    parser.add_argument("--daily", type=int, metavar="DAYS",
                       help="按日期统计（指定天数）")
    
    args = parser.parse_args()
    
    stats = MessageStats(args.db)
    
    if args.report:
        print(stats.generate_report())
    elif args.by_type:
        type_stats = stats.get_stats_by_type()
        print("【按消息类型统计】")
        for msg_type, count in type_stats.items():
            print(f"  {msg_type}: {count}")
    elif args.by_session:
        session_stats = stats.get_stats_by_session()
        print("【按会话统计（前10）】")
        for session_id, count in session_stats:
            print(f"  {session_id}: {count}")
    elif args.by_sender:
        sender_stats = stats.get_stats_by_sender()
        print("【按发送者统计（前10）】")
        for sender, count in sender_stats:
            print(f"  {sender}: {count}")
    elif args.daily:
        daily_stats = stats.get_daily_stats(args.daily)
        print(f"【按日期统计（最近{args.daily}天）】")
        for date, count in daily_stats:
            print(f"  {date}: {count}")
    else:
        # 默认显示总体统计
        overall = stats.get_overall_stats()
        print("【总体统计】")
        print(f"  总消息数: {overall['total_messages']}")
        print(f"  未读消息: {overall['unread_messages']}")
        print(f"  最新消息: {overall['latest_message_time'] or '无'}")
        print(f"  最早消息: {overall['earliest_message_time'] or '无'}")
        print()
        print("使用 --report 生成详细报告")
        print("使用 --help 查看更多选项")


if __name__ == "__main__":
    main()