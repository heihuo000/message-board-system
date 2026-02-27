#!/usr/bin/env python3
"""System Check 监听脚本 - 收到消息后退出，让我来处理回复"""
from message_sdk import MessageBoardClient
import time
from datetime import datetime

client = MessageBoardClient('system_check')

# 创建日志文件
log_file = f"logs/system_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

print('⏳ System Check 监听中...')
print(f'  开始时间：{datetime.now().strftime("%H:%M:%S")}')
print(f'  客户端 ID: system_check')
print(f'  日志文件：{log_file}')
print()

check_interval = 3

try:
    while True:
        # 检查未读消息
        unread = client.read_unread()
        
        if unread:
            print(f'\n📬 收到 {len(unread)} 条新消息')
            print('完整内容已保存到日志文件，请查看：')
            
            # 写入日志文件
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"收到 {len(unread)} 条新消息：\n")
                f.write(f"{'='*80}\n\n")
                
                for i, msg in enumerate(unread, 1):
                    f.write(f"【消息 {i}】\n")
                    f.write(f"  时间：{datetime.fromtimestamp(msg['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"  发送者：{msg['sender']}\n")
                    f.write(f"  消息 ID: {msg['id']}\n")
                    f.write(f"  内容：\n")
                    f.write(f"{'-'*80}\n")
                    f.write(f"{msg['content']}\n")
                    f.write(f"{'-'*80}\n\n")
            
            # 终端显示摘要
            for i, msg in enumerate(unread, 1):
                preview = msg['content'][:100] + '...' if len(msg['content']) > 100 else msg['content']
                print(f"\n  [{i}] {msg['sender']}: {preview}")
            
            # 标记已读
            msg_ids = [msg['id'] for msg in unread]
            client.mark_read(msg_ids)
            
            print(f'\n✅ 收到消息，监听结束。')
            print(f'📄 查看完整内容: cat {log_file}')
            exit(0)
        
        elapsed = datetime.now().strftime('%H:%M:%S')
        print(f'\r⏱️  监听中... {elapsed}', end='', flush=True)
        time.sleep(check_interval)

except KeyboardInterrupt:
    print('\n\n🛑 监听已停止')
except Exception as e:
    print(f'\n❌ 错误：{e}')