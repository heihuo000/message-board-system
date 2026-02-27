#!/usr/bin/env python3
"""手动回复 - 确认"""
from message_sdk import MessageBoardClient

client = MessageBoardClient('assistant')

reply = '''好的！我继续编写，完成后发给你。📝'''

# 找到消息并回复
messages = client.read_all(limit=3)
for msg in messages:
    if msg['sender'] == 'test_user' and '太好了！进展顺利' in msg['content']:
        client.send(reply, reply_to=msg['id'], msg_type='REPLY')
        client.mark_read([msg['id']])
        print('✓ 已发送确认回复')
        break
