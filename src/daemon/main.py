#!/usr/bin/env python3
"""Watch Daemon 主程序 - 监听新消息并自动触发 AI 回复"""
import sys
import time
import signal
import argparse
from pathlib import Path
from typing import Optional

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.daemon.watcher import FileWatcher
from src.daemon.processor import MessageProcessor
from src.daemon.trigger import AITrigger
from src.database import Database


class WatchDaemon:
    """Watch Daemon 主类"""
    
    def __init__(self, client_id: str, config: dict = None):
        self.client_id = client_id
        self.config = config or {}
        self.db_path = self.config.get("database", {}).get(
            "path", "~/.message_board/board.db"
        )
        
        # 初始化组件
        self.watcher = FileWatcher(self.db_path)
        self.processor = MessageProcessor(self.client_id, self.db_path)
        self.trigger = AITrigger(self.config.get("trigger", {}))
        
        # 状态
        self._running = False
        self._trigger_count = 0
    
    def on_file_modify(self, src_path: str):
        """文件修改回调"""
        print(f"[Daemon] 检测到文件变化：{src_path}")
        
        # 获取新消息
        new_messages = self.processor.get_new_messages()
        
        if new_messages:
            print(f"[Daemon] 发现 {len(new_messages)} 条新消息")
            
            for msg in new_messages:
                print(f"  - [{msg.sender}] {msg.content[:50]}...")
                
                # 触发 AI 回复
                result = self.trigger.trigger(msg.content, msg.sender)
                
                if result.success:
                    self._trigger_count += 1
                    print(f"  ✓ 触发成功 ({result.method}): {result.message[:50]}")
                else:
                    print(f"  ✗ 触发失败 ({result.method}): {result.message[:50]}")
                
                # 发送系统通知
                self.trigger.notify(
                    "新消息",
                    f"来自 {msg.sender}: {msg.content[:50]}"
                )
        else:
            print("[Daemon] 没有新消息")
    
    def start(self):
        """启动 Daemon"""
        print(f"[Daemon] 启动中...")
        print(f"  客户端 ID: {self.client_id}")
        print(f"  数据库：{self.db_path}")
        print(f"  触发方式：{self.config.get('trigger', {}).get('method', 'tmux')}")
        
        # 注册回调
        self.watcher.on_modify(self.on_file_modify)
        
        # 启动监听
        self.watcher.start()
        self._running = True
        
        print(f"[Daemon] 运行中 (按 Ctrl+C 停止)")
    
    def stop(self):
        """停止 Daemon"""
        print("\n[Daemon] 停止中...")
        self.watcher.stop()
        self._running = False
        print(f"[Daemon] 已停止，共触发 {self._trigger_count} 次")
    
    def run_forever(self):
        """运行主循环"""
        self.start()
        
        # 设置信号处理
        def signal_handler(sig, frame):
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()


def load_config() -> dict:
    """加载配置文件"""
    config_path = Path("~/.message_board/config.yaml").expanduser()
    
    if config_path.exists():
        try:
            import yaml
            return yaml.safe_load(config_path.read_text()) or {}
        except ImportError:
            pass
    
    return {}


def main():
    """入口点"""
    parser = argparse.ArgumentParser(description="Message Board Watch Daemon")
    parser.add_argument(
        "--client-id", "-c",
        help="客户端 ID",
        default=None
    )
    parser.add_argument(
        "--foreground", "-f",
        action="store_true",
        help="前台运行"
    )
    parser.add_argument(
        "--pid-file",
        help="PID 文件路径",
        default="~/.message_board/daemon.pid"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    # 获取客户端 ID
    client_id = args.client_id or config.get("client", {}).get("id", "default")
    
    # 创建 Daemon
    daemon = WatchDaemon(client_id, config)

    # 写入 PID 文件
    import os
    pid_file = Path(args.pid_file).expanduser()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))
    
    try:
        if args.foreground:
            # 前台运行
            daemon.run_forever()
        else:
            # 后台运行
            import os
            pid = os.fork()
            if pid > 0:
                print(f"[Daemon] 已启动 (PID: {pid})")
                sys.exit(0)
            
            # 子进程
            os.setsid()
            os.umask(0)
            
            # 重定向标准输出
            sys.stdout = open("/dev/null", "w")
            sys.stderr = open("/dev/null", "w")
            
            daemon.run_forever()
    finally:
        # 清理 PID 文件
        if pid_file.exists():
            pid_file.unlink()


if __name__ == "__main__":
    main()
