#!/usr/bin/env python3
"""
在线状态监控 - 显示谁在线、谁在监听
自动检测客户端在线状态和监听状态

使用方法:
    python3 online_status.py
"""
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))
from message_sdk import MessageBoardClient


class OnlineStatusMonitor:
    """在线状态监控器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化监控器
        
        Args:
            db_path: 数据库路径
        """
        if db_path:
            self.client = MessageBoardClient("system_monitor", db_path)
        else:
            self.client = MessageBoardClient("system_monitor")
        
        self.status_file = Path("~/.message_board/online_status.json").expanduser()
        self.heartbeat_interval = 30  # 心跳间隔 30 秒
        self.timeout_threshold = 120  # 超时阈值 2 分钟
    
    def ensure_status_file(self):
        """确保状态文件存在"""
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.status_file.exists():
            # 直接写入初始数据，避免递归
            initial_data = {
                "clients": {},
                "last_update": int(time.time())
            }
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)
    
    def load_status(self) -> Dict:
        """加载状态"""
        self.ensure_status_file()
        
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                "clients": {},
                "last_update": int(time.time())
            }
    
    def save_status(self, status: Dict):
        """保存状态"""
        self.ensure_status_file()
        
        status["last_update"] = int(time.time())
        
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    
    def register_client(self, client_id: str, status: str = "online"):
        """
        注册客户端
        
        Args:
            client_id: 客户端 ID
            status: 状态 (online/listening/offline)
        """
        data = self.load_status()
        
        data["clients"][client_id] = {
            "status": status,
            "last_seen": int(time.time()),
            "message_count": 0
        }
        
        self.save_status(data)
        print(f"✅ {client_id} 已注册，状态：{status}")
    
    def update_client_status(self, client_id: str, status: str):
        """
        更新客户端状态
        
        Args:
            client_id: 客户端 ID
            status: 新状态
        """
        data = self.load_status()
        
        if client_id in data["clients"]:
            data["clients"][client_id]["status"] = status
            data["clients"][client_id]["last_seen"] = int(time.time())
            self.save_status(data)
    
    def set_listening(self, client_id: str):
        """设置客户端为监听状态"""
        self.update_client_status(client_id, "listening")
    
    def set_offline(self, client_id: str):
        """设置客户端为离线状态"""
        self.update_client_status(client_id, "offline")
    
    def heartbeat(self, client_id: str):
        """
        心跳更新
        
        Args:
            client_id: 客户端 ID
        """
        data = self.load_status()
        
        if client_id in data["clients"]:
            data["clients"][client_id]["last_seen"] = int(time.time())
            # 如果离线，改为在线
            if data["clients"][client_id]["status"] == "offline":
                data["clients"][client_id]["status"] = "online"
        else:
            # 新客户端
            data["clients"][client_id] = {
                "status": "online",
                "last_seen": int(time.time()),
                "message_count": 0
            }
        
        self.save_status(data)
    
    def check_timeouts(self):
        """检查超时的客户端"""
        data = self.load_status()
        current_time = int(time.time())
        changed = False
        
        for client_id, info in data["clients"].items():
            last_seen = current_time - info["last_seen"]
            
            # 超过阈值，标记为离线
            if last_seen > self.timeout_threshold and info["status"] != "offline":
                info["status"] = "offline"
                changed = True
                print(f"⚠️ {client_id} 超时，已标记为离线")
        
        if changed:
            self.save_status(data)
    
    def get_online_count(self) -> int:
        """获取在线数量"""
        data = self.load_status()
        current_time = int(time.time())
        
        count = 0
        for info in data["clients"].values():
            if current_time - info["last_seen"] < self.timeout_threshold:
                count += 1
        
        return count
    
    def get_listening_count(self) -> int:
        """获取监听中的数量"""
        data = self.load_status()
        
        count = 0
        for info in data["clients"].values():
            if info["status"] == "listening":
                count += 1
        
        return count
    
    def get_status_display(self) -> str:
        """获取状态显示"""
        self.check_timeouts()
        data = self.load_status()
        
        online = []
        listening = []
        offline = []
        
        current_time = int(time.time())
        
        for client_id, info in data["clients"].items():
            last_seen = current_time - info["last_seen"]
            
            if last_seen > self.timeout_threshold:
                offline.append(client_id)
            elif info["status"] == "listening":
                listening.append(client_id)
            else:
                online.append(client_id)
        
        # 格式化显示
        lines = []
        lines.append("=" * 60)
        lines.append("📊 在线状态监控")
        lines.append("=" * 60)
        lines.append(f"总客户端：{len(data['clients'])}")
        lines.append(f"🟢 在线：{len(online)}")
        lines.append(f"👂 监听中：{len(listening)}")
        lines.append(f"🔴 离线：{len(offline)}")
        lines.append("=" * 60)
        
        if listening:
            lines.append("\n👂 监听中:")
            for client_id in listening:
                lines.append(f"   • {client_id}")
        
        if online:
            lines.append("\n🟢 在线（未监听）:")
            for client_id in online:
                lines.append(f"   • {client_id}")
        
        if offline:
            lines.append("\n🔴 离线:")
            for client_id in offline:
                lines.append(f"   • {client_id}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def display(self):
        """显示状态"""
        print(self.get_status_display())
    
    def run_monitor(self, interval: int = 10):
        """
        运行监控
        
        Args:
            interval: 刷新间隔（秒）
        """
        print(f"🚀 启动状态监控（刷新间隔：{interval}秒）")
        print("按 Ctrl+C 停止")
        
        try:
            while True:
                self.display()
                self.check_timeouts()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n⚠️  监控停止")


# ==================== 便捷函数 ====================

def show_status():
    """显示当前状态"""
    monitor = OnlineStatusMonitor()
    monitor.display()


def register(client_id: str, status: str = "online"):
    """注册客户端"""
    monitor = OnlineStatusMonitor()
    monitor.register_client(client_id, status)


def set_listening(client_id: str):
    """设置为监听状态"""
    monitor = OnlineStatusMonitor()
    monitor.set_listening(client_id)


def set_offline(client_id: str):
    """设置为离线状态"""
    monitor = OnlineStatusMonitor()
    monitor.set_offline(client_id)


def heartbeat(client_id: str):
    """发送心跳"""
    monitor = OnlineStatusMonitor()
    monitor.heartbeat(client_id)


# ==================== 命令行接口 ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="在线状态监控",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 显示状态
    python3 online_status.py show
    
    # 注册客户端
    python3 online_status.py register my_ai
    
    # 设置监听状态
    python3 online_status.py listening my_ai
    
    # 持续监控
    python3 online_status.py monitor
        """
    )
    
    parser.add_argument(
        "command",
        choices=["show", "register", "listening", "offline", "heartbeat", "monitor"],
        help="命令"
    )
    
    parser.add_argument(
        "client_id",
        nargs="?",
        help="客户端 ID"
    )
    
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=10,
        help="监控刷新间隔（秒）"
    )
    
    args = parser.parse_args()
    
    if args.command == "show":
        show_status()
    
    elif args.command == "register":
        if not args.client_id:
            print("❌ 需要客户端 ID")
            sys.exit(1)
        register(args.client_id)
    
    elif args.command == "listening":
        if not args.client_id:
            print("❌ 需要客户端 ID")
            sys.exit(1)
        set_listening(args.client_id)
    
    elif args.command == "offline":
        if not args.client_id:
            print("❌ 需要客户端 ID")
            sys.exit(1)
        set_offline(args.client_id)
    
    elif args.command == "heartbeat":
        if not args.client_id:
            print("❌ 需要客户端 ID")
            sys.exit(1)
        heartbeat(args.client_id)
    
    elif args.command == "monitor":
        monitor = OnlineStatusMonitor()
        monitor.run_monitor(interval=args.interval)
