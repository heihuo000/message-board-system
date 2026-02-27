#!/usr/bin/env python3
"""
任务分配示例
演示如何使用任务管理功能进行AI代理之间的任务分配
"""
from message_sdk import MessageBoardClient

# ==================== 任务分配者 ====================
def assign_task():
    """分配任务给其他AI代理"""
    client = MessageBoardClient("iflow")
    
    print("=== 任务分配示例 ===\n")
    
    # 创建任务
    task = client.create_task(
        title="分析DNF PVF文件结构",
        description="分析DNF私服PVF文件，提取装备和技能的基本信息",
        assigned_to="dnf-pvf-analyse",
        created_by="iflow",
        priority="high"
    )
    
    print(f"✓ 任务已创建")
    print(f"  任务ID: {task['task_id']}")
    print(f"  标题: {task['title']}")
    print(f"  分配给: {task['assigned_to']}")
    print(f"  状态: {task['status']}")
    
    # 发送通知消息
    client.send(
        content=f"新任务: {task['title']} (ID: {task['task_id']})",
        sender="iflow"
    )
    
    print(f"\n✓ 已发送通知消息给 dnf-pvf-analyse")
    
    return task['task_id']

# ==================== 任务执行者 ====================
def execute_tasks():
    """执行分配给自己的任务"""
    client = MessageBoardClient("dnf-pvf-analyse")
    
    print("\n=== 任务执行示例 ===\n")
    
    # 查询待处理任务
    tasks = client.get_tasks(assigned_to="dnf-pvf-analyse", status="pending")
    
    if not tasks:
        print("没有待处理任务")
        return
    
    print(f"找到 {len(tasks)} 个待处理任务\n")
    
    for task in tasks:
        print(f"任务: {task['title']}")
        print(f"描述: {task['description']}")
        print(f"优先级: {task['priority']}")
        print(f"创建者: {task['created_by']}")
        
        # 更新任务状态为运行中
        client.update_task(task['id'], status="running")
        print(f"\n→ 开始执行任务...")
        
        # 执行任务（这里模拟任务执行）
        result = "已完成PVF文件分析，发现50个装备文件和30个技能文件"
        
        # 更新任务状态为已完成
        client.update_task(
            task['id'],
            status="completed",
            result=result
        )
        
        print(f"→ 任务执行完成")
        print(f"  结果: {result}\n")
        
        # 发送完成通知
        client.send(
            content=f"任务完成: {task['title']} (ID: {task['id']})",
            sender="dnf-pvf-analyse"
        )

# ==================== 查询任务状态 ====================
def check_task_status():
    """查询任务状态"""
    client = MessageBoardClient("iflow")
    
    print("\n=== 任务状态查询 ===\n")
    
    # 查询所有任务
    tasks = client.get_tasks(limit=10)
    
    print(f"总任务数: {len(tasks)}\n")
    
    for task in tasks:
        status_icon = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌"
        }.get(task['status'], "❓")
        
        print(f"{status_icon} {task['title']}")
        print(f"   ID: {task['id']}")
        print(f"   状态: {task['status']}")
        print(f"   分配给: {task['assigned_to']}")
        print(f"   优先级: {task['priority']}")
        if task['result']:
            print(f"   结果: {task['result']}")
        print()

# ==================== 完整工作流程示例 ====================
def workflow_example():
    """完整的工作流程示例"""
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         AI代理任务分配系统 - 完整工作流程示例              ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    
    # 步骤1: 分配任务
    print("【步骤1】iflow 分配任务给 dnf-pvf-analyse")
    task_id = assign_task()
    
    # 步骤2: 执行任务
    print("\n【步骤2】dnf-pvf-analyse 执行任务")
    execute_tasks()
    
    # 步骤3: 查询状态
    print("\n【步骤3】iflow 查询任务状态")
    check_task_status()
    
    print("✓ 工作流程完成！")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "assign":
            assign_task()
        elif command == "execute":
            execute_tasks()
        elif command == "check":
            check_task_status()
        elif command == "workflow":
            workflow_example()
        else:
            print("用法: python3 task_example.py [assign|execute|check|workflow]")
    else:
        workflow_example()