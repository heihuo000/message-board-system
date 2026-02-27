#!/usr/bin/env python3
"""
Agent Hub MCP 连接测试脚本
测试 iFlow、Qwen、Gemini、Claude 之间的通信
"""

import json
import os
import sys
from pathlib import Path

# Agent Hub 数据目录
HUB_DIR = Path.home() / ".agent-hub"
AGENTS_DIR = HUB_DIR / "agents"
MESSAGES_DIR = HUB_DIR / "messages"
FEATURES_DIR = HUB_DIR / "features"

def print_section(title):
    """打印分隔线"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def check_hub_structure():
    """检查 Agent Hub 目录结构"""
    print_section("1. 检查 Agent Hub 目录结构")

    dirs = {
        "agents": AGENTS_DIR,
        "messages": MESSAGES_DIR,
        "features": FEATURES_DIR
    }

    all_exist = True
    for name, path in dirs.items():
        if path.exists():
            files = list(path.glob("*.json"))
            print(f"✅ {name:12} - {len(files)} 个文件")
        else:
            print(f"❌ {name:12} - 目录不存在")
            all_exist = False

    return all_exist

def list_registered_agents():
    """列出已注册的 agents"""
    print_section("2. 已注册的 Agents")

    if not AGENTS_DIR.exists():
        print("暂无已注册的 agent")
        return []

    agents = []
    for agent_file in AGENTS_DIR.glob("*.json"):
        try:
            with open(agent_file, 'r') as f:
                agent_data = json.load(f)
                agent_id = agent_data.get('agentId', 'unknown')
                capabilities = agent_data.get('capabilities', [])
                agents.append(agent_id)
                print(f"✅ {agent_id:20} - 能力: {', '.join(capabilities[:3])}")
        except Exception as e:
            print(f"❌ {agent_file.name} - 读取失败: {e}")

    if not agents:
        print("暂无已注册的 agent")
        return []

    return agents

def list_messages():
    """列出消息历史"""
    print_section("3. 消息历史")

    if not MESSAGES_DIR.exists():
        print("暂无消息")
        return 0

    messages = list(MESSAGES_DIR.glob("*.json"))
    if not messages:
        print("暂无消息")
        return 0

    print(f"共 {len(messages)} 条消息")

    # 显示最近的 5 条消息
    sorted_messages = sorted(messages, key=lambda x: x.stat().st_mtime, reverse=True)
    for msg_file in sorted_messages[:5]:
        try:
            with open(msg_file, 'r') as f:
                msg_data = json.load(f)
                from_agent = msg_data.get('from', 'unknown')
                to_agent = msg_data.get('to', 'unknown')
                msg_type = msg_data.get('message', {}).get('type', 'unknown')
                print(f"  {from_agent:10} → {to_agent:10} ({msg_type})")
        except Exception as e:
            print(f"  ❌ {msg_file.name} - 读取失败")

    return len(messages)

def check_configs():
    """检查各 AI CLI 配置"""
    print_section("4. AI CLI 配置检查")

    configs = {
        "Claude Code": Path.home() / ".claude-code" / "config.json",
        "Qwen": Path.home() / ".qwen" / "settings.json",
        "Gemini": Path.home() / ".gemini" / "settings.json"
    }

    for name, config_path in configs.items():
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)

                mcp_servers = config.get('mcpServers', {})
                if 'agent-hub' in mcp_servers:
                    hub_config = mcp_servers['agent-hub']
                    agent_name = hub_config.get('env', {}).get('AGENT_NAME', 'unknown')
                    data_dir = hub_config.get('env', {}).get('AGENT_HUB_DATA_DIR', 'unknown')
                    print(f"✅ {name:15} - Agent: {agent_name}, Data: {data_dir}")
                else:
                    print(f"⚠️  {name:15} - 未配置 agent-hub")
            except Exception as e:
                print(f"❌ {name:15} - 配置读取失败: {e}")
        else:
            print(f"❌ {name:15} - 配置文件不存在")

def test_npx():
    """测试 npx 命令"""
    print_section("5. 测试 Agent Hub MCP 命令")

    import subprocess

    try:
        # 检查 npx 是否可用
        result = subprocess.run(
            ['npx', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"✅ npx 版本: {result.stdout.strip()}")

            # 测试 agent-hub-mcp 是否可以运行
            print("正在测试 agent-hub-mcp...")
            result = subprocess.run(
                ['npx', '-y', 'agent-hub-mcp@latest', '--version'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print(f"✅ agent-hub-mcp 可运行")
                return True
            else:
                print(f"❌ agent-hub-mcp 运行失败")
                return False
        else:
            print(f"❌ npx 不可用")
            return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "="*60)
    print("  Agent Hub MCP 连接测试")
    print("="*60)

    # 运行所有测试
    check_hub_structure()
    agents = list_registered_agents()
    msg_count = list_messages()
    check_configs()
    npx_ok = test_npx()

    # 总结
    print_section("测试总结")

    if not agents:
        print("⚠️  当前没有已注册的 agent")
        print("\n下一步操作:")
        print("1. 重启所有 AI CLI (claude, qwen, gemini)")
        print("2. 在每个 AI CLI 中运行: /hub:register")
        print("3. 运行: /hub:status 验证连接")
    else:
        print(f"✅ 已注册 {len(agents)} 个 agent: {', '.join(agents)}")

    if msg_count == 0:
        print("\n💡 测试消息发送:")
        print("1. 在 Claude Code 中: send_message({to: 'qwen', message: 'test'})")
        print("2. 在 Qwen 中: /hub:sync")
    else:
        print(f"✅ 已有 {msg_count} 条消息记录")

    if not npx_ok:
        print("\n❌ agent-hub-mcp 未能正常运行，请检查网络和依赖")
    else:
        print("\n✅ Agent Hub MCP 配置正确，可以开始使用")

if __name__ == "__main__":
    main()