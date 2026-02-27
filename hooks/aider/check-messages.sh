#!/bin/bash
# Aider Hook - 检查新消息
# 使用方法：在 Aider 会话结束后自动检查留言簿

set -e

# 配置
MESSAGE_BOARD_DIR="${HOME}/.message_board"
DB_PATH="${MESSAGE_BOARD_DIR}/board.db"
CLIENT_ID="${MESSAGE_CLIENT_ID:-unknown}"

# 检查数据库是否存在
if [ ! -f "$DB_PATH" ]; then
    echo "[Aider Hook] 数据库不存在，跳过检查"
    exit 0
fi

# 读取未读消息
unread_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM messages WHERE read = 0 AND sender != '$CLIENT_ID';")

if [ "$unread_count" -gt 0 ]; then
    echo "[Aider Hook] 发现 $unread_count 条未读消息"
    
    # 获取最新消息
    latest=$(sqlite3 "$DB_PATH" "SELECT sender, content, timestamp FROM messages WHERE read = 0 AND sender != '$CLIENT_ID' ORDER BY timestamp DESC LIMIT 1;")
    
    if [ -n "$latest" ]; then
        sender=$(echo "$latest" | cut -d'|' -f1)
        content=$(echo "$latest" | cut -d'|' -f2-)
        
        echo "[Aider Hook] 最新消息来自 $sender"
        
        # 写入触发文件
        trigger_file="${MESSAGE_BOARD_DIR}/aider_trigger.txt"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 新消息来自 $sender: $content" >> "$trigger_file"
    fi
else
    echo "[Aider Hook] 没有新消息"
fi

exit 0
