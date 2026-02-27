#!/usr/bin/env python3
"""
Session ID 生成助手
用于AI代理的多实例会话管理
"""
import os
import sys
from pathlib import Path


def generate_session_id(agent_id: str) -> str:
    """
    生成session_id（序号命名）
    
    Args:
        agent_id: 代理ID（iflow、qwen、dnf-pvf-analyse、pvf-analyzer）
    
    Returns:
        session_id（如 iflow1、iflow2、iflow3）
    """
    # 会话文件路径
    session_file = Path("~/.message_board/sessions.json").expanduser()
    session_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 读取现有会话
    import json
    sessions = {}
    if session_file.exists():
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                sessions = json.load(f)
        except:
            sessions = {}
    
    # 获取该代理的现有实例
    agent_sessions = sessions.get(agent_id, [])
    
    # 生成新的序号
    next_number = len(agent_sessions) + 1
    session_id = f"{agent_id}{next_number}"
    
    # 记录新会话
    if agent_id not in sessions:
        sessions[agent_id] = []
    sessions[agent_id].append({
        "session_id": session_id,
        "timestamp": int(__import__('time').time())
    })
    
    # 保存
    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, indent=2)
    
    return session_id


def get_existing_sessions(agent_id: str) -> list:
    """
    获取代理的所有现有会话
    
    Args:
        agent_id: 代理ID
    
    Returns:
        session_id列表
    """
    session_file = Path("~/.message_board/sessions.json").expanduser()
    
    if not session_file.exists():
        return []
    
    import json
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            sessions = json.load(f)
        return [s['session_id'] for s in sessions.get(agent_id, [])]
    except:
        return []


def clear_sessions(agent_id: str = None):
    """
    清理会话记录
    
    Args:
        agent_id: 如果指定，只清除该代理的会话；否则清除所有
    """
    session_file = Path("~/.message_board/sessions.json").expanduser()
    
    if not session_file.exists():
        return
    
    import json
    with open(session_file, 'r', encoding='utf-8') as f:
        sessions = json.load(f)
    
    if agent_id:
        sessions.pop(agent_id, None)
    else:
        sessions = {}
    
    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, indent=2)


def setup_environment(agent_id: str) -> str:
    """
    设置环境变量并返回session_id
    
    Args:
        agent_id: 代理ID
    
    Returns:
        session_id
    """
    session_id = generate_session_id(agent_id)
    os.environ['AGENT_SESSION_ID'] = session_id
    os.environ['AGENT_ID'] = agent_id
    return session_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 session_helper.py <agent_id> [command]")
        print("")
        print("命令:")
        print("  generate  - 生成session_id（默认）")
        print("  list      - 列出现有会话")
        print("  clear     - 清除会话记录")
        print("  setup     - 设置环境变量")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else "generate"
    
    if command == "generate":
        session_id = generate_session_id(agent_id)
        print(f"Session ID: {session_id}")
        print(f"export AGENT_SESSION_ID={session_id}")
        print(f"export AGENT_ID={agent_id}")
    
    elif command == "list":
        sessions = get_existing_sessions(agent_id)
        print(f"现有会话 ({agent_id}):")
        for s in sessions:
            print(f"  - {s}")
        if not sessions:
            print("  无")
    
    elif command == "clear":
        clear_sessions(agent_id)
        print(f"已清除 {agent_id} 的会话记录")
    
    elif command == "setup":
        session_id = setup_environment(agent_id)
        print(f"Session ID: {session_id}")
        print(f"环境变量已设置:")
        print(f"  AGENT_SESSION_ID={session_id}")
        print(f"  AGENT_ID={agent_id}")
    
    else:
        print(f"未知命令: {command}")
        sys.exit(1)