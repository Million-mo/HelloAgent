"""DeepWiki 独立运行脚本 - 可选的独立启动方式."""

import sys
import os
import asyncio

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../ai_chat/backend'))

from workflow import DeepWikiWorkflow
from llm.client import LLMClient
from chat.session import SessionManager


async def main():
    """主函数 - 演示如何使用 DeepWiki Workflow."""
    
    print("=" * 60)
    print("DeepWiki - 深度知识探索系统")
    print("=" * 60)
    
    # 初始化工作流
    workflow = DeepWikiWorkflow()
    
    # 打印工作流信息
    info = workflow.get_info()
    print(f"\n工作流: {info['workflow_name']}")
    print(f"描述: {info['description']}")
    print(f"\nAgent 信息:")
    print(f"  名称: {info['agent']['name']}")
    print(f"  类型: {info['agent']['type']}")
    print(f"  最大迭代: {info['agent']['max_iterations']}")
    print(f"\n已注册工具 ({info['tool_count']}):")
    for tool in info['tools']:
        print(f"  - {tool}")
    
    print("\n" + "=" * 60)
    print("提示: DeepWiki 已准备就绪!")
    print("你可以将此工作流集成到现有的 Web 应用中使用。")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
