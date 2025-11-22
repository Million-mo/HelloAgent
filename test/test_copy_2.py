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
    location_lower = location.lower()
    if location_lower in WEATHER_DATA:
        data = WEATHER_DATA[location_lower]
        return f"{location}天气：温度 {data['temp']}，{data['condition']}，湿度 {data['humidity']}"
    else:
        return f"抱歉，没有 {location} 的天气数据。支持的城市：{', '.join(WEATHER_DATA.keys())}"

async def execute_tool(tool_name, arguments_str):
    try:
        arguments = json.loads(arguments_str)
    except json.JSONDecodeError:
        return f"错误：无法解析参数: {arguments_str}"
    
    if tool_name == "get_weather":
        location = arguments.get("location", "")
        if not location:
            return "错误：缺少位置参数"
        return get_weather(location)
    return f"错误：未知工具 {tool_name}"


# 修复版本：正确处理流式工具调用
async def process_single_turn_streaming(user_input, messages):
    messages.append({"role": "user", "content": user_input})
    print(f"\nUser> {user_input}")
    
    # 第一次流式调用：检测工具调用并收集内容
    print("Model> ", end="", flush=True)
    
    tool_calls_dict = {}  # 使用字典来组装tool_calls
    content_buffer = ""
    accumulated_content = ""
    
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        stream=True
    )
    
    # 第一阶段：收集工具调用和内容
    async for chunk in response:
        delta = chunk.choices[0].delta
        
        # 检测工具调用
        if delta.tool_calls:
            for tool_call in delta.tool_calls:
                if tool_call.id:  # 新的tool_call开始
                    tool_calls_dict[tool_call.index] = {
                        "id": tool_call.id,
                        "type": tool_call.type or "function",
                        "function": {"name": "", "arguments": ""}
                    }
                
                # 更新现有的tool_call
                if tool_call.index in tool_calls_dict:
                    if tool_call.function:
                        if tool_call.function.name:
                            tool_calls_dict[tool_call.index]["function"]["name"] = tool_call.function.name
                        if tool_call.function.arguments:
                            tool_calls_dict[tool_call.index]["function"]["arguments"] += tool_call.function.arguments
        
        # 收集内容（如果有）
        if delta.content:
            content_buffer += delta.content
            accumulated_content += delta.content
            print(delta.content, end="", flush=True)
    
    # 转换为列表格式
    tool_calls = list(tool_calls_dict.values()) if tool_calls_dict else None
    
    # 如果有工具调用，执行工具并继续对话
    if tool_calls:
        print(f"\n🔧 模型调用工具: {[tc['function']['name'] for tc in tool_calls]}")
        
        # 添加assistant消息（包含tool_calls）
        messages.append({
            "role": "assistant",
            "content": content_buffer if content_buffer else None,
            "tool_calls": tool_calls
        })
        
        # 执行所有工具调用
        tool_results = []
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]
            tool_result = await execute_tool(tool_name, tool_args)
            print(f"📤 {tool_name} 结果: {tool_result}")
            
            # 修复：添加tool消息时必需包含name字段
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": tool_name,  # 必需字段
                "content": tool_result
            })
            tool_results.append(tool_result)
        
        # 第二次流式调用：基于工具结果生成最终回答
        print("\nModel> ", end="", flush=True)
        final_response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True
        )
        
        final_content = ""
        async for chunk in final_response:
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                final_content += text
                print(text, end="", flush=True)
        
        print()  # 换行
        messages.append({"role": "assistant", "content": final_content})
        
    else:
        # 没有工具调用，直接保存内容
        messages.append({"role": "assistant", "content": accumulated_content})


# 对话循环
async def main():
    print("== 修复版：Function Calling + Streaming 单次调用 ==")
    
    messages = [{
        "role": "system",
        "content": (
            "你是一个智能助手，具有以下功能：\n"
            "1. 可以调用 get_weather 工具查询城市天气信息\n"
            "2. 支持自然语言对话和回答用户问题\n"
            "请根据用户需求，灵活使用工具或直接回答问题。"
        )
    }]
    
    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() in ["exit", "quit", "退出"]:
            break
        await process_single_turn_streaming(user_input, messages)


client = AsyncOpenAI(
    api_key="sk-a39471beda78451f83d3068fce622d08",
    base_url="https://api.deepseek.com/v1",
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather of a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "The city name, e.g. Beijing, Shanghai, must in English"}
                },
                "required": ["location"]
            },
        }
    }
]

if __name__ == "__main__":
    asyncio.run(main())
