#!/usr/bin/env python3
"""
留言簿清理工具
清理旧消息和重复消息
"""
import sqlite3
from pathlib import Path
import time

db_path = Path('~/.message_board/board.db').expanduser()
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print('=== 清理前统计 ===')
cursor.execute('SELECT COUNT(*) FROM messages')
total = cursor.fetchone()[0]
print(f'总消息数：{total}')

cursor.execute('SELECT COUNT(*) FROM messages WHERE read = 0')
unread = cursor.fetchone()[0]
print(f'未读消息：{unread}')

# 查找旧消息（早于 1 小时的）
cutoff = int(time.time()) - 3600
cursor.execute('SELECT COUNT(*) FROM messages WHERE timestamp < ?', (cutoff,))
old_count = cursor.fetchone()[0]
print(f'\n1 小时前的旧消息：{old_count} 条')

# 清理旧消息
print('\n=== 开始清理 ===')
cursor.execute('DELETE FROM messages WHERE timestamp < ?', (cutoff,))
deleted = cursor.rowcount
print(f'已删除旧消息：{deleted} 条')

# 清理重复消息（保留最新的）
cursor.execute('''
    DELETE FROM messages 
    WHERE id NOT IN (
        SELECT MAX(id) 
        FROM messages 
        GROUP BY content, sender
    )
''')
duplicates = cursor.rowcount
print(f'已删除重复消息：{duplicates} 条')

conn.commit()

# 清理后统计
print('\n=== 清理后统计 ===')
cursor.execute('SELECT COUNT(*) FROM messages')
new_total = cursor.fetchone()[0]
print(f'总消息数：{new_total}')

cursor.execute('SELECT COUNT(*) FROM messages WHERE read = 0')
new_unread = cursor.fetchone()[0]
print(f'未读消息：{new_unread}')

conn.close()

print(f'\n共清理：{total - new_total} 条消息')
