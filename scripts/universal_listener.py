#!/usr/bin/env python3
"""
通用消息监听脚本 - 适用于所有角色
使用方式：python3 universal_listener.py --client-id <角色名>
"""
from message_sdk import MessageBoardClient
import time
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

def setup_logging(log_file=None, log_level='info'):
    """配置日志"""
    log_levels = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR
    }
    level = log_levels.get(log_level.lower(), logging.INFO)
    
    if log_file:
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=log_file,
            filemode='a'
        )
    else:
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    return logging.getLogger(__name__)

def load_keywords(config_file=None):
    """加载关键词匹配规则"""
    keywords = {
        '你好': '你好！有什么可以帮助你的吗？',
        '在吗': '我在！请说。',
        '谢谢': '不客气！',
        '再见': '再见！',
        '测试': '收到测试消息！'
    }
    
    if config_file and Path(config_file).exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        keywords[key] = value
        except Exception as e:
            logging.warning(f'加载配置文件失败：{e}')
    
    return keywords

def match_reply(content, keywords):
    """关键词匹配回复"""
    for keyword, reply in keywords.items():
        if keyword in content:
            return reply
    return None

def generate_ai_reply(content, client_id):
    """调用 AI 生成回复"""
    try:
        # 使用 MCP 工具生成回复
        # 这里可以集成现有的 MCP 工具
        return f"（AI 回复）收到您的消息：{content}。我会尽快处理。"
    except Exception as e:
        return f"（AI 回复失败）{str(e)}"

def daemonize(pid_file):
    """后台运行 - 标准 daemon 实现"""
    # 第一次 fork
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)  # 退出父进程
    except OSError as e:
        sys.stderr.write(f'fork #1 failed: {e}\n')
        sys.exit(1)
    
    # 创建新会话
    os.setsid()
    
    # 第二次 fork
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)  # 退出父进程
    except OSError as e:
        sys.stderr.write(f'fork #2 failed: {e}\n')
        sys.exit(1)
    
    # 重定向标准输出
    sys.stdout = open('/dev/null', 'w')
    sys.stderr = open('/dev/null', 'w')
    sys.stdin = open('/dev/null', 'r')
    
    # 写入 PID 文件
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))

def main():
    parser = argparse.ArgumentParser(description='通用消息监听脚本')
    parser.add_argument('--client-id', required=True, help='客户端 ID（角色名）')
    parser.add_argument('--check-interval', type=int, default=3, help='检查间隔（秒）')
    parser.add_argument('--log', choices=['debug', 'info', 'warning', 'error'], help='日志级别')
    parser.add_argument('--log-file', default='logs/listener.log', help='日志文件路径')
    parser.add_argument('--daemon', action='store_true', help='后台运行模式')
    parser.add_argument('--pid-file', default='/tmp/universal_listener.pid', help='PID 文件路径')
    parser.add_argument('--quiet', action='store_true', help='静默模式')
    parser.add_argument('--config', help='关键词配置文件')
    parser.add_argument('--auto-reply', action='store_true', help='启用自动回复')
    parser.add_argument('--ai-reply', action='store_true', help='启用 AI 智能回复')
    args = parser.parse_args()

    log_file = args.log_file if args.log else None
    logger = setup_logging(log_file, args.log or 'info')
    
    if args.daemon:
        daemonize(args.pid_file)
        logger.info(f'以后台模式启动，PID 文件：{args.pid_file}')
    
    client = MessageBoardClient(args.client_id)
    logger.info(f'客户端 ID: {client.client_id}')
    
    keywords = load_keywords(args.config) if args.auto_reply else {}
    
    if not args.quiet:
        print('⏳ 开始监听消息...（按 Ctrl+C 停止）')
        print(f'  客户端 ID: {client.client_id}')
        print(f'  检查间隔：{args.check_interval} 秒')
        print(f'  开始时间：{datetime.now().strftime("%H:%M:%S")}')
        if args.auto_reply:
            print(f'  自动回复：已启用')
        print('=' * 60)
    
    logger.info('开始监听消息')

    try:
        while True:
            unread = client.read_unread()

            if unread:
                logger.info(f'收到 {len(unread)} 条新消息')
                
                if not args.quiet:
                    print(f'\n📬 收到 {len(unread)} 条新消息：')
                    print('-' * 60)

                for msg in unread:
                    time_str = datetime.fromtimestamp(msg['timestamp']).strftime('%H:%M:%S')
                    logger.info(f"来自 {msg['sender']}: {msg['content'][:50]}...")
                    
                    if not args.quiet:
                        print(f"  时间：{time_str}")
                        print(f"  发送者：{msg['sender']}")
                        print(f"  内容：{msg['content']}")
                        print(f"  消息 ID: {msg['id']}")
                        print('-' * 60)
                    
                    if args.auto_reply and keywords:
                        reply = match_reply(msg['content'], keywords)
                        if reply:
                            client.send(reply, reply_to=msg['id'])
                            logger.info(f'自动回复：{reply}')
                            if not args.quiet:
                                print(f'📤 已自动回复：{reply}')

                msg_ids = [msg['id'] for msg in unread]
                client.mark_read(msg_ids)
                logger.info(f'已标记 {len(msg_ids)} 条消息为已读')
                
                if not args.quiet:
                    print(f'✅ 已标记 {len(msg_ids)} 条消息为已读')
                    print()
                    print('📤 收到消息，监听结束。')
                return

            if not args.quiet:
                elapsed = datetime.now().strftime('%H:%M:%S')
                print(f'\r⏱️  监听中... {elapsed}', end='', flush=True)
            time.sleep(args.check_interval)

    except KeyboardInterrupt:
        if not args.quiet:
            print('\n\n🛑 监听已停止')
        logger.info('监听已停止')
        if args.daemon and os.path.exists(args.pid_file):
            os.remove(args.pid_file)
    except Exception as e:
        logger.error(f'错误：{e}')
        if not args.quiet:
            print(f'\n❌ 错误：{e}')

if __name__ == '__main__':
    main()
