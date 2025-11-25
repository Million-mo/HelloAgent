from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import asyncio
from typing import Dict, List, Any
import uuid

from config import config
from utils.logger import setup_logging, get_logger
from llm.client import LLMClient
from chat.session import SessionManager
from chat.processor import MessageProcessor
from chat.react_processor import ReactAgentProcessor
from chat.function_call_processor import FunctionCallProcessor
from agents import (
    AgentManager,
    FunctionCallAgent,
    SimpleAgent,
    AnalysisAgent,
    CodeAgent,
    PlanningAgent,
)
from tools.registry import ToolRegistry
from tools.weather import WeatherTool
from tools.calculator import CalculatorTool
from tools.time_tool import TimeTool
from tools.terminal import TerminalTool
from tools.file_operations import ReadFileTool, WriteFileTool, ListDirectoryTool

# --- 1. 配置和初始化 ---

# 初始化日志系统
setup_logging(
    log_dir=config.log.log_dir,
    log_level=config.log.log_level,
    max_bytes=config.log.max_bytes,
    backup_count=config.log.backup_count,
)
logger = get_logger(__name__)

# 定义生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时的逻辑
    logger.info(f"初始化 FastAPI 应用: {config.app.title} v{config.app.version}")
    yield
    # 关闭时的逻辑
    logger.info("开始关闭应用...")
    await llm_client.close()
    logger.info("LLM 客户端已关闭")
    logger.info("应用已关闭")

app = FastAPI(title=config.app.title, version=config.app.version, lifespan=lifespan)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors.allow_origins,
    allow_credentials=config.cors.allow_credentials,
    allow_methods=config.cors.allow_methods,
    allow_headers=config.cors.allow_headers,
)
logger.info("CORS 中间件已配置")

# 初始化 LLM 客户端
llm_client = LLMClient(config.llm)
llm_client.initialize()
logger.info(f"LLM 客户端已初始化: {config.llm.model}")

# --- 2. 工具注册 (使用 ToolRegistry) ---

# 初始化工具注册表
tool_registry = ToolRegistry()
logger.info("工具注册表已初始化")

# 注册内置工具
tool_registry.register(WeatherTool())  # 天气查询（mock数据）
tool_registry.register(CalculatorTool())  # 计算器
tool_registry.register(TimeTool())  # 时间日期
tool_registry.register(TerminalTool())  # 终端命令执行
tool_registry.register(ReadFileTool())  # 读取文件
tool_registry.register(WriteFileTool())  # 写入文件
tool_registry.register(ListDirectoryTool())  # 列出目录
registered_tools = [tool.name for tool in tool_registry.get_all_tools()]
logger.info(f"已注册 {len(registered_tools)} 个工具: {', '.join(registered_tools)}")

# --- 3. 会话管理 (使用 SessionManager) ---

# 初始化会话管理器（不册管理system_prompt，由Agent动态注入）
session_manager = SessionManager()
logger.info("会话管理器已初始化")

# --- 4. Agent 系统初始化 (多Agent架构) ---

# 创建 Agent 管理器
agent_manager = AgentManager(session_manager=session_manager)
logger.info("Agent 管理器已初始化")

# 创建并注册不同类型的Agent

# 1. FunctionCallAgent - 通用工具调用Agent（默认）
function_call_agent = FunctionCallAgent(
    name="通用助理",
    llm_client=llm_client,
    tool_registry=tool_registry,
    session_manager=session_manager,
    max_iterations=10,
    system_prompt=config.app.system_prompt,
)
agent_manager.register_agent(function_call_agent, is_default=True)
logger.info("FunctionCallAgent 已注册为默认 Agent")


# # 2. SimpleAgent - 纯对话Agent
# simple_agent = SimpleAgent(
#     name="简单对话",
#     llm_client=llm_client,
#     tool_registry=tool_registry,
#     session_manager=session_manager,
#     system_prompt="你是一个友好的AI助手，专注于提供清晰、简洁的对话。",
# )
# agent_manager.register_agent(simple_agent)
# logger.info("SimpleAgent 已注册")

# # 3. AnalysisAgent - 分析专家Agent
# analysis_agent = AnalysisAgent(
#     name="分析专家",
#     llm_client=llm_client,
#     tool_registry=tool_registry,
#     session_manager=session_manager,
#     thinking_depth=3,
# )
# agent_manager.register_agent(analysis_agent)
# logger.info("AnalysisAgent 已注册")

# # 4. CodeAgent - 编程助手Agent
# code_agent = CodeAgent(
#     name="编程助手",
#     llm_client=llm_client,
#     tool_registry=tool_registry,
#     session_manager=session_manager,
#     max_iterations=8,
# )
# agent_manager.register_agent(code_agent)
# logger.info("CodeAgent 已注册")

# # 5. PlanningAgent - 任务规划Agent
# planning_agent = PlanningAgent(
#     name="任务规划师",
#     llm_client=llm_client,
#     tool_registry=tool_registry,
#     session_manager=session_manager,
#     agent_manager=agent_manager,
#     max_iterations=20,
# )
# agent_manager.register_agent(planning_agent)
# logger.info("PlanningAgent 已注册")

# 输出 Agent 系统统计
stats = agent_manager.get_stats()
logger.info(f"Agent 系统统计: {stats}")

# --- 5. 消息处理器初始化 (向后兼容) ---

# 初始化消息处理器
message_processor = MessageProcessor(
    llm_client=llm_client, tool_registry=tool_registry, session_manager=session_manager
)
logger.info("消息处理器已初始化")

# 初始化 React Agent 处理器
# react_agent_processor = ReactAgentProcessor(
#     llm_client=llm_client,
#     tool_registry=tool_registry,
#     session_manager=session_manager,
#     max_steps=10,  # 最大执行步数
# )
# logger.info("React Agent 处理器已初始化")

# # 初始化 Function Call Agent 处理器
# function_call_processor = FunctionCallProcessor(
#     llm_client=llm_client,
#     tool_registry=tool_registry,
#     session_manager=session_manager,
#     max_iterations=10,  # 最大迭代次数
# )
# logger.info("Function Call 处理器已初始化")
# logger.info("\n=== 系统初始化完成 ===")

# --- 6. 路由和事件处理 ---


@app.get("/")
async def root():
    return {"message": "AI Chat API is running", "version": config.app.version}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/agent/info")
async def get_agent_info():
    """获取所有Agent信息"""
    return agent_manager.list_agents()


@app.get("/agent/stats")
async def get_agent_stats():
    """获取Agent系统统计"""
    return agent_manager.get_stats()


@app.post("/agent/switch/{session_id}")
async def switch_agent(session_id: str, agent_name: str):
    """
    切换会话Agent

    Args:
        session_id: 会话ID
        agent_name: 目标Agent名称
    """
    return agent_manager.switch_agent(session_id, agent_name)


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"客户端 {session_id} 已连接")

    try:
        while True:
            # 接收用户消息或控制指令
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data["type"] == "message":
                user_input = message_data["content"]
                messages = session_manager.get_messages(session_id)

                # 获取处理模式（默认使用 Agent）
                mode = message_data.get(
                    "mode", "agent"
                )  # 'agent', 'function_call', 'react' 或 'simple'
                logger.debug(f"[会话 {session_id}] 接收到消息，模式: {mode}")

                # 发送用户消息确认
                await websocket.send_json(
                    {
                        "type": "user_message_received",
                        "content": user_input,
                        "mode": mode,
                    }
                )

                # 如果已有任务在运行，先取消
                current_task = session_manager.get_task(session_id)
                if current_task and not current_task.done():
                    session_manager.set_cancel_flag(session_id, True)
                    current_task.cancel()
                    logger.warning(f"[会话 {session_id}] 取消上一个任务")

                # 根据模式选择处理器
                if mode == "agent":
                    # 使用Agent管理器（推荐）
                    # 支持指定Agent名称
                    agent_name = message_data.get("agent_name")
                    logger.info(
                        f"[会话 {session_id}] 使用 Agent 模式，Agent: {agent_name or '默认'}"
                    )
                    task = asyncio.create_task(
                        agent_manager.run(
                            websocket, session_id, user_input, messages, agent_name
                        )
                    )
                # elif mode == "function_call":
                #     # 使用 Function Call Agent 处理器（原生Function Calling，自动多轮）
                #     logger.info(f"[会话 {session_id}] 使用 Function Call 模式")
                #     task = asyncio.create_task(
                #         function_call_processor.process_streaming(
                #             websocket, session_id, user_input, messages
                #         )
                #     )
                # elif mode == "react":
                #     # 使用 React Agent 处理器（Reasoning + Action 模式）
                #     logger.info(f"[会话 {session_id}] 使用 React 模式")
                #     task = asyncio.create_task(
                #         react_agent_processor.process_streaming(
                #             websocket, session_id, user_input, messages
                #         )
                #     )
                else:
                    # 使用简单处理器（单次工具调用）
                    logger.info(f"[会话 {session_id}] 使用 Simple 模式")
                    task = asyncio.create_task(
                        message_processor.process_streaming(
                            websocket, session_id, user_input, messages
                        )
                    )

                session_manager.set_task(session_id, task)

                # 任务完成后自动清理
                def _cleanup(_):
                    if session_manager.get_task(session_id) is task:
                        session_manager.remove_task(session_id)

                task.add_done_callback(_cleanup)

            elif message_data["type"] == "stop":
                # 设置取消标记并取消当前任务
                logger.info(f"[会话 {session_id}] 收到停止指令")
                session_manager.set_cancel_flag(session_id, True)
                current_task = session_manager.get_task(session_id)
                if current_task and not current_task.done():
                    current_task.cancel()
                    logger.info(f"[会话 {session_id}] 任务已取消")

    except WebSocketDisconnect:
        logger.info(f"客户端 {session_id} 断开连接")
        # 清理会话数据
        session_manager.cleanup_session(session_id)
    except Exception as e:
        logger.error(f"[会话 {session_id}] WebSocket 错误: {e}", exc_info=True)
        await websocket.close()





if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.server.host, port=config.server.port)
