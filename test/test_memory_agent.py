"""测试具备记忆功能的Agent."""

import asyncio
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai_chat', 'backend'))

from agents.memory_function_call_agent import MemoryFunctionCallAgent
from agents.memory import MemoryType, MemoryImportance
from llm.client import LLMClient
from config import LLMConfig
from tools.registry import ToolRegistry
from tools.calculator import CalculatorTool
from tools.time_tool import TimeTool
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
            print(f"\n[Assistant Start - {data.get('messageId')}]", flush=True)
        elif msg_type == "assistant_end":
            print(f"\n[Assistant End - {data.get('messageId')}]", flush=True)
        elif msg_type == "tool_call":
            print(f"\n[Tool Call: {data.get('toolName')}]", flush=True)


async def test_memory_agent():
    """测试记忆功能Agent"""
    
    print("=" * 80)
    print("测试：具备记忆功能的Function Call Agent")
    print("=" * 80)
    
    # 1. 初始化组件
    print("\n1️⃣ 初始化组件...")
    llm_config = LLMConfig()
    llm_client = LLMClient(llm_config)
    tool_registry = ToolRegistry()
    session_manager = SessionManager()
    
    # 注册工具
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
    
    print(f"✅ Agent已初始化: {agent.name}")
    print(f"   类型: {agent.agent_type}")
    print(f"   可用工具: {agent.get_available_tools()}")
    
    # 2. 测试会话1：建立初始记忆
    print("\n" + "=" * 80)
    print("2️⃣ 测试会话1：建立初始记忆")
    print("=" * 80)
    
    session_id = "test_session_1"
    ws1 = MockWebSocket()
    messages1 = []
    
    # 第一轮对话：介绍自己
    print("\n👤 用户: 你好！我叫张三，我是一名Python开发者，喜欢使用Django框架。")
    await agent.run(ws1, session_id, "你好！我叫张三，我是一名Python开发者，喜欢使用Django框架。", messages1)
    
    # 手动添加一条长期记忆
    agent.add_long_term_memory(
        session_id=session_id,
        content="用户名: 张三, 职业: Python开发者, 偏好框架: Django",
        importance=MemoryImportance.HIGH,
        tags=["用户信息", "偏好"]
    )
    
    print("\n\n✅ 已保存用户信息到长期记忆")
    
    # 查看当前记忆统计
    stats = agent.get_memory_statistics(session_id)
    print(f"\n📊 当前记忆统计: {stats}")
    
    # 3. 测试会话2：利用记忆进行对话
    print("\n" + "=" * 80)
    print("3️⃣ 测试会话2：利用记忆进行个性化对话")
    print("=" * 80)
    
    ws2 = MockWebSocket()
    
    # 第二轮对话：询问建议（应该能引用之前的记忆）
    print("\n👤 用户: 我想学习一个新的Web框架，你有什么推荐吗？")
    await agent.run(ws2, session_id, "我想学习一个新的Web框架，你有什么推荐吗？", messages1)
    
    print("\n\n✅ Agent应该能够记住用户是Python开发者，喜欢Django")
    
    # 4. 测试记忆检索
    print("\n" + "=" * 80)
    print("4️⃣ 测试记忆检索功能")
    print("=" * 80)
    
    memory_manager = agent._get_memory_manager(session_id)
    
    # 检索所有记忆
    all_memories = agent.get_all_memories(session_id)
    print(f"\n📚 总记忆数: {len(all_memories)}")
    
    # 按类型分类显示
    for mem_type in MemoryType:
        mems = memory_manager.get_memories_by_type(mem_type)
        if mems:
            print(f"\n{mem_type.value} ({len(mems)}条):")
            for mem in mems[:3]:  # 只显示前3条
                print(f"  - {mem.content[:80]}...")
    
    # 搜索关键词
    print("\n🔍 搜索关键词 'Python':")
    python_memories = memory_manager.search_memories("Python")
    for mem in python_memories[:3]:
        print(f"  - {mem.content[:80]}...")
    
    # 5. 测试重要记忆
    print("\n" + "=" * 80)
    print("5️⃣ 测试重要记忆获取")
    print("=" * 80)
    
    important_memories = memory_manager.get_important_memories(MemoryImportance.HIGH)
    print(f"\n⭐ 重要记忆 ({len(important_memories)}条):")
    for mem in important_memories:
        print(f"  - [{mem.importance.value}] {mem.content[:80]}...")
    
    # 6. 测试记忆导出
    print("\n" + "=" * 80)
    print("6️⃣ 测试记忆导出功能")
    print("=" * 80)
    
    exported = memory_manager.export_memories()
    print(f"\n💾 导出的记忆数据 (前200字符):")
    print(exported[:200] + "...")
    
    # 7. 最终统计
    print("\n" + "=" * 80)
    print("7️⃣ 最终记忆统计")
    print("=" * 80)
    
    final_stats = agent.get_memory_statistics(session_id)
    print(f"\n📊 最终统计:")
    print(f"   总记忆数: {final_stats['total']}")
    print(f"   按类型: {final_stats['by_type']}")
    print(f"   按重要性: {final_stats['by_importance']}")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成！")
    print("=" * 80)


async def test_memory_persistence():
    """测试记忆在多轮对话中的持久性"""
    
    print("\n" + "=" * 80)
    print("测试：记忆持久性验证")
    print("=" * 80)
    
    llm_config = LLMConfig()
    llm_client = LLMClient(llm_config)
    tool_registry = ToolRegistry()
    session_manager = SessionManager()
    
    tool_registry.register(CalculatorTool())
    
    agent = MemoryFunctionCallAgent(
        name="记忆测试助手",
        llm_client=llm_client,
        tool_registry=tool_registry,
        session_manager=session_manager
    )
    
    session_id = "persistence_test"
    ws = MockWebSocket()
    messages = []
    
    # 对话1：告诉Agent一个数字
    print("\n👤 用户: 请记住这个数字：42")
    await agent.run(ws, session_id, "请记住这个数字：42", messages)
    
    # 手动添加记忆
    agent.add_long_term_memory(
        session_id=session_id,
        content="重要数字: 42",
        importance=MemoryImportance.CRITICAL,
        tags=["数字", "用户指定"]
    )
    
    # 对话2：询问之前的数字
    print("\n\n👤 用户: 我刚才告诉你的那个数字是多少？")
    await agent.run(ws, session_id, "我刚才告诉你的那个数字是多少？", messages)
    
    print("\n\n✅ 持久性测试完成！Agent应该能记住数字42")


if __name__ == "__main__":
    print("\n🚀 开始测试具备记忆功能的Agent\n")
    
    # 运行基础测试
    asyncio.run(test_memory_agent())
    
    # 运行持久性测试
    asyncio.run(test_memory_persistence())
    
    print("\n✅ 所有测试完成！\n")
