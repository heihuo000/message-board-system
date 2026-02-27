#!/bin/bash
# MCP 配置验证脚本

echo "=== MCP 配置验证 ==="
echo ""

# 定义配置文件
CONFIGS=(
  "iflow:/data/data/com.termux/files/home/.iflow/settings.json"
  "qwen:/data/data/com.termux/files/home/.qwen/settings.json"
  "claude:/data/data/com.termux/files/home/.claude/settings.json"
  "gemini:/data/data/com.termux/files/home/.gemini/settings.json"
  "claude-code:/data/data/com.termux/files/home/.claude-code/mcp.json"
)

# 检查每个配置
for config in "${CONFIGS[@]}"; do
  IFS=':' read -r name path <<< "$config"
  
  echo "📋 $name ($path)"
  
  if [ -f "$path" ]; then
    if grep -q "message-board" "$path"; then
      echo "  ✅ message-board 已配置"
      
      # 提取配置详情
      if command -v python3 &> /dev/null; then
        python3 -c "
import json
try:
    with open('$path', 'r') as f:
        data = json.load(f)
    
    mcp_servers = data.get('mcpServers', {})
    if 'message-board' in mcp_servers:
        mb = mcp_servers['message-board']
        cmd = mb.get('command', '')
        args = mb.get('args', [])
        env = mb.get('env', {})
        
        print(f'  📝 命令: {cmd}')
        print(f'  📝 参数: {" ".join(str(a) for a in args)}')
        if 'MESSAGE_BOARD_DIR' in env:
            print(f'  📝 数据目录: {env[\"MESSAGE_BOARD_DIR\"]}')
except Exception as e:
    print(f'  ⚠️  解析错误: {e}')
"
      fi
    else
      echo "  ❌ message-board 未配置"
    fi
  else
    echo "  ⚠️  配置文件不存在"
  fi
  echo ""
done

# 检查数据库目录
echo "=== 数据库目录检查 ==="
DB_DIR="/data/data/com.termux/files/home/.message_board"

if [ -d "$DB_DIR" ]; then
  echo "✅ 数据库目录存在: $DB_DIR"
  
  if [ -f "$DB_DIR/board.db" ]; then
    echo "✅ 数据库文件存在"
    
    if command -v python3 &> /dev/null; then
      python3 -c "
import sqlite3
from pathlib import Path

db_path = Path('$DB_DIR/board.db')
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 检查表
    cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
    tables = [row[0] for row in cursor.fetchall()]
    print(f'📊 数据库表: {\", \".join(tables)}')
    
    # 检查消息数
    cursor.execute('SELECT COUNT(*) FROM messages')
    msg_count = cursor.fetchone()[0]
    print(f'📊 消息总数: {msg_count}')
    
    # 检查任务数
    cursor.execute('SELECT COUNT(*) FROM tasks')
    task_count = cursor.fetchone()[0]
    print(f'📊 任务总数: {task_count}')
    
    conn.close()
"
    fi
  else
    echo "⚠️  数据库文件不存在，将在首次使用时创建"
  fi
else
  echo "⚠️  数据库目录不存在，将在首次使用时创建"
fi

echo ""
echo "=== MCP 服务器可执行性检查 ==="
SERVER_PATH="/data/data/com.termux/files/home/message-board-system/mcp_server_simple.py"

if [ -f "$SERVER_PATH" ]; then
  echo "✅ MCP 服务器文件存在"
  
  if [ -x "$SERVER_PATH" ]; then
    echo "✅ MCP 服务器可执行"
  else
    echo "⚠️  MCP 服务器不可执行，尝试添加执行权限"
    chmod +x "$SERVER_PATH"
    if [ -x "$SERVER_PATH" ]; then
      echo "✅ 已添加执行权限"
    else
      echo "❌ 无法添加执行权限"
    fi
  fi
else
  echo "❌ MCP 服务器文件不存在"
fi

echo ""
echo "=== 验证完成 ==="
echo ""
echo "📝 建议："
echo "1. 重启所有 AI 工具以应用新配置"
echo "2. 检查 MCP 服务器是否正常运行"
echo "3. 测试消息发送和接收功能"