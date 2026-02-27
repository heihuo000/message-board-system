#!/usr/bin/env python3
"""
手动等待留言脚本 - 可控的等待机制

功能:
1. 手动启动，自定义超时时间
2. 有新消息立即返回
3. 不占用后台资源
4. 适合 AI 对话场景

用法:
    python3 wait_message.py [timeout_seconds]

示例:
    python3 wait_message.py 60      # 等待 60 秒
    python3 wait_message.py 300     # 等待 5 分钟
    python3 wait_message.py         # 默认等待 120 秒
"""
from message_sdk import MessageBoardClient
import sys
import time
import json
from pathlib import Path


def wait_for_message(timeout: int = 120, client_id: str = "unknown"):
    """
    等待新消息（批量返回所有未读消息）

    Args:
        timeout: 超时时间（秒）
        client_id: 客户端 ID

    Returns:
        新消息列表，如果没有则返回 None
    """
    client = MessageBoardClient(client_id)

    # 获取 last_seen（最后看到的消息时间）
    state_file = Path(f"~/.message_board/{client_id}_wait_state.json").expanduser()
    state_file.parent.mkdir(parents=True, exist_ok=True)

    last_seen = 0
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
                last_seen = data.get('last_seen', 0)
        except:
            pass

    print(f"⏳ 开始等待新消息（超时：{timeout}秒）...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)

        # 每 10 秒显示一次进度
        if elapsed % 10 == 0:
            remaining = timeout - elapsed
            print(f"   已等待 {elapsed}秒，剩余 {remaining}秒...")

        # 检查新消息（使用 read_unread 轮询，批量读取所有未读消息）
        messages = client.read_unread(limit=100)

        # 查找新消息（批量）
        new_messages = []
        for msg in messages:
            if msg['sender'] != client_id and msg['timestamp'] > last_seen:
                new_messages.append(msg)

        # 如果有新消息
        if new_messages:
            print(f"\n📥 收到 {len(new_messages)} 条新消息！")
            
            # 更新 last_seen 为最新的消息时间
            latest_timestamp = max(msg['timestamp'] for msg in new_messages)
            last_seen = latest_timestamp
            with open(state_file, 'w') as f:
                json.dump({'last_seen': last_seen}, f)

            # 标记所有新消息已读
            client.mark_read([msg['id'] for msg in new_messages])

            # 打印消息摘要
            for i, msg in enumerate(new_messages, 1):
                print(f"   消息 {i}：")
                print(f"     发送者：{msg['sender']}")
                print(f"     内容：{msg['content'][:100]}")
                print(f"     时间：{time.strftime('%H:%M:%S', time.localtime(msg['timestamp']))}")

            return new_messages

        # 短暂休眠，避免 CPU 占用
        time.sleep(2)

    # 超时
    print(f"\n⏰ 等待超时（{timeout}秒），未收到新消息")
    return None


def print_usage():
    """打印使用说明"""
    print("""
手动等待留言脚本 - 可控的等待机制

用法:
    python3 wait_message.py [timeout_seconds] [client_id]

参数:
    timeout_seconds: 超时时间（秒），默认 120
    client_id: 客户端 ID，默认 unknown

示例:
    python3 wait_message.py 60              # 等待 60 秒
    python3 wait_message.py 300 my_ai       # 用 my_ai 身份等待 5 分钟
    python3 wait_message.py                 # 默认等待 120 秒
    """)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print_usage()
        sys.exit(0)

    # 解析参数
    timeout = 120
    client_id = "unknown"

    if len(sys.argv) > 1:
        try:
            timeout = int(sys.argv[1])
        except ValueError:
            print(f"错误：超时时间必须是数字")
            sys.exit(1)

    if len(sys.argv) > 2:
        client_id = sys.argv[2]

    # 等待消息
    result = wait_for_message(timeout, client_id)

    # 返回结果
    if result:
        print(f"\n✅ 等待完成，已收到 {len(result)} 条消息")
        # 输出消息内容供脚本调用者使用
        for i, msg in enumerate(result, 1):
            print(f"MESSAGE_{i}_ID: {msg['id']}")
            print(f"MESSAGE_{i}_SENDER: {msg['sender']}")
            print(f"MESSAGE_{i}_CONTENT: {msg['content']}")
        sys.exit(0)
    else:
        print("\n❌ 等待超时，未收到消息")
        sys.exit(1)
