#!/usr/bin/env python3
"""端到端通信测试脚本"""
import sys
import time
from pathlib import Path

# 添加路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import Database
from src.models import Message
from src.daemon.processor import MessageProcessor

def test_end_to_end():
    """端到端测试"""
    print("=" * 60)
    print("Message Board 端到端通信测试")
    print("=" * 60)
    
    # 初始化数据库
    db = Database()
    print("\n[1] 数据库初始化成功")
    
    # 客户端 A 发送消息
    print("\n[2] 客户端 A 发送消息...")
    msg_a = Message(sender="client_alice", content="你好，我是 Alice！")
    msg_id_a = db.add_message(msg_a)
    print(f"    消息 ID: {msg_id_a}")
    
    # 客户端 B 发送消息
    print("\n[3] 客户端 B 发送消息...")
    msg_b = Message(sender="client_bob", content="你好 Alice，我是 Bob！")
    msg_id_b = db.add_message(msg_b)
    print(f"    消息 ID: {msg_id_b}")
    
    # 客户端 A 回复
    print("\n[4] 客户端 A 回复消息...")
    msg_a2 = Message(sender="client_alice", content="很高兴认识你！", reply_to=msg_id_b)
    msg_id_a2 = db.add_message(msg_a2)
    print(f"    消息 ID: {msg_id_a2}")
    
    # 查看状态
    print("\n[5] 系统状态:")
    stats = db.get_stats()
    print(f"    总消息数：{stats['total_messages']}")
    print(f"    未读消息：{stats['unread_messages']}")
    
    # 客户端 A 读取未读消息（排除自己发送的）
    print("\n[6] 客户端 A 读取未读消息...")
    processor_a = MessageProcessor("client_alice")
    new_msgs = processor_a.get_new_messages()
    print(f"    新消息数：{len(new_msgs)}")
    for msg in new_msgs:
        print(f"    - [{msg.sender}] {msg.content}")
    
    # 客户端 B 读取未读消息
    print("\n[7] 客户端 B 读取未读消息...")
    processor_b = MessageProcessor("client_bob")
    new_msgs_b = processor_b.get_new_messages()
    print(f"    新消息数：{len(new_msgs_b)}")
    for msg in new_msgs_b:
        print(f"    - [{msg.sender}] {msg.content}")
    
    # 标记已读
    print("\n[8] 标记所有消息已读...")
    db.mark_all_read()
    stats = db.get_stats()
    print(f"    剩余未读：{stats['unread_messages']}")
    
    # JSON 输出测试
    print("\n[9] JSON 输出测试:")
    messages = db.get_messages(limit=3)
    for msg in messages:
        print(f"    {msg.to_json()[:80]}...")
    
    print("\n" + "=" * 60)
    print("测试完成！✓")
    print("=" * 60)


if __name__ == "__main__":
    test_end_to_end()
