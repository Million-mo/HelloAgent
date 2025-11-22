# 我想测试一下functioncall的流式生成

from openai import AsyncOpenAI
import json
import asyncio

# 天气数据库（模拟）
WEATHER_DATA = {
    "beijing": {"temp": "18℃", "condition": "晴天", "humidity": "45%"},
    "shanghai": {"temp": "22℃", "condition": "多云", "humidity": "60%"},
    "hangzhou": {"temp": "20℃", "condition": "晴天", "humidity": "50%"},
    "shenzhen": {"temp": "28℃", "condition": "高温", "humidity": "70%"},
    "chengdu": {"temp": "16℃", "condition": "阴天", "humidity": "55%"},
}

def get_weather(location):
    """
    获取指定位置的天气信息
    
    Args:
        location: 城市名称
    
    Returns:
        天气信息字符串
    """
    location_lower = location.lower()
    
    if location_lower in WEATHER_DATA:
        data = WEATHER_DATA[location_lower]
        return f"{location}天气：温度 {data['temp']}，{data['condition']}，湿度 {data['humidity']}"
    else:
        # 返回未知城市的响应
        return f"抱歉，没有 {location} 的天气数据。支持的城市：{', '.join(WEATHER_DATA.keys())}"

async def execute_tool(tool_name, arguments_str):
    """
    执行工具调用
    
    Args:
        tool_name: 工具名称
        arguments_str: 工具参数（JSON字符串）
    
    Returns:
        工具执行结果
    """
    try:
        arguments = json.loads(arguments_str)
    except json.JSONDecodeError:
        return f"错误：无法解析参数"
    
    if tool_name == "get_weather":
        location = arguments.get("location", "")
        if not location:
            return "错误：缺少位置参数"
        return get_weather(location)
    else:
        return f"错误：未知的工具 {tool_name}"

async def send_messages(messages, stream=False):
    """发送消息，支持流式输出
    
    Args:
        messages: 消息列表
        stream: 是否使用流式输出（注意：Function Calling决策阶段必须非流式）
    """
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        stream=stream
    )
    
    if stream:
        # 流式模式：逐块输出
        full_content = ""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_content += content
                print(content, end="", flush=True)
        return full_content
    else:
        # 非流式模式：直接返回
        return response.choices[0].message

client = AsyncOpenAI(
    api_key="sk-a39471beda78451f83d3068fce622d08",
    base_url="https://api.deepseek.com",
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather of a location, the user should supply a location first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    }
                },
                "required": ["location"]
            },
        }
    },
]

async def process_single_turn(user_input, messages):
    """处理单轮对话"""
    messages.append({"role": "user", "content": user_input})
    print(f"\nUser> {user_input}")
    
    # 第一步：获取模型响应（可能包含工具调用）
    message = await send_messages(messages, stream=False)
        
    # 处理工具调用
    for tool_call in message.tool_calls:
        tool_name = tool_call.function.name
        print(f"\n🔧 模型调用工具: {tool_name}")
        
        # 添加assistant消息到历史
        messages.append({"role": "assistant", "content": message.content, "tool_calls": [{
            "id": tool_call.id,
            "type": "function",
            "function": {
                "name": tool_name,
                "arguments": tool_call.function.arguments
            }
        }]})
        
        # 执行真实的工具调用
        tool_result = await execute_tool(tool_name, tool_call.function.arguments)
        
        print(f"📤 工具结果: {tool_result}")
        
        # 添加工具结果到历史
        messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_name, "content": tool_result})
    
    # 第二步：基于工具结果获取最终响应（流式）
    print(f"\nModel> ", end="")
    response_content = await send_messages(messages, stream=True)
    messages.append({"role": "assistant", "content": response_content})


# 多轮对话循环
async def main():
    print("\n" + "=" * 50)
    print("Function Calling 流式对话测试")
    print("输入 'exit' 或 'quit' 退出对话")
    print("=" * 50)
    
    messages = []
    
    while True:
        try:
            user_input = input("\n你: ").strip()
            
            if user_input.lower() in ['exit', 'quit', '退出']:
                print("\n再见！")
                break
            
            if not user_input:
                continue
            
            await process_single_turn(user_input, messages)
            
        except KeyboardInterrupt:
            print("\n\n对话已中断。")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            continue

if __name__ == "__main__":
    asyncio.run(main())