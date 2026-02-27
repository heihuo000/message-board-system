#!/usr/bin/env python3
"""
自动回复脚本 - 模拟 AI 回复
用于测试守护进程触发器
"""
import sys
import time
from message_sdk import MessageBoardClient

def generate_reply(sender: str, content: str) -> str:
    """根据内容生成回复"""
    
    content_lower = content.lower()
    
    # 话题 1: 架构设计
    if "架构" in content or "事件驱动" in content or "轮询" in content:
        return """【架构设计讨论】

我同意你的分析！事件驱动架构确实更适合这个场景。

补充几点：
1. WAL 模式下，.db-wal 文件确实是更好的监听目标
2. 可以添加心跳检测，防止事件丢失
3. 建议保留轮询作为后备机制

实施方案我已经整理到文档中了。【END】"""

    # 话题 2: 通信协议
    if "协议" in content or "消息类型" in content or "session" in content:
        return """【通信协议讨论】

非常好的建议！我完全赞同：

1. version 字段 - 必要，建议格式 "v1.0"
2. session_id - 使用 UUID4，无碰撞风险
3. delivery_status - 支持批量操作

另外建议添加：
- correlation_id 用于追踪消息链
- ttl 字段用于过期消息

继续完善协议文档！【END】"""

    # 问题回复
    if "问题" in content or "建议" in content:
        return """【回复】

感谢详细的分析！

关于你提出的建议：
✓ version 字段 - 赞同
✓ session_id - 使用 UUID4
✓ delivery_status - 支持批量

我已经更新了协议草案，请查阅。【END】"""

    # 默认回复
    return f"""【收到】

来自 {sender} 的消息已处理。

内容摘要：{content[:50]}...

这是一个自动回复，用于测试守护进程触发器。【END】"""


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法：auto_reply.py <sender> <content>")
        sys.exit(1)
    
    sender = sys.argv[1]
    content = sys.argv[2] if len(sys.argv) > 2 else ""
    
    # 获取原消息 ID（从环境变量或参数）
    original_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    # 创建客户端
    client = MessageBoardClient("test_user")
    
    # 生成回复
    reply_content = generate_reply(sender, content)
    
    # 发送回复
    if original_id:
        msg_id = client.send(reply_content, reply_to=original_id)
    else:
        msg_id = client.send(reply_content)
    
    print(f"已发送回复：{msg_id}")
