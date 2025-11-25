"""
代码分析工具演示脚本
独立测试每个代码分析工具的功能
"""

import asyncio
import sys
import os

# 添加backend目录到path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai_chat', 'backend'))

from tools.code_analysis import (
    AnalyzeProjectStructureTool,
    SearchCodeTool,
    FindFilesTool,
    AnalyzeFileTool
)


async def demo_analyze_project_structure():
    """演示项目结构分析工具"""
    print("=" * 70)
    print("【演示1】分析项目结构工具 (analyze_project_structure)")
    print("=" * 70)
    
    # 创建工具实例，基础目录设为项目根目录
    project_root = os.path.join(os.path.dirname(__file__), '..')
    tool = AnalyzeProjectStructureTool(base_dir=project_root)
    
    print(f"\n工具名称: {tool.name}")
    print(f"工具描述: {tool.description}")
    print(f"\n正在分析项目结构...")
    
    # 执行分析
    result = await tool.execute(directory_path="ai_chat/backend/agents", max_depth=3)
    print("\n结果:")
    print(result)


async def demo_search_code():
    """演示代码搜索工具"""
    print("\n\n" + "=" * 70)
    print("【演示2】代码搜索工具 (search_code)")
    print("=" * 70)
    
    project_root = os.path.join(os.path.dirname(__file__), '..')
    tool = SearchCodeTool(base_dir=project_root)
    
    print(f"\n工具名称: {tool.name}")
    print(f"工具描述: {tool.description}")
    
    # 测试1: 搜索类定义
    print(f"\n测试1: 搜索所有Agent类定义")
    result = await tool.execute(
        pattern="class.*Agent",
        directory_path="ai_chat/backend/agents",
        case_sensitive=False,
        max_results=10
    )
    print(result)
    
    # 测试2: 搜索函数调用
    print(f"\n测试2: 搜索 'async def' 函数定义")
    result = await tool.execute(
        pattern="async def",
        directory_path="ai_chat/backend",
        max_results=15
    )
    print(result)


async def demo_find_files():
    """演示文件查找工具"""
    print("\n\n" + "=" * 70)
    print("【演示3】文件查找工具 (find_files)")
    print("=" * 70)
    
    project_root = os.path.join(os.path.dirname(__file__), '..')
    tool = FindFilesTool(base_dir=project_root)
    
    print(f"\n工具名称: {tool.name}")
    print(f"工具描述: {tool.description}")
    
    # 测试1: 查找所有Python文件
    print(f"\n测试1: 查找所有Agent相关的Python文件")
    result = await tool.execute(
        name_pattern="*agent*.py",
        directory_path="ai_chat/backend"
    )
    print(result)
    
    # 测试2: 查找配置文件
    print(f"\n测试2: 查找所有配置文件")
    result = await tool.execute(
        name_pattern="config.*",
        directory_path="."
    )
    print(result)


async def demo_analyze_file():
    """演示文件分析工具"""
    print("\n\n" + "=" * 70)
    print("【演示4】文件分析工具 (analyze_file)")
    print("=" * 70)
    
    project_root = os.path.join(os.path.dirname(__file__), '..')
    tool = AnalyzeFileTool(base_dir=project_root)
    
    print(f"\n工具名称: {tool.name}")
    print(f"工具描述: {tool.description}")
    
    # 测试1: 分析Python文件
    print(f"\n测试1: 分析 base_agent.py")
    result = await tool.execute(
        file_path="ai_chat/backend/agents/base_agent.py"
    )
    print(result)
    
    # 测试2: 分析另一个文件
    print(f"\n测试2: 分析 function_call_agent.py")
    result = await tool.execute(
        file_path="ai_chat/backend/agents/function_call_agent.py"
    )
    print(result)


async def main():
    """主函数：运行所有演示"""
    print("\n" + "=" * 70)
    print(" " * 20 + "代码分析工具演示")
    print("=" * 70)
    
    try:
        await demo_analyze_project_structure()
        await demo_search_code()
        await demo_find_files()
        await demo_analyze_file()
        
        print("\n\n" + "=" * 70)
        print(" " * 25 + "演示完成！")
        print("=" * 70)
        print("\n提示: 这些工具都可以通过代码理解Agent自动调用")
        print("      运行 'python test_code_understanding_agent.py' 查看完整示例")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
