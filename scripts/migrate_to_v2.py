#!/usr/bin/env python3
"""数据库迁移脚本 - 从 v1.0 升级到 v2.0"""
import sqlite3
from pathlib import Path
import sys


def migrate_database(db_path: str = "~/.message_board/board.db"):
    """迁移数据库到 v2.0"""
    db_path = Path(db_path).expanduser()

    if not db_path.exists():
        print(f"❌ 数据库不存在: {db_path}")
        return False

    print(f"📦 开始迁移数据库: {db_path}")

    # 备份数据库
    backup_path = db_path.with_suffix('.db.backup')
    import shutil
    shutil.copy2(str(db_path), str(backup_path))
    print(f"✅ 已创建备份: {backup_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 检查当前版本
        cursor.execute("PRAGMA table_info(messages)")
        columns = [row[1] for row in cursor.fetchall()]

        if "version" in columns:
            print("✅ 数据库已经是 v2.0 版本")
            conn.close()
            return True

        print("🔄 正在升级到 v2.0...")

        # 添加新字段
        new_fields = [
            ("version", "TEXT DEFAULT '1.0'"),
            ("session_id", "TEXT"),
            ("msg_type", "TEXT DEFAULT 'STATEMENT'"),
            ("delivery_status", "TEXT DEFAULT 'pending'")
        ]

        for field_name, field_def in new_fields:
            if field_name not in columns:
                cursor.execute(f"ALTER TABLE messages ADD COLUMN {field_name} {field_def}")
                print(f"  ✓ 添加字段: {field_name}")
            else:
                print(f"  ℹ️  字段已存在: {field_name}")

        # 创建新索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(msg_type)")
        print("  ✓ 创建索引: session_id, msg_type")

        # 自动检测并填充 msg_type（基于现有数据）
        cursor.execute("SELECT id, content, reply_to FROM messages")
        rows = cursor.fetchall()

        for msg_id, content, reply_to in rows:
            msg_type = "STATEMENT"

            if reply_to:
                msg_type = "REPLY"
            elif "?" in content or "？" in content:
                msg_type = "QUESTION"
            elif content.strip().lower() in ["结束", "再见", "bye", "goodbye", "close"]:
                msg_type = "CLOSE"
            elif content.strip().lower() in ["你好", "hello", "hi", "嗨"]:
                msg_type = "INIT"

            cursor.execute(
                "UPDATE messages SET msg_type = ? WHERE id = ?",
                (msg_type, msg_id)
            )

        print(f"  ✓ 自动标记了 {len(rows)} 条消息的类型")

        # 更新 delivery_status（已读的消息标记为 delivered）
        cursor.execute(
            "UPDATE messages SET delivery_status = 'delivered' WHERE read = 1"
        )
        cursor.execute(
            "UPDATE messages SET delivery_status = 'pending' WHERE read = 0"
        )
        print("  ✓ 更新 delivery_status")

        conn.commit()
        print("✅ 数据库迁移完成！")
        return True

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
        # 恢复备份
        shutil.copy2(str(backup_path), str(db_path))
        print(f"🔄 已恢复备份")
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "~/.message_board/board.db"

    success = migrate_database(db_path)
    sys.exit(0 if success else 1)