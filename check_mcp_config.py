#!/usr/bin/env python3
"""
MCP 配置检查工具 - 验证两边 AI 的 MCP 配置是否正确
"""
import json
from pathlib import Path
import sys


def check_json_file(path: str, name: str) -> bool:
    """检查 JSON 配置文件"""
    file_path = Path(path).expanduser()
    
    if not file_path.exists():
        print(f"❌ {name} 配置文件不存在：{file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查 MCP 配置
        if 'mcpServers' in data:
            mcp_config = data['mcpServers']
            
            if 'message-board' in mcp_config:
                mb_config = mcp_config['message-board']
                print(f"✅ {name} MCP 配置正确")
                print(f"   类型：{mb_config.get('type', 'unknown')}")
                print(f"   命令：{mb_config.get('command', 'unknown')}")
                print(f"   参数：{' '.join(mb_config.get('args', []))}")
                return True
            else:
                print(f"⚠️ {name} 没有配置 message-board MCP 服务器")
                print(f"   已配置的 MCP 服务器：{list(mcp_config.keys())}")
                return False
        else:
            print(f"⚠️ {name} 没有 mcpServers 配置")
            return False
    
    except json.JSONDecodeError as e:
        print(f"❌ {name} 配置文件解析失败：{e}")
        return False


def check_sdk_installation() -> bool:
    """检查 SDK 是否可用"""
    try:
        from message_sdk import MessageBoardClient
        print("✅ Message Board SDK 已安装")
        return True
    except ImportError:
        print("❌ Message Board SDK 未安装")
        print("   请运行：pip install -r requirements.txt")
        return False


def check_database() -> bool:
    """检查数据库是否存在"""
    db_path = Path("~/.message_board/board.db").expanduser()
    
    if db_path.exists():
        print(f"✅ 数据库存在：{db_path}")
        return True
    else:
        print(f"⚠️ 数据库不存在：{db_path}")
        print("   首次运行时会自动创建")
        return True


def check_state_files() -> bool:
    """检查状态文件"""
    state_dir = Path("~/.message_board").expanduser()
    
    if not state_dir.exists():
        print(f"⚠️ 状态目录不存在：{state_dir}")
        print("   会在首次运行时创建")
        return True
    
    state_files = list(state_dir.glob("*_state.json"))
    
    if state_files:
        print(f"✅ 发现 {len(state_files)} 个状态文件:")
        for sf in state_files:
            print(f"   - {sf.name}")
    else:
        print(f"ℹ️ 暂无状态文件（首次对话时会创建）")
    
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("🔍 MCP 配置检查工具")
    print("=" * 60)
    print()
    
    checks = [
        ("SDK 安装", check_sdk_installation),
        ("数据库", check_database),
        ("iFlow MCP 配置", lambda: check_json_file("~/.iflow/settings.json", "iFlow")),
        ("Qwen MCP 配置", lambda: check_json_file("~/.qwen/settings.json", "Qwen")),
        ("Claude Code MCP 配置", lambda: check_json_file("~/.claude-code/config.json", "Claude Code")),
        ("状态文件", check_state_files),
    ]
    
    results = []
    
    for name, check_func in checks:
        print(f"\n检查：{name}")
        print("-" * 60)
        result = check_func()
        results.append((name, result))
        print()
    
    # 汇总结果
    print("=" * 60)
    print("📊 检查结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print()
    print(f"通过：{passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有检查通过！可以开始对话了")
        print("\n使用示例:")
        print("  # 终端 1 - AI_A 先发言")
        print("  python3 ai_dialogue.py ai_a ai_b --first")
        print()
        print("  # 终端 2 - AI_B 等待对方先发言")
        print("  python3 ai_dialogue.py ai_b ai_a --wait")
        return 0
    else:
        print("\n⚠️ 部分检查未通过，请先修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())
