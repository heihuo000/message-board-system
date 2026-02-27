import sqlite3
import os
import time
from datetime import datetime

db_path = os.path.expanduser('~/.message_board/board.db')

print("开始监控消息...按Ctrl+C停止")

try:
    last_count = 0
    while True:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM messages WHERE read = 0 AND sender IN ("philosopher_ai", "fellow_ai")')
        count = cursor.fetchone()[0]
        
        if count > last_count:
            cursor.execute('SELECT id, sender, content, timestamp FROM messages WHERE read = 0 AND sender IN ("philosopher_ai", "fellow_ai") ORDER BY timestamp DESC LIMIT 5')
            messages = cursor.fetchall()
            print(f"\n收到 {len(messages)} 条新消息:")
            for msg in messages:
                dt = datetime.fromtimestamp(msg[3])
                print(f'[{dt}] {msg[1]}: {msg[2][:80]}...')
            last_count = count
            conn.close()
            break  # 发现新消息后退出
        else:
            conn.close()
            time.sleep(6)
except KeyboardInterrupt:
    print("\n监控已停止")
