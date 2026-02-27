#!/usr/bin/env python3
"""
测试会话追踪功能
"""

from message_sdk import MessageBoardClient
import sqlite3
from pathlib import Path
import uuid

def test_session_tracking():
    """测试会话追踪"""
    client = MessageBoardClient('test_user')
    db_path = Path('~/.message_board/board.db').expanduser()

    print("=== 会话追踪测试 ===\n")

    # 创建不同的会话 ID
    session_a = f"session_test_a_{uuid.uuid4().hex[:8]}"
    session_b = f"session_test_b_{uuid.uuid4().hex[:8]}"

    print(f"会话 A: {session_a}")
    print(f"会话 B: {session_b}\n")

    # 发送不同会话的消息
    print("发送消息...")
    msg_a1 = client.send("会话 A 的第一条消息", session_id=session_a)
    msg_a2 = client.send("会话 A 的第二条消息", session_id=session_a)
    msg_b1 = client.send("会话 B 的第一条消息", session_id=session_b)
    msg_b2 = client.send("会话 B 的第二条消息", session_id=session_b)

    print(f"  会话 A: {msg_a1}, {msg_a2}")
    print(f"  会话 B: {msg_b1}, {msg_b2}\n")

    # 从数据库读取并验证
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 查询会话 A 的消息
    cursor.execute(
        "SELECT id, content, session_id FROM messages WHERE session_id = ?",
        (session_a,)
    )
    messages_a = cursor.fetchall()

    # 查询会话 B 的消息
    cursor.execute(
        "SELECT id, content, session_id FROM messages WHERE session_id = ?",
        (session_b,)
    )
    messages_b = cursor.fetchall()

    conn.close()

    # 验证结果
    print("验证结果:")
    print(f"  会话 A 消息数: {len(messages_a)} (期望: 2) {'✓' if len(messages_a) == 2 else '✗'}")
    print(f"  会话 B 消息数: {len(messages_b)} (期望: 2) {'✓' if len(messages_b) == 2 else '✗'}")

    if len(messages_a) == 2 and len(messages_b) == 2:
        print("\n✓ 会话追踪功能正常！")
    else:
        print("\n✗ 会话追踪功能异常！")

if __name__ == "__main__":
    test_session_tracking()