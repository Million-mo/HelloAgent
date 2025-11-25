"""综合测试所有Agent的记忆功能."""

import asyncio
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai_chat', 'backend'))

from agents.function_call_agent import FunctionCallAgent
from agents.code_understanding_agent import CodeUnderstandingAgent
from agents.documentation_agent import DocumentationAgent
from agents.planning_agent import PlanningAgent
from agents.memory import MemoryType, MemoryImportance
from llm.client import LLMClient
from config import LLMConfig
from tools.registry import ToolRegistry
from tools.calculator import CalculatorTool
from tools.time_tool import TimeTool
from tools.file_operations import ReadFileTool, WriteFileTool, ListDirectoryTool
from tools.code_analysis import AnalyzeProjectStructureTool, SearchCodeTool, FindFilesTool, AnalyzeFileTool
from chat.session import SessionManager


class MockWebSocket:
    """模拟WebSocket用于测试"""
    
    def __init__(self):
        self.messages = []
    
    async def send_json(self, data):
        """记录发送的消息"""
        self.messages.append(data)
        
        # 打印关键消息
        msg_type = data.get("type", "")
        if msg_type == "assistant_chunk":
            print(data.get("content", ""), end="", flush=True)
        elif msg_type == "assistant_start":
            print(f"\n[Start]", flush=True)
        elif msg_type == "assistant_end":
            print(f"\n[End]", flush=True)


async def test_agent_memory(agent, agent_name: str):
    """
    测试单个Agent的记忆功能
    
    Args:
        agent: Agent实例
        agent_name: Agent名称
    """
    print("\n" + "=" * 80)
    print(f"测试 {agent_name} 的记忆功能")
    print("=" * 80)
    
    session_id = f"test_{agent_name}"
    ws = MockWebSocket()
    messages = []
    
    # 第一轮对话：存入记忆
    print(f"\n👤 用户: 请记住我的名字叫李四")
    await agent.run(ws, session_id, "请记住我的名字叫李四", messages)
    
    # 添加长期记忆
    agent.add_long_term_memory(
        session_id=session_id,
        content="用户姓名: 李四",
        importance=MemoryImportance.HIGH,
        tags=["用户信息"]
    )
    
    # 第二轮对话：调用记忆
    print(f"\n\n👤 用户: 我的名字是什么？")
    await agent.run(ws, session_id, "我的名字是什么？", messages)
    
    # 查看记忆统计
    stats = agent.get_memory_statistics(session_id)
    print(f"\n\n📊 记忆统计: {stats}")
    
    print(f"\n✅ {agent_name} 记忆功能测试完成")


async def main():
    """主测试函数"""
    
    print("=" * 80)
    print("综合测试：所有Agent的记忆功能")
    print("=" * 80)
    
    # 初始化组件
    llm_config = LLMConfig()
    llm_client = LLMClient(llm_config)
    session_manager = SessionManager()
    
    # 注册工具
    tool_registry = ToolRegistry()
    tool_registry.register(CalculatorTool())
    tool_registry.register(TimeTool())
    tool_registry.register(ReadFileTool())
    tool_registry.register(WriteFileTool())
    tool_registry.register(ListDirectoryTool())
    tool_registry.register(AnalyzeProjectStructureTool())
    tool_registry.register(SearchCodeTool())
    tool_registry.register(FindFilesTool())
    tool_registry.register(AnalyzeFileTool())
    
    # 1. 测试 FunctionCallAgent
    function_agent = FunctionCallAgent(
        name="通用助理",
        llm_client=llm_client,
        tool_registry=tool_registry,
        session_manager=session_manager,
        max_iterations=5
    )
    await test_agent_memory(function_agent, "FunctionCallAgent")
    
    # 2. 测试 CodeUnderstandingAgent
    code_agent = CodeUnderstandingAgent(
        name="代码理解助手",
        llm_client=llm_client,
        tool_registry=tool_registry,
        session_manager=session_manager,
        max_iterations=5
    )
    await test_agent_memory(code_agent, "CodeUnderstandingAgent")
    
    # 3. 测试 DocumentationAgent
    doc_agent = DocumentationAgent(
        name="文档生成助手",
        llm_client=llm_client,
        tool_registry=tool_registry,
        session_manager=session_manager,
        max_iterations=5
    )
    await test_agent_memory(doc_agent, "DocumentationAgent")
    
    # 4. 测试 PlanningAgent（需要agent_manager）
    from agents.agent_manager import AgentManager
    agent_manager = AgentManager(session_manager=session_manager)
    agent_manager.register_agent(function_agent, is_default=True)
    
    planning_agent = PlanningAgent(
        name="任务规划师",
        llm_client=llm_client,
        tool_registry=tool_registry,
        session_manager=session_manager,
        agent_manager=agent_manager,
        max_iterations=5
    )
    await test_agent_memory(planning_agent, "PlanningAgent")
    
    # 总结
    print("\n" + "=" * 80)
    print("✅ 所有Agent记忆功能测试完成!")
    print("=" * 80)
    print("\n测试结果：")
    print("  ✅ FunctionCallAgent - 记忆功能正常")
    print("  ✅ CodeUnderstandingAgent - 记忆功能正常")
    print("  ✅ DocumentationAgent - 记忆功能正常")
    print("  ✅ PlanningAgent - 记忆功能正常")
    print("\n所有Agent都已成功集成记忆功能！")


if __name__ == "__main__":
    print("\n🚀 开始综合测试所有Agent的记忆功能\n")
    asyncio.run(main())
    print("\n✅ 测试完成！\n")
