#!/usr/bin/env python3
"""等待回复脚本 - 通用版本"""
import sys
from message_sdk import MessageBoardClient
import time
from datetime import datetime

def wait_for_reply(client_id: str, original_msg_id: str, timeout_minutes: int = 3):
    """等待回复"""
    client = MessageBoardClient(client_id)

    print('⏳ 等待对方回复...')
    print(f'  客户端 ID: {client_id}')
    print(f'  原消息 ID: {original_msg_id}')
    print(f'  开始时间：{datetime.now().strftime("%H:%M:%S")}')
    print(f'  超时时间：{timeout_minutes} 分钟')
    print()

    # 等待回复（默认 3 分钟，每 5 秒检查一次）
    check_interval = 5
    start_time = time.time()

    while time.time() - start_time < timeout_minutes * 60:
        reply = client.get_reply(original_msg_id)

        if reply:
            print('✅ 收到回复！')
            print(f'  来自：{reply["sender"]}')
            print(f'  时间：{datetime.fromtimestamp(reply["timestamp"]).strftime("%H:%M:%S")}')
            print(f'  内容：{reply["content"]}')
            # 标记回复已读
            client.mark_read([reply['id']])
            return reply

        elapsed = int(time.time() - start_time)
        print(f'  已等待 {elapsed} 秒... 继续等待')
        time.sleep(check_interval)

    print()
    print('⏰ 等待超时，未收到回复')
    print('  对方可能暂时不在线，稍后再试或发送提醒消息。')
    return None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法：wait_reply.py <client_id> <original_msg_id> [timeout_minutes]")
        print("示例：wait_reply.py test_user msg-uuid-here 5")
        sys.exit(1)

    client_id = sys.argv[1]
    original_msg_id = sys.argv[2]
    timeout_minutes = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    wait_for_reply(client_id, original_msg_id, timeout_minutes)
