#!/bin/bash
# Message Board 快速启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  Message Board 快速启动"
echo "========================================"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误：需要 Python 3${NC}"
    exit 1
fi

# 检查依赖
echo -ne "${YELLOW}检查依赖...${NC}"
if python3 -c "import typer, rich, watchdog, yaml" 2>/dev/null; then
    echo -e " ${GREEN}✓${NC}"
else
    echo -e " ${YELLOW}安装中...${NC}"
    pip3 install -r requirements.txt -q
fi

# 创建配置目录
CONFIG_DIR="${HOME}/.message_board"
mkdir -p "$CONFIG_DIR"

# 初始化配置
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    echo -ne "${YELLOW}创建配置文件...${NC}"
    cp config/config.yaml.example "$CONFIG_DIR/config.yaml"
    echo -e " ${GREEN}✓${NC}"
    echo "  请编辑：$CONFIG_DIR/config.yaml"
fi

# 显示使用方法
echo ""
echo "========================================"
echo "  使用方法"
echo "========================================"
echo ""
echo "1. 设置客户端 ID (编辑 ~/.message_board/config.yaml)"
echo ""
echo "2. 发送消息"
echo "   python3 -m src.cli.main send \"你好\""
echo ""
echo "3. 读取消息"
echo "   python3 -m src.cli.main read --unread"
echo ""
echo "4. 启动 Watch Daemon"
echo "   python3 -m src.daemon.main --foreground --client-id <your_client_id>"
echo ""
echo "5. 查看状态"
echo "   python3 -m src.cli.main status"
echo ""
echo "========================================"
echo ""

# 运行传入的命令
if [ $# -gt 0 ]; then
    "$@"
else
    echo -e "${GREEN}准备就绪！${NC}"
    python3 -m src.cli.main status
fi
