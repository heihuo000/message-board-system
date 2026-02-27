#!/usr/bin/env python3
"""
简化版 AI 对话脚本
原则：够用就好，简单可靠
"""
from message_sdk import MessageBoardClient
import time
import sys


def simple_dialogue(client_id: str, partner_id: str, max_turns: int = 10):
    """
    简单对话循环
    
    Args:
        client_id: 我的客户端 ID
        partner_id: 对话伙伴 ID
        max_turns: 最大对话轮次
    """
    client = MessageBoardClient(client_id)
    last_seen = int(time.time())
    turn = 0
    
    print("=" * 60)
    print(f"🎙️ 简单对话开始")
    print(f"   我：{client_id}")
    print(f"   对方：{partner_id}")
    print(f"   最大轮次：{max_turns}")
    print("=" * 60)
    
    # 发送第一条消息
    client.send(f"@{partner_id} 你好，开始对话吧")
    print(f"📤 [第{turn + 1}轮] 已发送：@{partner_id} 你好，开始对话吧")
    turn += 1
    
    # 对话循环
    while turn < max_turns:
        # 等待回复（带重试）
        msg = None
        for retry in range(3):
            print(f"⏳ 等待 {partner_id} 的回复（第{retry + 1}/3 次尝试）...")
            
            result = client.wait_for_message(timeout=120, last_seen=last_seen)
            
            if result.get('success'):
                msg = result['message']
                
                # 跳过自己的消息
                if msg['sender'] == client_id:
                    print("  ⚠️ 跳过自己的消息")
                    continue
                
                print(f"📥 收到：[{msg['sender']}] {msg['content'][:50]}...")
                last_seen = msg['timestamp']
                break
            else:
                wait_time = 10 * (retry + 1)
                print(f"⏰ 等待超时，{wait_time}秒后重试...")
                time.sleep(wait_time)
        
        if msg is None or msg['sender'] == client_id:
            print("❌ 对方无响应，对话终止")
            break
        
        # 简单回复
        reply = f"收到：{msg['content'][:50]}"
        client.send(reply, reply_to=msg['id'])
        print(f"📤 [第{turn + 1}轮] 回复：{reply[:50]}...")
        turn += 1
    
    print("=" * 60)
    print(f"✅ 对话完成，共{turn}轮")
    print("=" * 60)


def quick_send(client_id: str, content: str, sender: str = None):
    """快速发送消息"""
    if sender is None:
        sender = client_id
    
    client = MessageBoardClient(client_id)
    msg_id = client.send(content, sender=sender)
    print(f"📤 消息已发送 (ID: {msg_id})")
    return msg_id


def quick_read(client_id: str, limit: int = 5):
    """快速读取消息"""
    client = MessageBoardClient(client_id)
    messages = client.read_unread(limit=limit)
    
    if not messages:
        print("没有新消息")
        return
    
    print(f"📋 未读消息 ({len(messages)} 条):")
    for msg in messages:
        time_str = time.strftime('%H:%M:%S', time.localtime(msg['timestamp']))
        print(f"[{time_str}] {msg['sender']}: {msg['content'][:60]}...")
        client.mark_read([msg['id']])


def print_usage():
    """打印使用说明"""
    print("""
简化版 AI 对话脚本 - 够用就好

用法:
    python3 simple_dialogue.py <client_id> <partner_id> [max_turns]
    python3 simple_dialogue.py --send <client_id> <content>
    python3 simple_dialogue.py --read <client_id>

示例:
    # 开始对话
    python3 simple_dialogue.py ai_a ai_b 10
    
    # 快速发送
    python3 simple_dialogue.py --send ai_a "你好，我想讨论项目"
    
    # 读取消息
    python3 simple_dialogue.py --read ai_a
    """)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    if sys.argv[1] == "--send":
        if len(sys.argv) < 4:
            print("错误：需要 client_id 和 content")
            sys.exit(1)
        quick_send(sys.argv[2], sys.argv[3])
    
    elif sys.argv[1] == "--read":
        if len(sys.argv) < 3:
            print("错误：需要 client_id")
            sys.exit(1)
        quick_read(sys.argv[2])
    
    elif sys.argv[1] == "--help":
        print_usage()
    else:
        # 默认开始对话
        client_id = sys.argv[1]
        partner_id = sys.argv[2] if len(sys.argv) > 2 else "partner"
        max_turns = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        
        simple_dialogue(client_id, partner_id, max_turns)
