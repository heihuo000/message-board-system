"""AI 触发器 - 触发 AI CLI 自动回复"""
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class TriggerResult:
    """触发结果"""
    success: bool
    method: str
    message: str


class AITrigger:
    """AI 触发器"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.method = self.config.get("method", "tmux")
        self.tmux_config = self.config.get("tmux", {})
        self.hook_config = self.config.get("hook", {})
    
    def trigger(self, message_content: str, sender: str = "unknown") -> TriggerResult:
        """
        触发 AI 回复
        
        Args:
            message_content: 消息内容
            sender: 发送者
        
        Returns:
            TriggerResult
        """
        if self.method == "tmux":
            return self._trigger_tmux(message_content, sender)
        elif self.method == "hook":
            return self._trigger_hook(message_content, sender)
        elif self.method == "command":
            return self._trigger_command(message_content, sender)
        else:
            return TriggerResult(
                success=False,
                method=self.method,
                message=f"未知的触发方式：{self.method}"
            )
    
    def _trigger_tmux(self, message_content: str, sender: str) -> TriggerResult:
        """通过 tmux 触发"""
        session = self.tmux_config.get("session", "ai-session")
        pane = self.tmux_config.get("pane", "0")
        command_template = self.tmux_config.get(
            "command",
            "claude --prompt '你有新消息来自 {sender}: {content}'"
        )
        
        # 检查 tmux 是否可用
        if not shutil.which("tmux"):
            return TriggerResult(
                success=False,
                method="tmux",
                message="tmux 未安装"
            )
        
        # 检查会话是否存在
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", session],
                capture_output=True,
                timeout=2
            )
            if result.returncode != 0:
                return TriggerResult(
                    success=False,
                    method="tmux",
                    message=f"tmux 会话不存在：{session}"
                )
        except subprocess.TimeoutExpired:
            return TriggerResult(
                success=False,
                method="tmux",
                message="检查 tmux 会话超时"
            )
        
        # 构建命令
        command = command_template.format(
            sender=sender,
            content=message_content[:100]  # 限制长度
        )
        
        # 发送命令到 tmux
        try:
            subprocess.run(
                ["tmux", "send-keys", "-t", f"{session}:{pane}", command, "Enter"],
                capture_output=True,
                timeout=5
            )
            return TriggerResult(
                success=True,
                method="tmux",
                message=f"已发送到 tmux 会话 {session}:{pane}"
            )
        except subprocess.TimeoutExpired:
            return TriggerResult(
                success=False,
                method="tmux",
                message="发送命令超时"
            )
        except Exception as e:
            return TriggerResult(
                success=False,
                method="tmux",
                message=f"错误：{e}"
            )
    
    def _trigger_hook(self, message_content: str, sender: str) -> TriggerResult:
        """通过 hook 脚本触发"""
        hook_path = self.hook_config.get("path")
        if not hook_path:
            return TriggerResult(
                success=False,
                method="hook",
                message="未配置 hook 路径"
            )
        
        hook_file = Path(hook_path).expanduser()
        if not hook_file.exists():
            return TriggerResult(
                success=False,
                method="hook",
                message=f"hook 脚本不存在：{hook_path}"
            )
        
        # 设置环境变量
        env = {
            "MESSAGE_CONTENT": message_content,
            "MESSAGE_SENDER": sender,
            "TRIGGER_TYPE": "new_message"
        }
        
        try:
            result = subprocess.run(
                ["bash", str(hook_file)],
                capture_output=True,
                text=True,
                timeout=30,
                env={**subprocess.os.environ, **env}
            )
            
            if result.returncode == 0:
                return TriggerResult(
                    success=True,
                    method="hook",
                    message=f"hook 执行成功：{result.stdout[:200]}"
                )
            else:
                return TriggerResult(
                    success=False,
                    method="hook",
                    message=f"hook 执行失败：{result.stderr[:200]}"
                )
        except subprocess.TimeoutExpired:
            return TriggerResult(
                success=False,
                method="hook",
                message="hook 执行超时"
            )
        except Exception as e:
            return TriggerResult(
                success=False,
                method="hook",
                message=f"错误：{e}"
            )
    
    def _trigger_command(self, message_content: str, sender: str) -> TriggerResult:
        """通过直接执行命令触发"""
        command = self.config.get("command", "")
        if not command:
            return TriggerResult(
                success=False,
                method="command",
                message="未配置命令"
            )
        
        # 替换变量
        command = command.format(
            sender=sender,
            content=message_content[:100]
        )
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return TriggerResult(
                    success=True,
                    method="command",
                    message=f"命令执行成功：{result.stdout[:200]}"
                )
            else:
                return TriggerResult(
                    success=False,
                    method="command",
                    message=f"命令执行失败：{result.stderr[:200]}"
                )
        except subprocess.TimeoutExpired:
            return TriggerResult(
                success=False,
                method="command",
                message="命令执行超时"
            )
        except Exception as e:
            return TriggerResult(
                success=False,
                method="command",
                message=f"错误：{e}"
            )
    
    def notify(self, title: str, message: str) -> bool:
        """发送系统通知"""
        try:
            # 尝试使用 notify-send (Linux)
            if shutil.which("notify-send"):
                subprocess.run(
                    ["notify-send", title, message],
                    capture_output=True,
                    timeout=2
                )
                return True
            
            # 尝试使用 osascript (macOS)
            if shutil.which("osascript"):
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    timeout=2
                )
                return True
        except Exception:
            pass
        
        return False
