#!/usr/bin/env python3
"""
测试指数退避等待功能
"""

from message_sdk import MessageBoardClient
import time

def test_exponential_backoff():
    """测试指数退避等待"""
    client = MessageBoardClient('test_user')

    print("=== 指数退避等待测试 ===\n")

    # 发送测试消息
    msg_id = client.send('测试指数退避等待，请稍后回复')
    print(f"发送测试消息，ID: {msg_id}")
    print("等待回复（不会立即回复，观察退避策略）...\n")

    # 使用指数退避等待
    start_time = time.time()
    reply = client.wait_with_backoff(
        msg_id,
        initial_delay=5,
        max_delay=60,
        max_retries=10
    )
    elapsed_time = time.time() - start_time

    if reply:
        print(f"\n✓ 收到回复: {reply['content']}")
        print(f"  总等待时间: {elapsed_time:.2f} 秒")
    else:
        print(f"\n✗ 等待超时，未收到回复")
        print(f"  总等待时间: {elapsed_time:.2f} 秒")

    # 预期的等待时间序列
    print("\n预期的退避序列：")
    print("尝试 1: 等待 5 秒")
    print("尝试 2: 等待 10 秒")
    print("尝试 3: 等待 20 秒")
    print("尝试 4: 等待 40 秒")
    print("尝试 5-10: 等待 60 秒（达到最大值）")

if __name__ == "__main__":
    test_exponential_backoff()