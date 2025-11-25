"""
测试文档生成Agent的示例脚本
展示如何与文档生成助手进行交互以生成技术文档
"""

import asyncio
import json
import websockets


async def test_documentation_generation():
    """测试文档生成Agent"""
    
    # WebSocket 连接地址
    uri = "ws://localhost:8000/ws/test_session_documentation"
    
    # 测试问题列表
    test_cases = [
        {
            "question": "请为这个AI聊天项目生成一份架构设计文档，包含整体架构、主要模块和技术栈的说明",
            "description": "测试架构文档生成"
        },
        {
            "question": "请分析并生成Agent系统的模块关系文档，要包含各Agent的职责和它们之间的关系，最好用Mermaid图表描述",
            "description": "测试模块关系分析"
        },
        {
            "question": "请生成前后端数据交互流程文档，包括WebSocket通信机制和数据流向",
            "description": "测试数据流分析"
        }
    ]
    
    print("=" * 80)
    print("文档生成Agent测试")
    print("=" * 80)
    print("\n注意：生成的文档内容将直接显示在控制台中，可以复制使用")
    print("=" * 80)
    
    async with websockets.connect(uri) as websocket:
        for i, test in enumerate(test_cases, 1):
            print(f"\n{'=' * 80}")
            print(f"测试 {i}/{len(test_cases)}: {test['description']}")
            print(f"问题: {test['question']}")
            print("=" * 80)
            
            # 发送消息，指定使用文档生成助手
            message = {
                "type": "message",
                "content": test['question'],
                "mode": "agent",
                "agent_name": "文档生成助手"
            }
            
            await websocket.send(json.dumps(message))
            print("\n[用户] " + test['question'])
            print("\n[助手开始生成文档] ")
            print("-" * 80)
            
            # 接收响应
            document_content = ""
            tool_calls_count = 0
            
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
                        document_content += content
                    
                    elif data["type"] == "tool_calls_start":
                        tools_info = data.get("tools", [])
                        tool_calls_count += len(tools_info)
                        print(f"\n\n[正在调用工具分析代码: {', '.join(t['name'] for t in tools_info)}]")
                    
                    elif data["type"] == "tool_call":
                        tool_name = data.get("toolName")
                        print(f"[✓ {tool_name} 完成]", end=" ")
                    
                    elif data["type"] == "assistant_end":
                        print("\n")
                        print("-" * 80)
                        print(f"[文档生成完成] 调用了 {tool_calls_count} 次工具，生成了 {len(document_content)} 字符的文档")
                        break
                    
                    elif data["type"] == "error":
                        print(f"\n[错误] {data.get('message')}")
                        break
                
                except Exception as e:
                    print(f"\n接收消息错误: {e}")
                    break
            
            # 等待一下再进行下一个测试
            if i < len(test_cases):
                print("\n等待5秒后继续下一个测试...")
                await asyncio.sleep(5)
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


async def interactive_documentation_mode():
    """交互模式：与文档生成助手对话"""
    
    uri = "ws://localhost:8000/ws/interactive_doc_session"
    
    print("=" * 80)
    print("文档生成助手 - 交互模式")
    print("=" * 80)
    print("提示：")
    print("- 你可以请求生成各种技术文档（架构文档、API文档、模块说明等）")
    print("- 生成的文档是Markdown格式，可以直接复制使用")
    print("- 输入 'exit' 或 'quit' 退出")
    print("- 输入 'stop' 停止当前生成")
    print("=" * 80)
    
    print("\n示例问题：")
    print("1. 请生成项目架构文档")
    print("2. 请分析并生成工具系统的设计文档")
    print("3. 请生成前端交互流程文档")
    print("4. 请用Mermaid图表描述Agent之间的关系")
    print("=" * 80)
    
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
                "agent_name": "文档生成助手"
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
                        print("\n\n[分析代码中: {}]".format(
                            ", ".join(t['name'] for t in tools_info)
                        ))
                    
                    elif data["type"] == "tool_call":
                        tool_name = data.get("toolName")
                        print(f"[✓ {tool_name}]", end=" ")
                    
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
        asyncio.run(interactive_documentation_mode())
    else:
        # 测试模式
        asyncio.run(test_documentation_generation())


if __name__ == "__main__":
    main()
