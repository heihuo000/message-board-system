#!/bin/bash
# Claude Code Hook - 检查新消息（仅通知，不标记已读）
# 使用方法：在 Claude Code 会话结束后自动检查留言簿

set -e

# 配置
MESSAGE_BOARD_DIR="${HOME}/.message_board"
DB_PATH="${MESSAGE_BOARD_DIR}/board.db"
CLIENT_ID="${MESSAGE_CLIENT_ID:-unknown}"

# 检查数据库是否存在
if [ ! -f "$DB_PATH" ]; then
    echo "[Hook] 数据库不存在，跳过检查"
    exit 0
fi

# 读取未读消息（排除自己发送的）- 仅查询，不标记
unread_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM messages WHERE read = 0 AND sender != '$CLIENT_ID';")

if [ "$unread_count" -gt 0 ]; then
    echo "[Hook] 发现 $unread_count 条未读消息"
    
    # 获取最新消息详情
    latest=$(sqlite3 "$DB_PATH" "SELECT id, sender, content, timestamp FROM messages WHERE read = 0 AND sender != '$CLIENT_ID' ORDER BY timestamp DESC LIMIT 1;")
    
    if [ -n "$latest" ]; then
        msg_id=$(echo "$latest" | cut -d'|' -f1)
        sender=$(echo "$latest" | cut -d'|' -f2)
        content=$(echo "$latest" | cut -d'|' -f3)
        timestamp=$(echo "$latest" | cut -d'|' -f4)
        
        echo "[Hook] 最新消息来自 $sender (ID: ${msg_id:0:8}...): ${content:0:50}..."
        
        # 只通知，不标记已读
        # 写入触发文件（供其他进程使用）
        TRIGGER_FILE="${MESSAGE_BOARD_DIR}/trigger_queue.json"
        echo "{\"sender\": \"$sender\", \"content\": \"$content\", \"timestamp\": $timestamp, \"message_id\": \"$msg_id\"}" >> "$TRIGGER_FILE"
        
        # 发送系统通知（如果有）
        if command -v notify-send &> /dev/null; then
            notify-send "新留言" "来自 $sender: ${content:0:50}"
        fi
    fi
else
    echo "[Hook] 没有新消息"
fi

exit 0
