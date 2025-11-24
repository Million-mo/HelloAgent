"""
多Agent系统使用示例

展示如何使用多Agent系统进行不同类型的任务处理
"""

import asyncio
import json
from websockets import connect


async def example_usage():
    """示例：使用不同的Agent处理不同任务"""
    
    # WebSocket连接地址
    uri = "ws://localhost:8000/ws/example_session"
    
    async with connect(uri) as websocket:
        
        # ========== 示例1: 使用默认Agent（通用助理） ==========
        print("=" * 50)
        print("示例1: 使用默认Agent处理通用任务")
        print("=" * 50)
        
        message1 = {
            "type": "message",
            "content": "今天北京的天气怎么样？",
            "mode": "agent"  # 使用Agent管理器
        }
        await websocket.send(json.dumps(message1))
        
        # 接收响应
        async for response in websocket:
            data = json.loads(response)
            if data["type"] == "assistant_chunk":
                print(data["content"], end="", flush=True)
            elif data["type"] == "assistant_end":
                print("\n")
                break
        
        await asyncio.sleep(1)
        
        # ========== 示例2: 指定使用SimpleAgent ==========
        print("=" * 50)
        print("示例2: 使用SimpleAgent进行纯对话")
        print("=" * 50)
        
        message2 = {
            "type": "message",
            "content": "请用一句话介绍自己",
            "mode": "agent",
            "agent_name": "简单对话"  # 指定Agent
        }
        await websocket.send(json.dumps(message2))
        
        async for response in websocket:
            data = json.loads(response)
            if data["type"] == "assistant_chunk":
                print(data["content"], end="", flush=True)
            elif data["type"] == "assistant_end":
                print("\n")
                break
        
        await asyncio.sleep(1)
        
        # ========== 示例3: 使用AnalysisAgent进行深度分析 ==========
        print("=" * 50)
        print("示例3: 使用AnalysisAgent分析问题")
        print("=" * 50)
        
        message3 = {
            "type": "message",
            "content": "分析一下AI技术对未来教育的影响",
            "mode": "agent",
            "agent_name": "分析专家"
        }
        await websocket.send(json.dumps(message3))
        
        async for response in websocket:
            data = json.loads(response)
            if data["type"] == "assistant_chunk":
                print(data["content"], end="", flush=True)
            elif data["type"] == "assistant_end":
                print("\n")
                break
        
        await asyncio.sleep(1)
        
        # ========== 示例4: 使用CodeAgent编写代码 ==========
        print("=" * 50)
        print("示例4: 使用CodeAgent编写代码")
        print("=" * 50)
        
        message4 = {
            "type": "message",
            "content": "帮我写一个Python快速排序函数",
            "mode": "agent",
            "agent_name": "编程助手"
        }
        await websocket.send(json.dumps(message4))
        
        async for response in websocket:
            data = json.loads(response)
            if data["type"] == "assistant_chunk":
                print(data["content"], end="", flush=True)
            elif data["type"] == "tool_call":
                print(f"\n[工具调用: {data['toolName']}]")
            elif data["type"] == "assistant_end":
                print("\n")
                break


async def example_agent_switching():
    """示例：动态切换Agent"""
    import httpx
    
    session_id = "test_session_123"
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # 1. 获取所有Agent信息
        print("=" * 50)
        print("获取所有Agent信息")
        print("=" * 50)
        
        response = await client.get(f"{base_url}/agent/info")
        agents = response.json()
        
        for agent in agents:
            print(f"- {agent['name']} ({agent['type']})")
            print(f"  默认: {agent['is_default']}")
            print(f"  工具: {', '.join(agent['available_tools'][:3])}...")
            print()
        
        # 2. 切换到不同的Agent
        print("=" * 50)
        print("切换Agent")
        print("=" * 50)
        
        # 切换到分析专家
        response = await client.post(
            f"{base_url}/agent/switch/{session_id}",
            params={"agent_name": "分析专家"}
        )
        result = response.json()
        print(f"切换结果: {result['message']}")
        print()
        
        # 切换到编程助手
        response = await client.post(
            f"{base_url}/agent/switch/{session_id}",
            params={"agent_name": "编程助手"}
        )
        result = response.json()
        print(f"切换结果: {result['message']}")
        print()
        
        # 3. 获取系统统计
        print("=" * 50)
        print("系统统计")
        print("=" * 50)
        
        response = await client.get(f"{base_url}/agent/stats")
        stats = response.json()
        
        for key, value in stats.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    print("多Agent系统使用示例\n")
    
    # 运行WebSocket示例
    print("=" * 50)
    print("WebSocket交互示例")
    print("=" * 50)
    asyncio.run(example_usage())
    
    print("\n\n")
    
    # 运行Agent切换示例
    print("=" * 50)
    print("Agent切换示例")
    print("=" * 50)
    asyncio.run(example_agent_switching())
