#!/usr/bin/env python3
"""
测试投递状态更新功能
"""

from message_sdk import MessageBoardClient
import sqlite3
from pathlib import Path

def test_delivery_status():
    """测试投递状态更新"""
    client = MessageBoardClient('test_user')
    db_path = Path('~/.message_board/board.db').expanduser()

    print("=== 投递状态测试 ===\n")

    # 发送测试消息
    msg_id = client.send('测试投递状态')
    print(f"发送消息，ID: {msg_id}\n")

    # 从数据库读取 delivery_status
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT delivery_status, read FROM messages WHERE id = ?",
        (msg_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        status = row['delivery_status']
        is_read = row['read']

        print(f"当前状态:")
        print(f"  delivery_status: {status} (期望: delivered) {'✓' if status == 'delivered' else '✗'}")
        print(f"  read: {is_read} (期望: 0) {'✓' if is_read == 0 else '✗'}\n")

        # 验证状态转换
        if status == 'delivered' and is_read == 0:
            print("✓ 投递状态正常！")
            print("  pending → delivered ✓")
        else:
            print("✗ 投递状态异常！")
    else:
        print("✗ 未找到消息")

    print("\n注意：delivery_status 'read' 状态需要对方读取消息后才会更新")

if __name__ == "__main__":
    test_delivery_status()