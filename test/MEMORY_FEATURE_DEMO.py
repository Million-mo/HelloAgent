"""记忆功能使用示例和演示."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai_chat', 'backend'))

from agents.memory_function_call_agent import MemoryFunctionCallAgent
from agents.function_call_agent import FunctionCallAgent
from agents.memory import MemoryType, MemoryImportance
from llm.client import LLMClient
from config import LLMConfig
from tools.registry import ToolRegistry
from tools.calculator import CalculatorTool
from tools.time_tool import TimeTool
from chat.session import SessionManager


class MockWebSocket:
    """模拟WebSocket"""
    async def send_json(self, data):
        msg_type = data.get("type", "")
        if msg_type == "assistant_chunk":
            print(data.get("content", ""), end="", flush=True)
        elif msg_type == "assistant_end":
            print()


async def demo_memory_features():
    """演示记忆功能的各种特性"""
    
    print("=" * 80)
    print("记忆功能演示")
    print("=" * 80)
    
    # 初始化
    llm_config = LLMConfig()
    llm_client = LLMClient(llm_config)
    tool_registry = ToolRegistry()
    session_manager = SessionManager()
    
    tool_registry.register(CalculatorTool())
    tool_registry.register(TimeTool())
    
    # 创建具备记忆功能的Agent
    agent = MemoryFunctionCallAgent(
        name="记忆助手",
        llm_client=llm_client,
        tool_registry=tool_registry,
        session_manager=session_manager,
        max_iterations=5
    )
    
    session_id = "demo_session"
    ws = MockWebSocket()
    messages = []
    
    # 演示1: 记住用户信息
    print("\n" + "-" * 80)
    print("演示1: 记住用户基本信息")
    print("-" * 80)
    print("\n👤 用户: 我叫王五，是一名前端开发者，擅长React和Vue")
    await agent.run(ws, session_id, "我叫王五，是一名前端开发者，擅长React和Vue", messages)
    
    # 手动添加重要记忆
    agent.add_long_term_memory(
        session_id=session_id,
        content="姓名: 王五 | 职业: 前端开发者 | 技能: React, Vue",
        importance=MemoryImportance.CRITICAL,
        tags=["用户信息", "技能"]
    )
    
    # 演示2: 利用记忆提供个性化建议
    print("\n" + "-" * 80)
    print("演示2: 基于记忆提供个性化建议")
    print("-" * 80)
    print("\n👤 用户: 推荐一些适合我学习的新技术")
    await agent.run(ws, session_id, "推荐一些适合我学习的新技术", messages)
    
    # 演示3: 记忆检索
    print("\n" + "-" * 80)
    print("演示3: 记忆检索和查询")
    print("-" * 80)
    
    # 查看所有记忆
    all_memories = agent.get_all_memories(session_id)
    print(f"\n📚 当前共有 {len(all_memories)} 条记忆\n")
    
    # 按类型查看
    for mem_type in MemoryType:
        mems = agent.get_memories_by_type(session_id, mem_type)
        if mems:
            print(f"\n{mem_type.value.upper()} ({len(mems)}条):")
            for mem in mems[:2]:
                print(f"  • {mem.content[:60]}...")
    
    # 搜索关键词
    print("\n🔍 搜索'React'相关记忆:")
    react_mems = agent.search_memories(session_id, "React")
    for mem in react_mems[:3]:
        print(f"  • {mem.content[:60]}...")
    
    # 演示4: 导出和导入记忆
    print("\n" + "-" * 80)
    print("演示4: 记忆导出和导入")
    print("-" * 80)
    
    # 导出记忆
    exported = agent.export_memories(session_id)
    print(f"\n💾 已导出记忆数据 ({len(exported)} 字符)")
    
    # 统计信息
    stats = agent.get_memory_statistics(session_id)
    print(f"\n📊 记忆统计:")
    print(f"  总数: {stats['total']}")
    print(f"  短期记忆: {stats['by_type']['short_term']}")
    print(f"  长期记忆: {stats['by_type']['long_term']}")
    print(f"  工作记忆: {stats['by_type']['working']}")
    
    print("\n" + "=" * 80)
    print("✅ 记忆功能演示完成!")
    print("=" * 80)


async def compare_with_without_memory():
    """对比有无记忆功能的差异"""
    
    print("\n\n" + "=" * 80)
    print("对比：有记忆 vs 无记忆")
    print("=" * 80)
    
    # 初始化
    llm_config = LLMConfig()
    llm_client = LLMClient(llm_config)
    tool_registry = ToolRegistry()
    session_manager = SessionManager()
    
    tool_registry.register(CalculatorTool())
    
    # 无记忆Agent
    normal_agent = FunctionCallAgent(
        name="普通助手",
        llm_client=llm_client,
        tool_registry=tool_registry,
        session_manager=session_manager,
        max_iterations=3
    )
    
    # 有记忆Agent
    memory_agent = MemoryFunctionCallAgent(
        name="记忆助手",
        llm_client=llm_client,
        tool_registry=tool_registry,
        session_manager=session_manager,
        max_iterations=3
    )
    
    ws = MockWebSocket()
    
    # 测试普通Agent
    print("\n" + "-" * 80)
    print("普通Agent (无记忆)")
    print("-" * 80)
    
    session1 = "normal_session"
    messages1 = []
    
    print("\n👤 第1轮: 我喜欢的数字是88")
    await normal_agent.run(ws, session1, "我喜欢的数字是88", messages1)
    
    print("\n👤 第2轮: 我喜欢的数字是多少？")
    await normal_agent.run(ws, session1, "我喜欢的数字是多少？", messages1)
    
    # 测试记忆Agent
    print("\n" + "-" * 80)
    print("记忆Agent (有记忆)")
    print("-" * 80)
    
    session2 = "memory_session"
    messages2 = []
    
    print("\n👤 第1轮: 我喜欢的数字是88")
    await memory_agent.run(ws, session2, "我喜欢的数字是88", messages2)
    
    # 添加长期记忆
    memory_agent.add_long_term_memory(
        session_id=session2,
        content="用户喜欢的数字: 88",
        importance=MemoryImportance.HIGH,
        tags=["用户偏好"]
    )
    
    print("\n👤 第2轮: 我喜欢的数字是多少？")
    await memory_agent.run(ws, session2, "我喜欢的数字是多少？", messages2)
    
    # 统计
    mem_stats = memory_agent.get_memory_statistics(session2)
    print(f"\n📊 记忆Agent统计: 共{mem_stats['total']}条记忆")
    
    print("\n" + "=" * 80)
    print("对比结论：记忆Agent能够记住并引用之前的信息！")
    print("=" * 80)


if __name__ == "__main__":
    print("\n🎯 记忆功能完整演示\n")
    
    # 运行完整演示
    asyncio.run(demo_memory_features())
    
    # 运行对比测试
    asyncio.run(compare_with_without_memory())
    
    print("\n✅ 演示完成!\n")
