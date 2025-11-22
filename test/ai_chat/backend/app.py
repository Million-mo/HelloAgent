from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from typing import Dict, List, Any
import uuid

from config import config
from llm.client import LLMClient
from chat.session import SessionManager
from chat.processor import MessageProcessor
from chat.react_processor import ReactAgentProcessor
from chat.function_call_processor import FunctionCallProcessor
from tools.registry import ToolRegistry
from tools.weather import WeatherTool
from tools.calculator import CalculatorTool
from tools.time_tool import TimeTool
from tools.terminal import TerminalTool
from tools.file_operations import ReadFileTool, WriteFileTool, ListDirectoryTool

# --- 1. 配置和初始化 ---

app = FastAPI(title=config.app.title, version=config.app.version)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors.allow_origins,
    allow_credentials=config.cors.allow_credentials,
    allow_methods=config.cors.allow_methods,
    allow_headers=config.cors.allow_headers,
)

# 初始化 LLM 客户端
llm_client = LLMClient(config.llm)
llm_client.initialize()

# --- 2. 工具注册 (使用 ToolRegistry) ---

# 初始化工具注册表
tool_registry = ToolRegistry()

# 注册内置工具
tool_registry.register(WeatherTool())           # 天气查询（mock数据）
tool_registry.register(CalculatorTool())        # 计算器
tool_registry.register(TimeTool())              # 时间日期
tool_registry.register(TerminalTool())          # 终端命令执行
tool_registry.register(ReadFileTool())          # 读取文件
tool_registry.register(WriteFileTool())         # 写入文件
tool_registry.register(ListDirectoryTool())     # 列出目录

# --- 3. 会话管理 (使用 SessionManager) ---

# 初始化会话管理器
session_manager = SessionManager(system_prompt=config.app.system_prompt)

# 初始化消息处理器
message_processor = MessageProcessor(
    llm_client=llm_client,
    tool_registry=tool_registry,
    session_manager=session_manager
)

# 初始化 React Agent 处理器
react_agent_processor = ReactAgentProcessor(
    llm_client=llm_client,
    tool_registry=tool_registry,
    session_manager=session_manager,
    max_steps=10  # 最大执行步数
)

# 初始化 Function Call Agent 处理器
function_call_processor = FunctionCallProcessor(
    llm_client=llm_client,
    tool_registry=tool_registry,
    session_manager=session_manager,
    max_iterations=10  # 最大迭代次数
)

# --- 4. 路由和事件处理 ---

@app.get("/")
async def root():
    return {
        "message": "AI Chat API is running",
        "version": config.app.version
    }

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
                messages = session_manager.get_messages(session_id)
                
                # 获取处理模式（默认使用 Function Call Agent）
                mode = message_data.get('mode', 'function_call')  # 'function_call', 'react' 或 'simple'
                print(f"[DEBUG] 接收到消息，模式: {mode}")  # 调试日志
                
                # 发送用户消息确认
                await websocket.send_json({
                    "type": "user_message_received",
                    "content": user_input,
                    "mode": mode
                })
                
                # 如果已有任务在运行，先取消
                current_task = session_manager.get_task(session_id)
                if current_task and not current_task.done():
                    session_manager.set_cancel_flag(session_id, True)
                    current_task.cancel()
                
                # 根据模式选择处理器
                if mode == 'function_call':
                    # 使用 Function Call Agent 处理器（原生Function Calling，自动多轮）
                    task = asyncio.create_task(
                        function_call_processor.process_streaming(websocket, session_id, user_input, messages)
                    )
                elif mode == 'react':
                    # 使用 React Agent 处理器（Reasoning + Action 模式）
                    task = asyncio.create_task(
                        react_agent_processor.process_streaming(websocket, session_id, user_input, messages)
                    )
                else:
                    # 使用简单处理器（单次工具调用）
                    task = asyncio.create_task(
                        message_processor.process_streaming(websocket, session_id, user_input, messages)
                    )
                
                session_manager.set_task(session_id, task)
                
                # 任务完成后自动清理
                def _cleanup(_):
                    if session_manager.get_task(session_id) is task:
                        session_manager.remove_task(session_id)
                task.add_done_callback(_cleanup)
            
            elif message_data['type'] == 'stop':
                # 设置取消标记并取消当前任务
                session_manager.set_cancel_flag(session_id, True)
                current_task = session_manager.get_task(session_id)
                if current_task and not current_task.done():
                    current_task.cancel()
                
    except WebSocketDisconnect:
        print(f"Client {session_id} disconnected")
        # 清理会话数据
        session_manager.cleanup_session(session_id)
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()

# 添加关闭处理
@app.on_event("shutdown")
async def shutdown_event():
    await llm_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.server.host, port=config.server.port)
