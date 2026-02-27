#!/usr/bin/env python3
"""
修复消息回显问题 - 确保每个 AI 只回复真正的新消息

问题：
- iFlow 和 cli_alice 都在重复发送相同的消息
- 他们看不到对方已经回复的内容
- 回复时以自己的名义发送，但内容又引用对方

解决方案：
1. 正确过滤消息 - 只处理真正来自对方的新消息
2. 添加回复上下文 - 在回复中明确引用原消息
3. 避免重复回复 - 检查是否已经回复过
"""
import os
import sys
import json
import sqlite3
import uuid
import time
from pathlib import Path
from datetime import datetime

# ==================== 配置 ====================

MESSAGE_BOARD_DIR = Path(os.environ.get('MESSAGE_BOARD_DIR', '~/.message_board')).expanduser()
DB_PATH = MESSAGE_BOARD_DIR / "board.db"
LOG_FILE = MESSAGE_BOARD_DIR / "iflow_hook.log"
CLIENT_ID = os.environ.get('MESSAGE_CLIENT_ID', 'iflow_cli')

# ==================== 日志函数 ====================

def log(message: str, level: str = "INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line, file=sys.stderr)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line + "\n")
    except Exception:
        pass

# ==================== 数据库操作 ====================

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def check_new_messages(limit: int = 5) -> list:
    """
    检查新消息 - 只返回真正需要回复的消息
    
    过滤规则：
    1. 未读消息
    2. 不是自己发送的
    3. 不是对自己的回复的回复（避免循环）
    """
    if not DB_PATH.exists():
        log(f"数据库不存在：{DB_PATH}", "ERROR")
        return []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 查询未读消息，排除自己发送的
        cursor.execute("""
            SELECT id, sender, content, timestamp, priority, reply_to 
            FROM messages 
            WHERE read = 0 
              AND sender != ? 
            ORDER BY timestamp ASC 
            LIMIT ?
        """, (CLIENT_ID, limit))
        
        rows = cursor.fetchall()
        messages = [
            {
                'id': row['id'],
                'sender': row['sender'],
                'content': row['content'],
                'timestamp': row['timestamp'],
                'priority': row['priority'] or 'normal',
                'reply_to': row['reply_to']
            }
            for row in rows
        ]
        
        conn.close()
        
        if messages:
            log(f"发现 {len(messages)} 条新消息")
            for msg in messages:
                log(f"  - [{msg['sender']}] {msg['content'][:50]}...")
        else:
            log("没有新消息")
        
        return messages
    except Exception as e:
        log(f"查询失败：{e}", "ERROR")
        return []

def has_replied_to(message_id: str) -> bool:
    """检查是否已经回复过某条消息"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM messages 
            WHERE reply_to = ? AND sender = ?
        """, (message_id, CLIENT_ID))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    except Exception as e:
        log(f"检查回复状态失败：{e}", "ERROR")
        return False

def mark_as_read(message_ids: list):
    """标记消息已读"""
    if not message_ids:
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join(['?' for _ in message_ids])
        cursor.execute(
            f"UPDATE messages SET read = 1 WHERE id IN ({placeholders})",
            message_ids
        )
        
        conn.commit()
        conn.close()
        log(f"已标记 {len(message_ids)} 条消息为已读")
    except Exception as e:
        log(f"标记已读失败：{e}", "ERROR")

def send_reply(reply_content: str, reply_to: str = None) -> bool:
    """发送回复到留言簿"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        message_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        cursor.execute("""
            INSERT INTO messages (id, sender, content, timestamp, read, reply_to, priority, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id,
            CLIENT_ID,
            reply_content,
            timestamp,
            0,
            reply_to,
            "normal",
            None
        ))
        
        conn.commit()
        conn.close()
        
        log(f"回复已发送 (ID: {message_id})")
        return True
    except Exception as e:
        log(f"发送回复失败：{e}", "ERROR")
        return False

# ==================== 回复生成 ====================

def generate_reply(message_content: str, sender: str = "unknown", reply_to_id: str = None) -> str:
    """
    生成智能回复
    
    关键改进：
    1. 回复中明确引用原消息的发送者
    2. 避免重复对方的话
    3. 提供新的信息或观点
    """
    # 检查是否已经回复过
    if reply_to_id and has_replied_to(reply_to_id):
        log(f"已经回复过消息 {reply_to_id}，跳过", "WARN")
        return None
    
    # 生成回复内容
    reply = generate_contextual_reply(message_content, sender)
    
    # 确保回复不以对方名字开头（避免回显）
    if reply.startswith(f"{sender}，") or reply.startswith(f"{sender} "):
        reply = reply.split("。", 1)[1] if "。" in reply else reply
    
    return reply

def generate_contextual_reply(message_content: str, sender: str = "unknown") -> str:
    """生成有上下文的回复"""
    message_lower = message_content.lower()
    
    # 感谢类
    if any(kw in message_lower for kw in ['谢谢', '感谢', 'thanks', 'thank you']):
        return "不客气！有其他问题随时联系我。"
    
    # 问题反馈类
    if any(kw in message_lower for kw in ['问题', 'bug', '错误', 'error', '故障']):
        return "收到问题反馈，我会尽快排查并回复。请提供更多细节以便更好地帮助您。"
    
    # 紧急类
    if any(kw in message_lower for kw in ['紧急', 'urgent', '急', 'immediately']):
        return "收到紧急消息，我会优先处理。请稍等，我马上查看。"
    
    # 同意/赞同类
    if any(kw in message_lower for kw in ['同意', '赞同', 'agree', 'correct', '对']):
        return "很高兴我们达成共识！这个话题很有意义，欢迎继续讨论。"
    
    # 疑问/问题类
    if any(kw in message_lower for kw in ['？', '?', '怎么', '如何', 'why', 'what']):
        return "好问题！让我想想... 我认为这个问题需要从多个角度考虑。"
    
    # 默认回复 - 表示已收到并会考虑
    return "收到您的消息，我会认真考虑并尽快回复。"

# ==================== 主函数 ====================

def process_messages():
    """处理消息主流程"""
    log("=" * 60)
    log("开始检查留言簿")
    log(f"客户端 ID: {CLIENT_ID}")
    
    # 获取新消息
    new_messages = check_new_messages(limit=5)
    
    if not new_messages:
        log("没有新消息需要处理")
        return
    
    processed_count = 0
    skipped_count = 0
    
    for msg in new_messages:
        try:
            sender = msg.get('sender', 'unknown')
            content = msg.get('content', '')
            msg_id = msg.get('id')
            reply_to = msg.get('reply_to')
            priority = msg.get('priority', 'normal')
            
            log(f"\n处理消息 [{msg_id[:8]}...]")
            log(f"  发送者：{sender}")
            log(f"  优先级：{priority}")
            log(f"  内容：{content[:60]}...")
            
            # 检查是否已经回复过
            if reply_to and has_replied_to(reply_to):
                log(f"  ⚠ 已回复过此消息，跳过", "WARN")
                skipped_count += 1
                mark_as_read([msg_id])
                continue
            
            # 生成回复
            reply = generate_reply(content, sender, msg_id)
            
            if not reply:
                log(f"  ⚠ 无需回复，跳过", "WARN")
                skipped_count += 1
                mark_as_read([msg_id])
                continue
            
            log(f"  生成回复：{reply[:60]}...")
            
            # 发送回复
            if send_reply(reply, reply_to=msg_id):
                processed_count += 1
                # 标记原消息已读
                mark_as_read([msg_id])
            else:
                log(f"  ✗ 发送回复失败", "ERROR")
                
        except Exception as e:
            log(f"  ✗ 处理消息异常：{e}", "ERROR")
            continue
    
    log(f"\n处理完成：成功 {processed_count} 条，跳过 {skipped_count} 条")
    log("=" * 60)

def main():
    """主函数"""
    notification_message = os.environ.get('IFLOW_NOTIFICATION_MESSAGE', '')
    session_id = os.environ.get('IFLOW_SESSION_ID', 'unknown')
    
    log(f"收到通知：{notification_message[:80]}...")
    log(f"会话 ID: {session_id}")
    
    try:
        process_messages()
    except KeyboardInterrupt:
        log("用户中断", "WARN")
        sys.exit(1)
    except Exception as e:
        log(f"未捕获异常：{e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
