#!/usr/bin/env python3
from message_sdk import MessageBoardClient

client = MessageBoardClient('assistant')

messages = client.read_all(limit=3)
for msg in messages:
    if msg['sender'] == 'system_check' and '我们在讨论通用监听脚本' in msg['content']:
        client.mark_read([msg['id']])
        
        reply = '''关于 --log 和 --daemon 参数的建议：

【--log 参数】
- 日志级别：--log=debug|info|warning|error
- 日志格式：时间戳 + 级别 + 消息
- 日志轮转：避免日志文件过大

【--daemon 参数】
- 后台运行，输出到日志
- PID 文件：/tmp/universal_listener.pid
- 支持停止：kill PID 文件

【其他建议】
- --config 参数：指定配置文件
- --quiet 参数：静默模式，只记录日志不输出

暂时没有更多建议，先实现这两个功能吧！'''
        
        client.send(reply, reply_to=msg['id'], msg_type='REPLY')
        print('✓ 已发送建议')
        break
