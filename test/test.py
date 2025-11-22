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
        return f"错误：无法解析参数"
    
    if tool_name == "get_weather":
        location = arguments.get("location", "")
        if not location:
            return "错误：缺少位置参数"
        return get_weather(location)
    return f"错误：未知工具 {tool_name}"


# ------------------------
# Two-Pass: 第一步 non-stream，只识别工具，不输出内容
# ------------------------
async def detect_tool(messages):
    # system prompt 强制模型不要在第一次回答自然语言
    detect_messages = [{
        "role": "system",
        "content": (
            "你现在处于工具检测阶段。如果需要调用工具，请返回 tool_calls。"
            "如果不需要调用工具，请返回字符串 'NO_TOOL'，不要输出自然语言内容。"
        )
    }] + messages
    
    result = await client.chat.completions.create(
        model="deepseek-chat",
        messages=detect_messages,
        tools=tools,
        stream=False
    )
    return result.choices[0].message


# ------------------------
# 第二步：真正流式输出内容（最终用户看到的）
# ------------------------
async def final_stream(messages):
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=True
    )

    print("Model> ", end="", flush=True)
    full = ""
    async for chunk in response:
        if chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            full += text
            print(text, end="", flush=True)
    print()
    return full


# 单轮
async def process_single_turn(user_input, messages):

    # 把用户消息加进去
    messages.append({"role": "user", "content": user_input})

    print(f"\nUser> {user_input}")

    # ===============================
    # 第一步：non-stream 只判断工具
    # ===============================
    detect_msg = await detect_tool(messages)

    # --- 有工具调用 ---
    if detect_msg.tool_calls:

        # 写入 assistant tool_call 消息
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": detect_msg.tool_calls
        })

        for tool_call in detect_msg.tool_calls:
            tool_name = tool_call.function.name
            print(f"\n🔧 模型调用工具: {tool_name}")

            tool_result = await execute_tool(tool_name, tool_call.function.arguments)
            print(f"📤 工具结果: {tool_result}")

            # 把工具执行结果写入上下文
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": tool_result
            })

        # ===============================
        # 第二步：基于工具结果 → 流式输出最终答案
        # ===============================
        final_content = await final_stream(messages)
        messages.append({"role": "assistant", "content": final_content})
        return

    # --- 无工具调用 ---
    else:
        # 第二次调用：直接让模型流式回答
        final_content = await final_stream(messages)
        messages.append({"role": "assistant", "content": final_content})


# 对话循环
async def main():
    print("== Function Calling + Streaming Two-Pass 测试 ==")

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
        await process_single_turn(user_input, messages)


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
                    "location": {"type": "string", "description": "The city name, e.g. Beijing, Shanghai, 不能是中文，应该是英文"}
                },
                "required": ["location"]
            },
        }
    }
]

if __name__ == "__main__":
    asyncio.run(main())
