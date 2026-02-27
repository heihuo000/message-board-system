#!/usr/bin/env python3
"""
测试消息类型自动检测功能
"""

from message_sdk import MessageBoardClient
import sqlite3
from pathlib import Path

def test_msg_type_detection():
    """测试消息类型自动检测"""
    client = MessageBoardClient('test_user')
    db_path = Path('~/.message_board/board.db').expanduser()

    # 测试用例
    test_cases = [
        ('你好', 'INIT'),
        ('hello', 'INIT'),
        ('Hi', 'INIT'),
        ('这是一个问题？', 'QUESTION'),
        ('这是普通陈述', 'STATEMENT'),
        ('再见', 'CLOSE'),
        ('bye', 'CLOSE'),
        ('goodbye', 'CLOSE')
    ]

    print("=== 消息类型自动检测测试 ===\n")

    for content, expected in test_cases:
        # 发送消息
        msg_id = client.send(content)
        print(f"发送: {content}")

        # 从数据库读取 msg_type
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT msg_type FROM messages WHERE id = ?",
            (msg_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            actual = row['msg_type']
            status = "✓" if actual == expected else "✗"
            print(f"  期望: {expected}, 实际: {actual} {status}")
        else:
            print(f"  ✗ 未找到消息")

        print()

if __name__ == "__main__":
    test_msg_type_detection()