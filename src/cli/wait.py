#!/usr/bin/env python3
"""监听新消息守护进程"""
import sys
import time
import signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.database import Database
from rich.console import Console
from rich.panel import Panel

console = Console()

running = True

def signal_handler(sig, frame):
    """处理中断信号"""
    global running
    console.print("\n[yellow]正在退出监听...[/yellow]")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def wait_for_messages(check_interval: int = 3, client_id: str = None):
    """持续监听新消息"""
    db = Database()

    # 获取当前最大 ID，用于检测新消息
    messages = db.get_messages(limit=1)
    last_id = messages[0].id if messages else None

    console.print(Panel.fit(
        "[bold green]📮 消息监听中[/bold green]\n\n"
        f"检查间隔：{check_interval} 秒\n"
        f"客户端 ID: {client_id or '默认'}\n\n"
        "[dim]按 Ctrl+C 停止监听[/dim]"
    ))

    while running:
        try:
            # 获取最新消息
            messages = db.get_messages(limit=10)

            if messages:
                current_id = messages[0].id

                # 检测新消息
                if current_id != last_id:
                    # 找到新消息
                    new_messages = []
                    for m in messages:
                        if m.id != last_id:
                            new_messages.append(m)
                        else:
                            break

                    if new_messages:
                        console.print("\n")
                        for m in reversed(new_messages):
                            # 标记已读
                            db.mark_read([m.id])

                            # 显示消息
                            priority_style = "red bold" if m.priority == "urgent" else "green"
                            priority_icon = "🔴" if m.priority == "urgent" else "📩"

                            console.print(Panel(
                                f"[{priority_style}]{priority_icon} 优先级：{m.priority}[/{priority_style}]\n"
                                f"[cyan]发送者:[/cyan] {m.sender}\n"
                                f"[cyan]时间:[/cyan] {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(m.timestamp))}\n"
                                f"\n[magenta]📝 内容:[/magenta]\n{m.content}",
                                title=f"新消息 (ID: {m.id[:8]}...)",
                                border_style="bright_green"
                            ))

                        last_id = current_id
                else:
                    # 无新消息，显示等待状态
                    console.print(f"[dim]等待中... 上次检查：{time.strftime('%H:%M:%S')}[/dim]", end="\r")

            time.sleep(check_interval)

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]错误：{e}[/red]")
            time.sleep(check_interval)

    console.print("\n[green]✓ 监听已停止[/green]")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="监听新消息")
    parser.add_argument("--interval", "-i", type=int, default=3, help="检查间隔（秒）")
    parser.add_argument("--client", "-c", type=str, default="default", help="客户端 ID")

    args = parser.parse_args()
    wait_for_messages(check_interval=args.interval, client_id=args.client)
