"""测试PlanningAgent的功能."""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai_chat', 'backend'))

from agents.planning_agent import PlanningAgent, Task, TaskStatus, TaskPriority, TaskManager


def test_task_model():
    """测试任务数据模型"""
    print("\n=== 测试任务数据模型 ===")
    
    task = Task(
        id="task1",
        title="需求分析",
        description="分析用户需求，明确目标",
        priority=TaskPriority.HIGH,
        dependencies=["task0"],
        assigned_agent="分析专家"
    )
    
    print(f"任务ID: {task.id}")
    print(f"任务标题: {task.title}")
    print(f"任务状态: {task.status.value}")
    print(f"任务优先级: {task.priority.value}")
    print(f"依赖任务: {task.dependencies}")
    print(f"分配Agent: {task.assigned_agent}")
    
    task_dict = task.to_dict()
    print(f"任务字典: {json.dumps(task_dict, ensure_ascii=False, indent=2)}")
    
    print("✓ 任务数据模型测试通过")


def test_task_manager():
    """测试任务管理器"""
    print("\n=== 测试任务管理器 ===")
    
    manager = TaskManager()
    
    # 创建任务
    task1 = Task(
        id="task1",
        title="需求分析",
        description="分析需求",
        priority=TaskPriority.HIGH
    )
    
    task2 = Task(
        id="task2",
        title="方案设计",
        description="设计解决方案",
        priority=TaskPriority.HIGH,
        dependencies=["task1"]
    )
    
    task3 = Task(
        id="task3",
        title="代码实现",
        description="实现功能",
        priority=TaskPriority.MEDIUM,
        dependencies=["task2"]
    )
    
    task4 = Task(
        id="task4",
        title="文档编写",
        description="编写文档",
        priority=TaskPriority.LOW,
        dependencies=["task1"]
    )
    
    # 添加任务
    for task in [task1, task2, task3, task4]:
        manager.add_task(task)
    
    print(f"总任务数: {len(manager.get_all_tasks())}")
    
    # 测试获取可执行任务
    executable = manager.get_executable_tasks()
    print(f"\n当前可执行任务: {len(executable)}")
    for task in executable:
        print(f"  - {task.title} (优先级: {task.priority.value})")
    
    # 完成task1
    manager.update_task_status("task1", TaskStatus.COMPLETED)
    print(f"\n完成task1后可执行任务:")
    executable = manager.get_executable_tasks()
    for task in executable:
        print(f"  - {task.title} (依赖: {task.dependencies})")
    
    # 完成task2
    manager.update_task_status("task2", TaskStatus.COMPLETED)
    print(f"\n完成task2后可执行任务:")
    executable = manager.get_executable_tasks()
    for task in executable:
        print(f"  - {task.title}")
    
    # 测试进度
    progress = manager.get_progress()
    print(f"\n任务进度:")
    print(f"  总计: {progress['total']}")
    print(f"  已完成: {progress['completed']}")
    print(f"  进行中: {progress['in_progress']}")
    print(f"  待处理: {progress['pending']}")
    print(f"  失败: {progress['failed']}")
    print(f"  进度: {progress['progress']}%")
    
    print("✓ 任务管理器测试通过")


def test_task_priority_sorting():
    """测试任务优先级排序"""
    print("\n=== 测试任务优先级排序 ===")
    
    manager = TaskManager()
    
    tasks = [
        Task(id="t1", title="低优先级", description="低", priority=TaskPriority.LOW),
        Task(id="t2", title="关键任务", description="关键", priority=TaskPriority.CRITICAL),
        Task(id="t3", title="中等任务", description="中等", priority=TaskPriority.MEDIUM),
        Task(id="t4", title="高优先级", description="高", priority=TaskPriority.HIGH),
    ]
    
    for task in tasks:
        manager.add_task(task)
    
    executable = manager.get_executable_tasks()
    print("任务执行顺序（按优先级）:")
    for i, task in enumerate(executable, 1):
        print(f"  {i}. {task.title} - {task.priority.value}")
    
    # 验证顺序
    expected_order = ["关键任务", "高优先级", "中等任务", "低优先级"]
    actual_order = [task.title for task in executable]
    
    if actual_order == expected_order:
        print("✓ 优先级排序正确")
    else:
        print(f"✗ 优先级排序错误: 期望 {expected_order}, 实际 {actual_order}")


def test_dependency_chain():
    """测试依赖链"""
    print("\n=== 测试任务依赖链 ===")
    
    manager = TaskManager()
    
    # 创建依赖链: A -> B -> C -> D
    tasks = [
        Task(id="A", title="任务A", description="第一步", dependencies=[]),
        Task(id="B", title="任务B", description="第二步", dependencies=["A"]),
        Task(id="C", title="任务C", description="第三步", dependencies=["B"]),
        Task(id="D", title="任务D", description="第四步", dependencies=["C"]),
    ]
    
    for task in tasks:
        manager.add_task(task)
    
    print("依赖链: A -> B -> C -> D")
    
    # 模拟执行流程
    steps = []
    while True:
        executable = manager.get_executable_tasks()
        if not executable:
            break
        
        task = executable[0]
        steps.append(task.id)
        print(f"执行: {task.id} - {task.title}")
        manager.update_task_status(task.id, TaskStatus.COMPLETED)
    
    expected_steps = ["A", "B", "C", "D"]
    if steps == expected_steps:
        print(f"✓ 依赖链执行顺序正确: {' -> '.join(steps)}")
    else:
        print(f"✗ 执行顺序错误: 期望 {expected_steps}, 实际 {steps}")


def print_example_task_plan():
    """打印示例任务计划"""
    print("\n=== 示例任务计划 ===")
    
    example_plan = {
        "tasks": [
            {
                "id": "task1",
                "title": "需求分析",
                "description": "分析用户需求，明确系统目标和功能要求",
                "priority": "high",
                "dependencies": [],
                "assigned_agent": "分析专家"
            },
            {
                "id": "task2",
                "title": "技术选型",
                "description": "根据需求选择合适的技术栈和框架",
                "priority": "high",
                "dependencies": ["task1"],
                "assigned_agent": "编程助手"
            },
            {
                "id": "task3",
                "title": "架构设计",
                "description": "设计系统整体架构和模块划分",
                "priority": "high",
                "dependencies": ["task2"],
                "assigned_agent": "编程助手"
            },
            {
                "id": "task4",
                "title": "核心功能实现",
                "description": "实现系统核心功能模块",
                "priority": "medium",
                "dependencies": ["task3"],
                "assigned_agent": "编程助手"
            },
            {
                "id": "task5",
                "title": "测试验证",
                "description": "编写测试用例并验证功能",
                "priority": "medium",
                "dependencies": ["task4"],
                "assigned_agent": "编程助手"
            },
            {
                "id": "task6",
                "title": "文档编写",
                "description": "编写使用文档和API文档",
                "priority": "low",
                "dependencies": ["task4"],
                "assigned_agent": "通用助理"
            }
        ]
    }
    
    print(json.dumps(example_plan, ensure_ascii=False, indent=2))
    
    print("\n任务依赖关系图:")
    print("  需求分析")
    print("      ↓")
    print("  技术选型")
    print("      ↓")
    print("  架构设计")
    print("      ↓")
    print("  核心功能实现")
    print("    ↓     ↓")
    print("  测试验证  文档编写")


def main():
    """主测试函数"""
    print("开始测试PlanningAgent组件...\n")
    
    # 运行测试
    test_task_model()
    test_task_manager()
    test_task_priority_sorting()
    test_dependency_chain()
    print_example_task_plan()
    
    print("\n" + "="*60)
    print("所有测试完成!")
    print("="*60)
    
    print("\n使用说明:")
    print("1. 启动服务: python run_server.py")
    print("2. 连接WebSocket: ws://localhost:8000/ws/session_id")
    print("3. 发送消息:")
    print('''
{
    "type": "message",
    "mode": "agent",
    "agent_name": "任务规划师",
    "content": "帮我规划一个Web应用开发项目的任务"
}
''')
    print("\n4. 查看Agent信息: GET http://localhost:8000/agent/info")


if __name__ == "__main__":
    main()
