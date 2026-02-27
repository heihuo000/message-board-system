#!/usr/bin/env python3
"""
iFlow Notification Hook 触发器
当 iFlow 发送通知时，自动检查留言簿并触发回复

使用方法：
  在 ~/.iflow/settings.json 中配置：
  {
    "hooks": {
      "Notification": [
        {
          "matcher": ".*",
          "hooks": [
            {
              "type": "command",
              "command": "python3 ~/.message_board/hooks/iflow_trigger.py",
              "timeout": 60
            }
          ]
        }
      ]
    }
  }
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime


# ==================== 配置 ====================

MESSAGE_BOARD_DIR = Path(os.environ.get('MESSAGE_BOARD_DIR', '~/.message_board')).expanduser()
DB_PATH = MESSAGE_BOARD_DIR / "board.db"
CLI_PATH = MESSAGE_BOARD_DIR.parent / "message-board-system" / "src" / "cli" / "main.py"
LOG_FILE = MESSAGE_BOARD_DIR / "iflow_hook.log"
CLIENT_ID = os.environ.get('MESSAGE_CLIENT_ID', 'iflow_cli')

# LLM 配置（可选）
USE_LLM = os.environ.get('USE_LLM', 'false').lower() == 'true'
LLM_COMMAND = os.environ.get('LLM_COMMAND', 'ollama run qwen2.5:7b')

# ==================== 日志函数 ====================

def log(message: str, level: str = "INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    
    # 输出到 stderr（iFlow 会捕获）
    print(log_line, file=sys.stderr)
    
    # 写入日志文件
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line + "\n")
    except Exception:
        pass


# ==================== 数据库操作 ====================

def check_new_messages(limit: int = 5) -> list:
    """检查新消息（使用 Python sqlite3 模块）"""
    if not DB_PATH.exists():
        log(f"数据库不存在：{DB_PATH}", "ERROR")
        return []
    
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, sender, content, timestamp, priority, reply_to 
            FROM messages 
            WHERE read = 0 AND sender != ? 
            ORDER BY timestamp DESC 
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
        return messages
    except Exception as e:
        log(f"查询失败：{e}", "ERROR")
        return []


def mark_as_read(message_ids: list):
    """标记消息已读（使用 Python sqlite3 模块）"""
    if not message_ids:
        return
    
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
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
    """发送回复到留言簿（直接使用数据库）"""
    try:
        import sqlite3
        import uuid
        import time
        
        conn = sqlite3.connect(str(DB_PATH))
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


# ==================== AI 回复生成 ====================

def generate_ai_reply(message_content: str, sender: str = "unknown") -> str:
    """
    生成 AI 回复
    
    策略：
    1. 如果配置了 LLM，调用 LLM 生成
    2. 否则使用预设回复模板
    """
    if USE_LLM:
        return generate_llm_reply(message_content, sender)
    else:
        return generate_template_reply(message_content, sender)


def generate_llm_reply(message_content: str, sender: str = "unknown") -> str:
    """调用 LLM 生成回复"""
    try:
        prompt = f"""收到留言（来自 {sender}）：
{message_content}

请生成简短、友好的回复（不超过 100 字）。"""

        result = subprocess.run(
            LLM_COMMAND.split() + [prompt],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            log(f"LLM 返回异常：{result.stderr}", "WARN")
            return generate_template_reply(message_content, sender)
    except subprocess.TimeoutExpired:
        log("LLM 调用超时", "WARN")
        return generate_template_reply(message_content, sender)
    except Exception as e:
        log(f"LLM 调用失败：{e}", "WARN")
        return generate_template_reply(message_content, sender)


def generate_template_reply(message_content: str, sender: str = "unknown") -> str:
    """使用模板生成回复"""
    templates = [
        f"收到您的消息，我会尽快处理。",
        f"谢谢 {sender} 的留言，已收到。",
        f"消息已收到，正在处理中...",
        f"感谢您的反馈，我会尽快回复。",
    ]
    
    # 简单关键词匹配
    message_lower = message_content.lower()
    
    if any(kw in message_lower for kw in ['问题', 'bug', '错误', 'error']):
        return "收到问题反馈，我会尽快排查并回复。"
    
    if any(kw in message_lower for kw in ['谢谢', '感谢', 'thanks']):
        return "不客气！有其他问题随时联系我。"
    
    if any(kw in message_lower for kw in ['紧急', 'urgent', '急']):
        return "收到紧急消息，我会优先处理。"
    
    # 默认回复
    import random
    return random.choice(templates)


# ==================== 主函数 ====================

def main():
    """主函数"""
    # 获取环境变量
    notification_message = os.environ.get('IFLOW_NOTIFICATION_MESSAGE', '')
    session_id = os.environ.get('IFLOW_SESSION_ID', 'unknown')
    
    log("=" * 50)
    log(f"收到通知：{notification_message[:100]}...")
    log(f"会话 ID: {session_id}")
    
    # 检查新消息
    new_messages = check_new_messages(limit=5)
    
    if not new_messages:
        log("没有新消息，跳过处理")
        return
    
    log(f"开始处理 {len(new_messages)} 条新消息")
    
    # 处理每条消息
    processed_count = 0
    for msg in new_messages:
        try:
            sender = msg.get('sender', 'unknown')
            content = msg.get('content', '')
            msg_id = msg.get('id')
            priority = msg.get('priority', 'normal')
            timestamp = msg.get('timestamp', 0)
            
            log(f"处理消息 [{sender}] (优先级：{priority})")
            
            # 生成回复
            reply = generate_ai_reply(content, sender)
            log(f"生成回复：{reply[:50]}...")
            
            # 发送回复
            if send_reply(reply, reply_to=msg_id):
                processed_count += 1
                # 标记已读
                mark_as_read([msg_id])
            else:
                log(f"消息 {msg_id} 处理失败", "ERROR")
        except Exception as e:
            log(f"处理消息异常：{e}", "ERROR")
            continue
    
    log(f"处理完成：成功 {processed_count}/{len(new_messages)} 条")
    log("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("用户中断", "WARN")
        sys.exit(1)
    except Exception as e:
        log(f"未捕获异常：{e}", "ERROR")
        sys.exit(1)
