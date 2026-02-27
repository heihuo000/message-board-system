#!/usr/bin/env python3
"""MCP Server 主程序"""
import sys
import asyncio
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, Resource
except ImportError:
    print("错误：需要安装 mcp 包", file=sys.stderr)
    print("请运行：pip install mcp", file=sys.stderr)
    sys.exit(1)

from src.mcp_server.tools import (
    send_message,
    read_messages,
    mark_read,
    get_status,
    register_client,
    delete_message,
    clear_old_messages
)
from src.mcp_server.resources import (
    get_unread_messages,
    get_all_messages,
    get_sent_messages,
    get_current_status,
    RESOURCE_TEMPLATES
)


async def create_server():
    """创建并运行 MCP Server"""
    server = Server("message-board")
    
    # ==================== 注册 Tools ====================
    
    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="send_message",
                description="发送消息到留言簿",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "消息内容"
                        },
                        "sender": {
                            "type": "string",
                            "description": "发送者 ID"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["normal", "urgent"],
                            "description": "优先级",
                            "default": "normal"
                        },
                        "reply_to": {
                            "type": "string",
                            "description": "回复的消息 ID"
                        }
                    },
                    "required": ["content", "sender"]
                }
            ),
            Tool(
                name="read_messages",
                description="读取留言簿消息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "unread_only": {
                            "type": "boolean",
                            "description": "只读取未读消息",
                            "default": False
                        },
                        "limit": {
                            "type": "integer",
                            "description": "限制返回数量",
                            "default": 100
                        },
                        "since": {
                            "type": "integer",
                            "description": "起始时间戳",
                            "default": 0
                        },
                        "sender": {
                            "type": "string",
                            "description": "发送者过滤"
                        }
                    }
                }
            ),
            Tool(
                name="mark_read",
                description="标记消息已读",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "消息 ID 列表"
                        }
                    },
                    "required": ["message_ids"]
                }
            ),
            Tool(
                name="get_status",
                description="获取系统状态",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="register_client",
                description="注册客户端",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "client_id": {
                            "type": "string",
                            "description": "客户端 ID"
                        },
                        "name": {
                            "type": "string",
                            "description": "客户端名称"
                        }
                    },
                    "required": ["client_id", "name"]
                }
            ),
            Tool(
                name="delete_message",
                description="删除消息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "消息 ID"
                        }
                    },
                    "required": ["message_id"]
                }
            ),
            Tool(
                name="clear_old_messages",
                description="清理旧消息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "older_than_seconds": {
                            "type": "integer",
                            "description": "清理早于指定秒数的消息",
                            "default": 2592000
                        }
                    }
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "send_message":
            result = send_message(
                content=arguments.get("content"),
                sender=arguments.get("sender", "unknown"),
                priority=arguments.get("priority", "normal"),
                reply_to=arguments.get("reply_to")
            )
        elif name == "read_messages":
            result = read_messages(
                unread_only=arguments.get("unread_only", False),
                limit=arguments.get("limit", 100),
                since=arguments.get("since", 0),
                sender=arguments.get("sender")
            )
        elif name == "mark_read":
            result = mark_read(arguments.get("message_ids", []))
        elif name == "get_status":
            result = get_status()
        elif name == "register_client":
            result = register_client(
                client_id=arguments.get("client_id"),
                name=arguments.get("name")
            )
        elif name == "delete_message":
            result = delete_message(arguments.get("message_id"))
        elif name == "clear_old_messages":
            result = clear_old_messages(arguments.get("older_than_seconds", 2592000))
        else:
            return {"error": f"未知工具：{name}"}
        
        return [result]
    
    # ==================== 注册 Resources ====================
    
    @server.list_resources()
    async def list_resources():
        return [
            Resource(
                uri=uri,
                name=info["name"],
                description=info["description"],
                mimeType=info["mime_type"]
            )
            for uri, info in RESOURCE_TEMPLATES.items()
            if "{" not in uri  # 排除模板资源
        ]
    
    @server.read_resource()
    async def read_resource(uri: str):
        # 处理模板资源
        if uri.startswith("messages://sent/"):
            client_id = uri.replace("messages://sent/", "")
            result = get_sent_messages(client_id)
        elif uri == "messages://unread":
            result = get_unread_messages()
        elif uri == "messages://all":
            result = get_all_messages()
        elif uri == "status://current":
            result = get_current_status()
        else:
            return f"未知资源：{uri}"
        
        return result.get("text", str(result))
    
    # ==================== 运行 Server ====================
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """入口点"""
    print("Starting Message Board MCP Server...", file=sys.stderr)
    asyncio.run(create_server())


if __name__ == "__main__":
    main()
