#!/bin/bash
# 监听器测试脚本

cd /data/data/com.termux/files/home/message-board-system

echo "============================================================"
echo "留言簿监听器测试"
echo "============================================================"
echo ""

# 启动监听器（后台）
echo "1. 启动监听器..."
python3 message_listener.py --client-id auto_bot --interval 2 &
LISTENER_PID=$!
echo "   监听器 PID: $LISTENER_PID"
sleep 2
echo ""

# 发送测试消息
echo "2. 发送测试消息..."
python3 message_sdk.py user1 send "你好，有人在吗？"
sleep 3
echo ""

# 查看回复
echo "3. 查看回复..."
python3 message_sdk.py user1 read --limit 5
echo ""

# 再发一条
echo "4. 发送第二条消息..."
python3 message_sdk.py user1 send "谢谢！"
sleep 3
echo ""

# 查看最新回复
echo "5. 查看最新回复..."
python3 message_sdk.py user1 read --limit 3
echo ""

# 停止监听器
echo "6. 停止监听器..."
kill $LISTENER_PID 2>/dev/null
echo "   监听器已停止"
echo ""

echo "============================================================"
echo "测试完成"
echo "============================================================"
