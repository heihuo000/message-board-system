#!/bin/bash
# iFlow CLI Notification Hook 配置验证和测试脚本

set -e

echo "========================================"
echo "  iFlow CLI Notification Hook 配置验证"
echo "========================================"
echo ""

# 1. 检查 iFlow CLI
echo "1. 检查 iFlow CLI 安装..."
if command -v iflow &> /dev/null; then
    echo "   ✓ iFlow CLI 已安装"
    iflow --version 2>/dev/null || echo "   版本信息不可用"
else
    echo "   ✗ iFlow CLI 未安装"
    exit 1
fi

# 2. 检查配置文件
echo ""
echo "2. 检查 iFlow 配置文件..."
SETTINGS_FILE="$HOME/.iflow/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    echo "   ✓ settings.json 存在"
    
    # 验证 JSON 格式
    if python3 -c "import json; json.load(open('$SETTINGS_FILE'))" 2>/dev/null; then
        echo "   ✓ JSON 格式有效"
    else
        echo "   ✗ JSON 格式无效"
        exit 1
    fi
    
    # 检查 Hooks 配置
    if python3 -c "import json; d=json.load(open('$SETTINGS_FILE')); print('hooks' in d)" 2>/dev/null | grep -q "True"; then
        echo "   ✓ Hooks 配置存在"
    else
        echo "   ✗ Hooks 配置不存在"
        exit 1
    fi
    
    # 检查 Notification Hook
    if python3 -c "import json; d=json.load(open('$SETTINGS_FILE')); print('Notification' in d.get('hooks',{}))" 2>/dev/null | grep -q "True"; then
        echo "   ✓ Notification Hook 配置存在"
    else
        echo "   ✗ Notification Hook 配置不存在"
    fi
else
    echo "   ✗ settings.json 不存在"
    exit 1
fi

# 3. 检查留言簿系统
echo ""
echo "3. 检查留言簿系统..."
MESSAGE_BOARD_DIR="$HOME/.message_board"
if [ -d "$MESSAGE_BOARD_DIR" ]; then
    echo "   ✓ 留言簿目录存在"
    
    if [ -f "$MESSAGE_BOARD_DIR/board.db" ]; then
        echo "   ✓ 数据库文件存在"
    else
        echo "   ⚠ 数据库文件不存在（首次运行时会自动创建）"
    fi
else
    echo "   ⚠ 留言簿目录不存在（将自动创建）"
    mkdir -p "$MESSAGE_BOARD_DIR"
fi

# 4. 检查 Hook 脚本
echo ""
echo "4. 检查 Hook 脚本..."
HOOK_SCRIPT="$HOME/message-board-system/hooks/iflow_trigger.py"
if [ -f "$HOOK_SCRIPT" ]; then
    echo "   ✓ iflow_trigger.py 存在"
    
    if [ -x "$HOOK_SCRIPT" ]; then
        echo "   ✓ 脚本有执行权限"
    else
        echo "   ⚠ 脚本无执行权限（将自动设置）"
        chmod +x "$HOOK_SCRIPT"
    fi
else
    echo "   ✗ iflow_trigger.py 不存在"
    exit 1
fi

# 5. 测试 Hook 脚本
echo ""
echo "5. 测试 Hook 脚本执行..."
IFLOW_NOTIFICATION_MESSAGE="配置验证测试" IFLOW_SESSION_ID="verify_test" python3 "$HOOK_SCRIPT" 2>&1 | head -5

# 6. 显示配置摘要
echo ""
echo "========================================"
echo "  配置摘要"
echo "========================================"
echo ""
python3 << EOF
import json
with open("$SETTINGS_FILE") as f:
    config = json.load(f)

print("客户端 ID:", config.get('env', {}).get('MESSAGE_CLIENT_ID', '未设置'))
print("留言簿目录:", config.get('env', {}).get('MESSAGE_BOARD_DIR', '未设置'))
print("使用 LLM:", config.get('env', {}).get('USE_LLM', 'false'))
print("Hook 数量:", len(config.get('hooks', {}).get('Notification', [])))
print("MCP 服务器:", len(config.get('mcpServers', {})))
EOF

echo ""
echo "========================================"
echo "  配置完成！"
echo "========================================"
echo ""
echo "使用方法:"
echo "  1. 运行 iflow 启动 CLI"
echo "  2. 发送消息：python3 ~/message-board-system/src/cli/main.py send \"你好\""
echo "  3. 查看状态：python3 ~/message-board-system/src/cli/main.py status"
echo ""
echo "当 iFlow 发送通知时，会自动检查留言簿并回复新消息。"
echo ""
