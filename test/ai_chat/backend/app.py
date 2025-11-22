from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
import json
import asyncio
from typing import Dict, List, Any
import uuid
import httpx

# --- 1. 配置和初始化 ---

app = FastAPI(title="AI Chat API", version="1.1.0 - Refactored")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 修复版本：创建自定义 HTTP 客户端
http_client = httpx.AsyncClient()

client = AsyncOpenAI(
    api_key="sk-a39471beda78451f83d3068fce622d08",
    base_url="https://api.deepseek.com/v1",
    http_client=http_client  # 使用自定义 HTTP 客户端
)

# 会话级流式任务与控制状态
session_tasks: Dict[str, asyncio.Task] = {}
session_cancel_flags: Dict[str, bool] = {}
session_current_message: Dict[str, str] = {}

# --- 2. 工具定义和执行逻辑 (从原 app.py 提取) ---

WEATHER_DATA = {
    "beijing": {"temp": "18℃", "condition": "晴天", "humidity": "45%"},
    "shanghai": {"temp": "22℃", "condition": "多云", "humidity": "60%"},
    "hangzhou": {"temp": "20℃", "condition": "晴天", "humidity": "50%"},
    "shenzhen": {"temp": "28℃", "condition": "高温", "humidity": "70%"},
    "chengdu": {"temp": "16℃", "condition": "阴天", "humidity": "55%"},
}

def get_weather(location: str) -> str:
    """Get weather of a location."""
    location_lower = location.lower()
    if location_lower in WEATHER_DATA:
        data = WEATHER_DATA[location_lower]
        return f"{location}天气：温度 {data['temp']}，{data['condition']}，湿度 {data['humidity']}"
    else:
        return f"抱歉，没有 {location} 的天气数据。支持的城市：{', '.join(WEATHER_DATA.keys())}"

async def execute_tool(tool_name: str, arguments_str: str) -> str:
    """Execute the specified tool function."""
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

TOOLS_DEFINITION = [
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

# --- 3. 会话管理 (从原 app.py 提取) ---

sessions: Dict[str, List[Dict[str, Any]]] = {}

SYSTEM_PROMPT = (
    "你是一个智能助手，具有以下功能：\n"
    "1. 可以调用 get_weather 工具查询城市天气信息\n"
    "2. 支持自然语言对话和回答用户问题\n"
    "请根据用户需求，灵活使用工具或直接回答问题。"
)

def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    """Get or initialize messages for a session."""
    if session_id not in sessions:
        sessions[session_id] = [{
            "role": "system",
            "content": SYSTEM_PROMPT
        }]
    return sessions[session_id]

# --- 4. 核心逻辑重构 ---

async def process_message_streaming(websocket: WebSocket, session_id: str, user_input: str, messages: List[Dict[str, Any]]):
    """Handles the streaming chat logic, including tool calling, with cancel support."""
    
    # 1. 添加用户消息
    messages.append({"role": "user", "content": user_input})
    message_id = f"msg_{uuid.uuid4().hex[:8]}"
    session_cancel_flags[session_id] = False
    session_current_message[session_id] = message_id
    
    # 2. 第一次流式调用 (可能包含工具调用)
    tool_calls_dict = {}
    content_buffer = ""
    
    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=TOOLS_DEFINITION,
            stream=True
        )
        
        # 通知前端开始接收助手消息
        await websocket.send_json({
            "type": "assistant_start",
            "messageId": message_id
        })
        
        # 收集工具调用和内容
        async for chunk in response:
            # 检查是否收到停止信号
            if session_cancel_flags.get(session_id):
                await websocket.send_json({
                    "type": "assistant_end",
                    "messageId": message_id
                })
                return
            
            delta = chunk.choices[0].delta
            
            # 工具调用处理
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    index = tool_call.index
                    if index not in tool_calls_dict:
                        tool_calls_dict[index] = {
                            "id": tool_call.id,
                            "type": tool_call.type or "function",
                            "function": {"name": "", "arguments": ""}
                        }
                    
                    if tool_call.function:
                        if tool_call.function.name:
                            tool_calls_dict[index]["function"]["name"] = tool_call.function.name
                        if tool_call.function.arguments:
                            tool_calls_dict[index]["function"]["arguments"] += tool_call.function.arguments
            
            # 内容流处理
            if delta.content:
                content_buffer += delta.content
                await websocket.send_json({
                    "type": "assistant_chunk",
                    "messageId": message_id,
                    "content": delta.content
                })
        
        tool_calls = list(tool_calls_dict.values()) if tool_calls_dict else None
        
        # 3. 处理工具调用
        if tool_calls:
            # 添加 assistant 消息 (包含工具调用)
            messages.append({
                "role": "assistant",
                "content": content_buffer if content_buffer else None,
                "tool_calls": tool_calls
            })
            
            # 通知工具调用开始
            await websocket.send_json({
                "type": "tool_calls_start",
                "tools": [{"name": tc["function"]["name"]} for tc in tool_calls]
            })
            
            # 执行所有工具调用并添加 tool 消息
            for tool_call in tool_calls:
                # 停止检查
                if session_cancel_flags.get(session_id):
                    await websocket.send_json({
                        "type": "assistant_end",
                        "messageId": message_id
                    })
                    return
                
                tool_name = tool_call["function"]["name"]
                tool_args = tool_call["function"]["arguments"]
                tool_result = await execute_tool(tool_name, tool_args)
                
                # 发送工具调用信息
                await websocket.send_json({
                    "type": "tool_call",
                    "toolName": tool_name,
                    "toolResult": tool_result
                })
                
                # 添加 tool 消息到历史记录
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_name,
                    "content": tool_result
                })
            
            # 4. 第二次流式调用 (获取最终回复)
            final_response = await client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=True
            )
            
            # 通知开始新的助手消息 (使用新的 messageId)
            final_message_id = f"msg_{uuid.uuid4().hex[:8]}"
            session_current_message[session_id] = final_message_id
            await websocket.send_json({
                "type": "assistant_start",
                "messageId": final_message_id
            })
            
            final_content = ""
            async for chunk in final_response:
                # 检查停止信号
                if session_cancel_flags.get(session_id):
                    await websocket.send_json({
                        "type": "assistant_end",
                        "messageId": final_message_id
                    })
                    return
                
                if chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    final_content += text
                    await websocket.send_json({
                        "type": "assistant_chunk",
                        "messageId": final_message_id,
                        "content": text
                    })
            
            # 保存最终回复
            messages.append({"role": "assistant", "content": final_content})
            
            # 结束消息
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": final_message_id
            })
        else:
            # 没有工具调用，直接保存内容
            messages.append({"role": "assistant", "content": content_buffer})
            
            # 结束消息
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": message_id
            })
    
    except asyncio.CancelledError:
        # 任务被取消：发送结束消息
        current_id = session_current_message.get(session_id, message_id)
        await websocket.send_json({
            "type": "assistant_end",
            "messageId": current_id
        })
        return
    except Exception as e:
        print(f"Error in process_message_streaming: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"处理消息时出错: {str(e)}"
        })
    finally:
        # 清理当前消息和取消标记
        session_cancel_flags[session_id] = False
        session_current_message.pop(session_id, None)

# --- 5. 路由和事件处理 ---

@app.get("/")
async def root():
    return {"message": "AI Chat API is running", "version": "1.1.0 - Refactored"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    try:
        while True:
            # 接收用户消息或控制指令
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data['type'] == 'message':
                user_input = message_data['content']
                messages = get_session_messages(session_id)
                
                # 发送用户消息确认
                await websocket.send_json({
                    "type": "user_message_received",
                    "content": user_input
                })
                
                # 如果已有任务在运行，先取消
                if session_tasks.get(session_id) and not session_tasks[session_id].done():
                    session_cancel_flags[session_id] = True
                    session_tasks[session_id].cancel()
                
                # 启动新的流式任务
                task = asyncio.create_task(process_message_streaming(websocket, session_id, user_input, messages))
                session_tasks[session_id] = task
                
                # 任务完成后自动清理
                def _cleanup(_):
                    if session_tasks.get(session_id) is task:
                        session_tasks.pop(session_id, None)
                task.add_done_callback(_cleanup)
            
            elif message_data['type'] == 'stop':
                # 设置取消标记并取消当前任务
                session_cancel_flags[session_id] = True
                current_task = session_tasks.get(session_id)
                if current_task and not current_task.done():
                    current_task.cancel()
                
    except WebSocketDisconnect:
        print(f"Client {session_id} disconnected")
        # 清理会话数据（可选）
        if session_id in sessions:
            del sessions[session_id]
        # 取消可能的运行中任务
        if session_tasks.get(session_id) and not session_tasks[session_id].done():
            session_tasks[session_id].cancel()
        session_tasks.pop(session_id, None)
        session_cancel_flags.pop(session_id, None)
        session_current_message.pop(session_id, None)
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()

# 添加关闭处理
@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
