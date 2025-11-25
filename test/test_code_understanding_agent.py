"""
测试代码理解Agent的示例脚本
展示如何与代码理解助手进行交互
"""

import asyncio
import json
import websockets
from typing import List, Dict


async def test_code_understanding_agent():
    """测试代码理解Agent"""
    
    # WebSocket 连接地址
    uri = "ws://localhost:8000/ws/test_session_code_understanding"
    
    # 测试问题列表
    test_questions = [
        {
            "question": "请分析一下这个项目的整体结构",
            "description": "测试项目结构分析能力"
        },
        {
            "question": "这个项目有哪些Agent？请帮我找到并说明它们的功能",
            "description": "测试代码搜索和理解能力"
        },
        {
            "question": "请帮我分析 function_call_agent.py 文件，说明它的核心功能",
            "description": "测试文件分析能力"
        },
        {
            "question": "在项目中查找所有使用了 WebSocket 的地方",
            "description": "测试代码搜索能力"
        }
    ]
    
    print("=" * 60)
    print("代码理解Agent测试")
    print("=" * 60)
    
    async with websockets.connect(uri) as websocket:
        # 切换到代码理解助手
        print("\n[切换Agent] 切换到 '代码理解助手'...")
        
        # 注意：这里需要通过HTTP API切换，或在消息中指定agent_name
        # 为了演示，我们直接在消息中指定
        
        for i, test in enumerate(test_questions, 1):
            print(f"\n{'=' * 60}")
            print(f"测试 {i}/{len(test_questions)}: {test['description']}")
            print(f"问题: {test['question']}")
            print("=" * 60)
            
            # 发送消息，指定使用代码理解助手
            message = {
                "type": "message",
                "content": test['question'],
                "mode": "agent",
                "agent_name": "代码理解助手"
            }
            
            await websocket.send(json.dumps(message))
            print("\n[用户] " + test['question'])
            print("\n[助手] ", end="", flush=True)
            
            # 接收响应
            assistant_content = ""
            tool_calls_info = []
            
            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    if data["type"] == "user_message_received":
                        continue
                    
                    elif data["type"] == "assistant_start":
                        pass
                    
                    elif data["type"] == "assistant_chunk":
                        content = data.get("content", "")
                        print(content, end="", flush=True)
                        assistant_content += content
                    
                    elif data["type"] == "tool_calls_start":
                        tools_info = data.get("tools", [])
                        print("\n\n[工具调用开始]")
                        for tool in tools_info:
                            print(f"  - {tool['name']}")
                    
                    elif data["type"] == "tool_call":
                        tool_name = data.get("toolName")
                        tool_result = data.get("toolResult", "")
                        result_preview = tool_result[:200] + "..." if len(tool_result) > 200 else tool_result
                        print(f"\n[工具结果] {tool_name}:")
                        print(f"  {result_preview}")
                        tool_calls_info.append({
                            "name": tool_name,
                            "result": tool_result
                        })
                    
                    elif data["type"] == "assistant_end":
                        print("\n")
                        break
                    
                    elif data["type"] == "error":
                        print(f"\n[错误] {data.get('message')}")
                        break
                
                except Exception as e:
                    print(f"\n接收消息错误: {e}")
                    break
            
            # 等待一下再进行下一个测试
            if i < len(test_questions):
                print("\n等待3秒后继续下一个测试...")
                await asyncio.sleep(3)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


async def interactive_mode():
    """交互模式：与代码理解助手对话"""
    
    uri = "ws://localhost:8000/ws/interactive_code_session"
    
    print("=" * 60)
    print("代码理解助手 - 交互模式")
    print("=" * 60)
    print("输入 'exit' 或 'quit' 退出")
    print("输入 'stop' 停止当前生成")
    print("=" * 60)
    
    async with websockets.connect(uri) as websocket:
        while True:
            # 获取用户输入
            try:
                user_input = input("\n[你] ")
            except EOFError:
                break
            
            if user_input.lower() in ['exit', 'quit', '退出']:
                print("再见！")
                break
            
            if user_input.lower() == 'stop':
                # 发送停止信号
                await websocket.send(json.dumps({"type": "stop"}))
                print("[系统] 已发送停止信号")
                continue
            
            if not user_input.strip():
                continue
            
            # 发送消息
            message = {
                "type": "message",
                "content": user_input,
                "mode": "agent",
                "agent_name": "代码理解助手"
            }
            
            await websocket.send(json.dumps(message))
            print("\n[助手] ", end="", flush=True)
            
            # 接收响应
            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    if data["type"] == "assistant_chunk":
                        content = data.get("content", "")
                        print(content, end="", flush=True)
                    
                    elif data["type"] == "tool_calls_start":
                        tools_info = data.get("tools", [])
                        print("\n\n[调用工具: {}]".format(
                            ", ".join(t['name'] for t in tools_info)
                        ))
                    
                    elif data["type"] == "tool_call":
                        tool_name = data.get("toolName")
                        print(f"[✓ {tool_name} 完成]", end=" ")
                    
                    elif data["type"] == "assistant_end":
                        print("\n")
                        break
                    
                    elif data["type"] == "error":
                        print(f"\n[错误] {data.get('message')}")
                        break
                
                except Exception as e:
                    print(f"\n接收消息错误: {e}")
                    break


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        # 交互模式
        asyncio.run(interactive_mode())
    else:
        # 测试模式
        asyncio.run(test_code_understanding_agent())


if __name__ == "__main__":
    main()
