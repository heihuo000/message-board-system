"""CLI 命令实现"""
import sys
import time
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.database import Database
from src.models import Message, Client

console = Console()

# 全局数据库实例
db: Optional[Database] = None


def get_db() -> Database:
    """获取数据库实例"""
    global db
    if db is None:
        db = Database()
    return db


def get_client_id() -> str:
    """获取当前客户端 ID"""
    config_path = Path("~/.message_board/config.yaml").expanduser()
    if config_path.exists():
        import yaml
        config = yaml.safe_load(config_path.read_text())
        return config.get("client", {}).get("id", "unknown")
    return "default"


app = typer.Typer(help="Message Board CLI - AI CLI 跨终端通信工具")


@app.command("send")
def send_message(
    content: str = typer.Argument(..., help="消息内容"),
    priority: str = typer.Option("normal", "--priority", "-p", help="优先级：normal, urgent"),
    reply_to: Optional[str] = typer.Option(None, "--reply-to", "-r", help="回复的消息 ID"),
):
    """发送消息"""
    db = get_db()
    client_id = get_client_id()
    
    message = Message(
        sender=client_id,
        content=content,
        priority=priority,
        reply_to=reply_to
    )
    
    message_id = db.add_message(message)
    console.print(f"[green]✓[/green] 消息已发送 (ID: [cyan]{message_id}[/cyan])")
    
    if priority == "urgent":
        console.print("[yellow]⚠ 优先级：紧急[/yellow]")


@app.command("read")
def read_messages(
    unread_only: bool = typer.Option(False, "--unread", "-u", help="只读取未读消息"),
    limit: int = typer.Option(10, "--limit", "-l", help="限制返回数量"),
    since: Optional[str] = typer.Option(None, "--since", "-s", help="起始时间 (如：1 hour ago)"),
    as_json: bool = typer.Option(False, "--json", "-j", help="JSON 格式输出"),
    plain: bool = typer.Option(False, "--plain", help="纯文本输出（用于脚本）"),
):
    """读取消息"""
    db = get_db()
    
    # 解析 since 参数
    since_ts = 0
    if since:
        from dateutil import parser
        try:
            since_ts = int(parser.parse(since).timestamp())
        except Exception:
            console.print(f"[red]✗[/red] 无法解析时间：{since}")
            raise typer.Exit(1)
    
    messages = db.get_messages(unread_only=unread_only, limit=limit, since=since_ts)
    
    if not messages:
        if plain:
            return
        console.print("[yellow]没有消息[/yellow]")
        return
    
    # 反转顺序，按时间正序显示
    messages.reverse()
    
    if as_json:
        output = [m.to_dict() for m in messages]
        console.print(JSON.from_data(output))
    elif plain:
        for m in messages:
            console.print(f"[{m.sender}] {m.content}")
    else:
        table = Table(title="消息列表", show_header=True, header_style="bold magenta")
        table.add_column("状态", style="dim", width=4)
        table.add_column("发送者", style="cyan")
        table.add_column("内容", style="white")
        table.add_column("时间", style="green")
        table.add_column("优先级", width=8)
        
        for m in messages:
            status = "📭" if m.read else "📬"
            priority_style = "red bold" if m.priority == "urgent" else "dim"
            time_str = time.strftime("%m-%d %H:%M", time.localtime(m.timestamp))
            
            table.add_row(
                status,
                m.sender,
                m.content[:50] + "..." if len(m.content) > 50 else m.content,
                time_str,
                m.priority
            )
        
        console.print(table)
    
    # 自动标记已读（仅当读取未读消息时）
    if unread_only and messages:
        message_ids = [m.id for m in messages]
        db.mark_read(message_ids)


@app.command("mark-read")
def mark_read(
    message_ids: List[str] = typer.Argument(..., help="消息 ID 列表"),
    all_messages: bool = typer.Option(False, "--all", "-a", help="标记所有消息已读"),
):
    """标记消息已读"""
    db = get_db()
    
    if all_messages:
        count = db.mark_all_read()
        console.print(f"[green]✓[/green] 已标记 {count} 条消息为已读")
    else:
        count = db.mark_read(message_ids)
        console.print(f"[green]✓[/green] 已标记 {count} 条消息为已读")


@app.command("list")
def list_messages(
    limit: int = typer.Option(20, "--limit", "-l", help="限制返回数量"),
    as_json: bool = typer.Option(False, "--json", "-j", help="JSON 格式输出"),
):
    """列出所有消息"""
    db = get_db()
    messages = db.get_messages(limit=limit)
    
    if not messages:
        console.print("[yellow]没有消息[/yellow]")
        return
    
    if as_json:
        output = [m.to_dict() for m in messages]
        console.print(JSON.from_data(output))
    else:
        table = Table(title=f"消息列表 (最近 {len(messages)} 条)", show_header=True)
        table.add_column("状态", width=4)
        table.add_column("发送者", style="cyan")
        table.add_column("内容")
        table.add_column("时间", style="green")
        
        for m in reversed(messages):
            status = "📭" if m.read else "📬"
            time_str = time.strftime("%m-%d %H:%M", time.localtime(m.timestamp))
            table.add_row(
                status,
                m.sender,
                m.content[:40] + "..." if len(m.content) > 40 else m.content,
                time_str
            )
        
        console.print(table)


@app.command("status")
def show_status():
    """显示系统状态"""
    db = get_db()
    stats = db.get_stats()
    clients = db.get_all_clients()
    
    console.print(Panel.fit(
        "[bold]Message Board 状态[/bold]\n\n"
        f"📬 未读消息：[red]{stats['unread_messages']}[/red]\n"
        f"📭 总消息数：{stats['total_messages']}\n"
        f"🕐 最新消息：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats['latest_message_time'])) if stats['latest_message_time'] else '无'}\n"
        f"👥 注册客户端：{len(clients)}"
    ))
    
    if clients:
        table = Table(title="注册客户端", show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("名称")
        table.add_column("最后活跃")
        
        for c in clients:
            last_seen = time.strftime("%Y-%m-%d %H:%M", time.localtime(c.last_seen))
            table.add_row(c.id, c.name, last_seen)
        
        console.print(table)


@app.command("config")
def config_command(
    key: Optional[str] = typer.Argument(None, help="配置键"),
    value: Optional[str] = typer.Argument(None, help="配置值"),
):
    """配置管理"""
    config_path = Path("~/.message_board/config.yaml").expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 读取现有配置
    config = {}
    if config_path.exists():
        import yaml
        config = yaml.safe_load(config_path.read_text()) or {}
    
    if key is None:
        # 显示所有配置
        import yaml
        console.print(yaml.dump(config, default_flow_style=False))
    elif value is None:
        # 显示单个配置
        keys = key.split(".")
        val = config
        for k in keys:
            val = val.get(k, {}) if isinstance(val, dict) else None
        console.print(f"{key} = {val}")
    else:
        # 设置配置
        import yaml
        keys = key.split(".")
        d = config
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        
        config_path.write_text(yaml.dump(config, default_flow_style=False))
        console.print(f"[green]✓[/green] 配置已更新：{key} = {value}")


@app.command("delete")
def delete_message(
    message_id: str = typer.Argument(..., help="消息 ID"),
):
    """删除消息"""
    db = get_db()
    if db.delete_message(message_id):
        console.print(f"[green]✓[/green] 消息已删除：{message_id}")
    else:
        console.print(f"[red]✗[/red] 消息不存在：{message_id}")


@app.command("clear")
def clear_messages(
    older_than_days: int = typer.Option(30, "--older-than", "-d", help="清理早于指定天数的消息"),
):
    """清理旧消息"""
    db = get_db()
    cutoff = int(time.time()) - (older_than_days * 24 * 60 * 60)
    count = db.clear_old_messages(cutoff)
    console.print(f"[green]✓[/green] 已清理 {count} 条早于 {older_than_days} 天的消息")


def main():
    """CLI 入口点"""
    app()


if __name__ == "__main__":
    main()
