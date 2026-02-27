#!/usr/bin/env python3
"""
资源清理工具
定期清理旧数据，释放资源
"""
import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from message_sdk import MessageBoardClient


def cleanup_old_messages(older_than_hours: int = 1):
    """清理旧消息"""
    client = MessageBoardClient("cleanup")
    
    cutoff = int(time.time()) - (older_than_hours * 3600)
    conn = client._get_db_connection()
    cursor = conn.cursor()
    
    # 清理旧消息
    cursor.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff,))
    count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"✓ 清理了 {count} 条旧消息（{older_than_hours}小时前）")


def cleanup_completed_tasks(older_than_hours: int = 24):
    """清理已完成的任务"""
    client = MessageBoardClient("cleanup")
    
    cutoff = int(time.time()) - (older_than_hours * 3600)
    conn = client._get_db_connection()
    cursor = conn.cursor()
    
    # 清理已完成任务
    cursor.execute(
        "DELETE FROM tasks WHERE status IN ('completed', 'failed') AND updated_at < ?",
        (cutoff,)
    )
    count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"✓ 清理了 {count} 个已完成任务（{older_than_hours}小时前）")


def cleanup_stale_waiting(older_than_seconds: int = 300):
    """清理过期的等待代理"""
    client = MessageBoardClient("cleanup")
    
    cutoff = int(time.time()) - older_than_seconds
    conn = client._get_db_connection()
    cursor = conn.cursor()
    
    # 清理过期的等待代理
    cursor.execute("DELETE FROM waiting_agents WHERE registered_at < ?", (cutoff,))
    count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"✓ 清理了 {count} 个过期等待代理（{older_than_seconds}秒前）")


def cleanup_short_messages():
    """清理短消息"""
    client = MessageBoardClient("cleanup")
    
    conn = client._get_db_connection()
    cursor = conn.cursor()
    
    # 清理短消息（小于 20 字符）
    cursor.execute("DELETE FROM messages WHERE length(content) < 20")
    count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"✓ 清理了 {count} 条短消息")


def cleanup_wal_files():
    """清理 WAL 文件"""
    db_dir = Path("~/.message_board").expanduser()
    
    wal_files = list(db_dir.glob("*.db-wal"))
    shm_files = list(db_dir.glob("*.db-shm"))
    
    for wal_file in wal_files:
        try:
            wal_file.unlink()
            print(f"✓ 删除 WAL 文件: {wal_file.name}")
        except Exception as e:
            print(f"✗ 删除失败 {wal_file.name}: {e}")
    
    for shm_file in shm_files:
        try:
            shm_file.unlink()
            print(f"✓ 删除 SHM 文件: {shm_file.name}")
        except Exception as e:
            print(f"✗ 删除失败 {shm_file.name}: {e}")


def cleanup_all():
    """执行所有清理操作"""
    print("开始全面清理...")
    print("-" * 50)
    
    cleanup_short_messages()
    cleanup_old_messages(older_than_hours=1)
    cleanup_completed_tasks(older_than_hours=24)
    cleanup_stale_waiting(older_than_seconds=300)
    cleanup_wal_files()
    
    print("-" * 50)
    print("✓ 清理完成")


def get_cleanup_stats():
    """获取清理统计"""
    client = MessageBoardClient("cleanup")
    
    conn = client._get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # 消息统计
    cursor.execute("SELECT COUNT(*) FROM messages")
    stats["total_messages"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages WHERE read = 0")
    stats["unread_messages"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages WHERE length(content) < 20")
    stats["short_messages"] = cursor.fetchone()[0]
    
    # 任务统计
    cursor.execute("SELECT COUNT(*) FROM tasks")
    stats["total_tasks"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
    stats["completed_tasks"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'")
    stats["failed_tasks"] = cursor.fetchone()[0]
    
    # 等待代理统计
    cursor.execute("SELECT COUNT(*) FROM waiting_agents")
    stats["waiting_agents"] = cursor.fetchone()[0]
    
    conn.close()
    
    return stats


def print_stats():
    """打印统计信息"""
    stats = get_cleanup_stats()
    
    print("\n" + "=" * 50)
    print("清理统计")
    print("=" * 50)
    print(f"总消息数: {stats['total_messages']}")
    print(f"未读消息: {stats['unread_messages']}")
    print(f"短消息: {stats['short_messages']}")
    print(f"总任务数: {stats['total_tasks']}")
    print(f"已完成任务: {stats['completed_tasks']}")
    print(f"失败任务: {stats['failed_tasks']}")
    print(f"等待代理: {stats['waiting_agents']}")
    print("=" * 50 + "\n")


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python3 cleanup.py <command>")
        print("命令:")
        print("  all                    - 执行所有清理")
        print("  messages [hours]       - 清理旧消息（默认1小时）")
        print("  tasks [hours]          - 清理已完成任务（默认24小时）")
        print("  waiting [seconds]      - 清理过期等待代理（默认300秒）")
        print("  short                  - 清理短消息")
        print("  wal                    - 清理 WAL 文件")
        print("  stats                  - 显示统计")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "all":
        cleanup_all()
    
    elif command == "messages":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        cleanup_old_messages(hours)
    
    elif command == "tasks":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        cleanup_completed_tasks(hours)
    
    elif command == "waiting":
        seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        cleanup_stale_waiting(seconds)
    
    elif command == "short":
        cleanup_short_messages()
    
    elif command == "wal":
        cleanup_wal_files()
    
    elif command == "stats":
        print_stats()
    
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
