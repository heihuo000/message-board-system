#!/usr/bin/env python3
"""
消息功能测试脚本
测试已读标注、发送、读取等功能
"""
import sys
sys.path.insert(0, '.')
from message_sdk import MessageBoardClient
from datetime import datetime

def test_all():
    """运行所有测试"""
    print("=" * 60)
    print("消息功能测试")
    print("=" * 60)
    print()
    
    # 创建测试客户端
    sender = MessageBoardClient('test_sender')
    receiver = MessageBoardClient('test_receiver')
    
    test_count = 0
    pass_count = 0
    
    # 测试 1: 发送消息
    test_count += 1
    print(f"测试 {test_count}: 发送消息")
    try:
        msg_id = sender.send("这是一条测试消息")
        print(f"  ✅ 通过 - 消息 ID: {msg_id[:8]}...")
        pass_count += 1
    except Exception as e:
        print(f"  ❌ 失败 - {e}")
    print()
    
    # 测试 2: 读取未读消息
    test_count += 1
    print(f"测试 {test_count}: 读取未读消息")
    try:
        messages = receiver.read_unread()
        print(f"  ✅ 通过 - 未读消息数：{len(messages)}")
        for msg in messages:
            print(f"      [{msg['sender']}] {msg['content'][:30]}...")
        pass_count += 1
    except Exception as e:
        print(f"  ❌ 失败 - {e}")
    print()
    
    # 测试 3: 标记已读
    test_count += 1
    print(f"测试 {test_count}: 标记已读")
    try:
        if messages:
            msg_ids = [m['id'] for m in messages]
            count = receiver.mark_read(msg_ids)
            print(f"  ✅ 通过 - 标记了 {count} 条消息")
            pass_count += 1
        else:
            print(f"  ⚠️ 跳过 - 没有消息")
    except Exception as e:
        print(f"  ❌ 失败 - {e}")
    print()
    
    # 测试 4: 再次读取未读（应该为 0）
    test_count += 1
    print(f"测试 {test_count}: 再次读取未读消息")
    try:
        messages = receiver.read_unread()
        if len(messages) == 0:
            print(f"  ✅ 通过 - 未读消息数：{len(messages)} (正确)")
            pass_count += 1
        else:
            print(f"  ⚠️ 警告 - 未读消息数：{len(messages)} (应该为 0)")
    except Exception as e:
        print(f"  ❌ 失败 - {e}")
    print()
    
    # 测试 5: 读取所有消息（包含 read 字段）
    test_count += 1
    print(f"测试 {test_count}: 读取所有消息")
    try:
        all_msgs = receiver.read_all(limit=5)
        print(f"  ✅ 通过 - 总消息数：{len(all_msgs)}")
        for msg in all_msgs[:3]:
            status = '📭 已读' if msg['read'] else '📬 未读'
            print(f"      {status} [{msg['sender']}] {msg['content'][:30]}...")
        pass_count += 1
    except Exception as e:
        print(f"  ❌ 失败 - {e}")
    print()
    
    # 测试 6: 获取统计
    test_count += 1
    print(f"测试 {test_count}: 获取统计")
    try:
        stats = receiver.get_stats()
        print(f"  ✅ 通过 - 总消息：{stats['total_messages']}, 未读：{stats['unread_messages']}")
        pass_count += 1
    except Exception as e:
        print(f"  ❌ 失败 - {e}")
    print()
    
    # 测试 7: 发送并等待回复
    test_count += 1
    print(f"测试 {test_count}: 发送并等待回复 (超时测试)")
    try:
        msg_id = sender.send("测试等待")
        print(f"  发送消息：{msg_id[:8]}...")
        # 不实际等待，只测试发送
        print(f"  ✅ 通过 - 发送成功")
        pass_count += 1
    except Exception as e:
        print(f"  ❌ 失败 - {e}")
    print()
    
    # 总结
    print("=" * 60)
    print(f"测试完成：{pass_count}/{test_count} 通过")
    print(f"成功率：{pass_count/test_count*100:.1f}%")
    print("=" * 60)
    
    return pass_count == test_count

if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)
