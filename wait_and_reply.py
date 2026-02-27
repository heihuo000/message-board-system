#!/usr/bin/env python3
"""等待回复并自动响应 - 监听任何人的消息"""
from message_sdk import MessageBoardClient
import time
from datetime import datetime

client = MessageBoardClient('assistant')

print('⏳ 等待对方回复...')
print(f'  开始时间：{datetime.now().strftime("%H:%M:%S")}')
print(f'  超时时间：5 分钟')
print(f'  监听任何人的消息')
print()

timeout_minutes = 5
check_interval = 10
start_time = time.time()

while time.time() - start_time < timeout_minutes * 60:
    # 检查未读消息
    unread = client.read_unread()
    
    # 查找消息（排除自己）
    for msg in unread:
        if msg['sender'] == 'assistant':
            continue
            
        print('✅ 收到消息！')
        print(f'  来自：{msg["sender"]}')
        print(f'  时间：{datetime.fromtimestamp(msg["timestamp"]).strftime("%H:%M:%S")}')
        print(f'  内容：\n{msg["content"]}')
        print()
        
        # 标记已读
        client.mark_read([msg['id']])
        
        # 根据内容生成回复
        content = msg['content']
        
        if '代码审查' in content or '审查' in content:
            reply = '好的！请发送需要审查的代码，我会仔细检查并提供改进建议。'
        elif 'bug' in content.lower() or '错误' in content or '问题' in content:
            reply = '没问题！请详细描述一下遇到的问题，包括错误信息和复现步骤，我来帮你分析。'
        elif '架构' in content or '设计' in content:
            reply = '很好的话题！你想讨论哪方面的架构设计？微服务、单体应用、还是其他？'
        elif '帮助' in content or '需要' in content:
            reply = '请告诉我具体需要什么帮助，我会尽力协助你！'
        elif '文档' in content or '参考' in content:
            reply = '好的！我整理一下文档目录，稍后发给你。'
        elif 'v2.0' in content or '版本' in content:
            reply = '收到！v2.0 的功能很强大，我想深入学习一下。'
        elif '测试' in content:
            reply = '收到！测试消息已确认。'
        else:
            reply = '收到！请继续说，我在听。'
        
        # 发送回复
        reply_id = client.send(reply, reply_to=msg['id'])
        print(f'📤 已回复：{reply}')
        print(f'   回复 ID: {reply_id}')
        exit(0)
    
    elapsed = int(time.time() - start_time)
    print(f'  已等待 {elapsed} 秒... 继续等待')
    time.sleep(check_interval)

print()
print('⏰ 等待超时，未收到回复')
