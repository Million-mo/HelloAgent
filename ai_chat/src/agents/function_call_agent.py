"""Function Call Agent - 基于OpenAI Function Calling的Agent."""

import asyncio
import uuid
from typing import Dict, List, Any, Optional
from fastapi import WebSocket

from ..tools.registry import ToolRegistry
from ..tools.calculator import CalculatorTool
from ..tools.time_tool import TimeTool
from ..tools.terminal import TerminalTool
from ..tools.file_operations import ReadFileTool, WriteFileTool, ListDirectoryTool
from ..tools.code_analysis import (
    AnalyzeProjectStructureTool,
    SearchCodeTool,
    FindFilesTool,
    AnalyzeFileTool,
)
from ..tools.web_scraper import WebScraperTool
from ..chat.session import SessionManager
from .base_agent import BaseAgent
from .memory import MemoryManager, Memory, MemoryType, MemoryImportance
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FunctionCallAgent(BaseAgent):
    """
    Function Call Agent - 基于OpenAI Function Calling的Agent

    功能特性:
    1. 支持流式对话输出
    2. 支持工具调用和自动迭代
    3. 维护对话上下文
    4. 支持取消操作
    """

    def __init__(
        self,
        name: str,
        llm_client,
        tool_registry: Optional[ToolRegistry] = None,
        session_manager: SessionManager = None,
        max_iterations: int = 10,
        system_prompt: Optional[str] = None,
        memory_manager: Optional[MemoryManager] = None,  # 依赖注入
    ):
        """
        初始化 Function Call Agent

        Args:
            name: Agent 名称
            llm_client: LLM 客户端实例
            tool_registry: 工具注册表（如果传入则使用，否则创建专用工具子集）
            session_manager: 会话管理器
            max_iterations: 最大工具调用迭代次数
            system_prompt: 系统提示词
            memory_manager: 记忆管理器（可选，通过依赖注入传入）
        """
        # 优先使用传入的 tool_registry，如果没有则创建专用工具子集
        if tool_registry is not None:
            agent_tool_registry = tool_registry
            logger.debug(f"FunctionCallAgent '{name}' 使用传入的工具注册表")
        else:
            # 为 FunctionCallAgent 创建专用工具子集
            agent_tool_registry = ToolRegistry()
            required_tools = [
                CalculatorTool(),
                TimeTool(),
                TerminalTool(),
                ReadFileTool(),
                WriteFileTool(),
                ListDirectoryTool(),
                AnalyzeProjectStructureTool(),
                SearchCodeTool(),
                FindFilesTool(),
                AnalyzeFileTool(),
                WebScraperTool(),
            ]
            for tool in required_tools:
                agent_tool_registry.register(tool)
            logger.info(
                f"FunctionCallAgent '{name}' 创建工具子集成功: {', '.join([t.name for t in required_tools])}"
            )
        super().__init__(
            name=name,
            agent_type="function_call",
            llm_client=llm_client,
            tool_registry=agent_tool_registry,
            session_manager=session_manager,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
        )
        self.max_iterations = max_iterations

        # 记忆管理器（通过依赖注入）
        self.memory_manager = memory_manager

        logger.info(
            f"FunctionCallAgent '{self.name}' 已初始化 (记忆: {'启用' if memory_manager else '禁用'})"
        )
        tool_names = [tool.name for tool in self.tool_registry.get_all_tools()]
        logger.debug(f"可用工具 ({len(tool_names)}): {', '.join(tool_names)}")
        logger.debug(f"最大迭代次数: {self.max_iterations}")

    async def run(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]],
    ) -> None:
        """
        执行 Agent 主循环

        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
            user_input: 用户输入
            messages: 对话历史
        """
        # 确保消息历史中有本 Agent 的 system_prompt
        self._ensure_system_prompt(messages)

        # 添加用户消息
        messages.append({"role": "user", "content": user_input})
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        self.session_manager.set_cancel_flag(session_id, False)
        self.session_manager.set_current_message(session_id, message_id)

        try:
            # 执行多轮迭代
            for iteration in range(self.max_iterations):
                logger.debug(
                    f"[{self.name}] 迭代 {iteration + 1}/{self.max_iterations} (session: {session_id})"
                )

                # 检查取消信号
                if self.session_manager.get_cancel_flag(session_id):
                    logger.info(
                        f"[{self.name}] 收到取消信号，停止处理 (session: {session_id})"
                    )
                    await websocket.send_json(
                        {"type": "assistant_end", "messageId": message_id}
                    )
                    return

                # 如果不是第一次迭代，创建新的 message_id
                if iteration > 0:
                    message_id = f"msg_{uuid.uuid4().hex[:8]}"
                    self.session_manager.set_current_message(session_id, message_id)

                # 调用 LLM 并处理响应
                has_tool_calls = await self._process_iteration(
                    websocket, session_id, messages, message_id, iteration
                )

                # 如果没有工具调用，说明已得到最终答案
                if not has_tool_calls:
                    logger.info(
                        f"[{self.name}] 已获得最终答案，结束迭代 (session: {session_id})"
                    )
                    break

            # 发送结束信号
            await websocket.send_json(
                {"type": "assistant_end", "messageId": message_id}
            )

        except asyncio.CancelledError:
            logger.info(f"[{self.name}] 任务被取消 (session: {session_id})")
            current_id = (
                self.session_manager.get_current_message(session_id) or message_id
            )
            await websocket.send_json(
                {"type": "assistant_end", "messageId": current_id}
            )
            return
        except Exception as e:
            logger.error(
                f"[{self.name}] 处理错误 (session: {session_id}): {e}", exc_info=True
            )
            await websocket.send_json(
                {"type": "error", "message": f"处理消息时出错: {str(e)}"}
            )
        finally:
            self.session_manager.set_cancel_flag(session_id, False)
            self.session_manager.remove_current_message(session_id)

    async def _process_iteration(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        message_id: str,
        iteration: int,
    ) -> bool:
        """
        处理单次迭代

        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
            messages: 对话历史
            message_id: 消息 ID
            iteration: 当前迭代次数

        Returns:
            是否有工具调用（True 表示需要继续迭代）
        """
        # 准备请求参数
        request_params = {
            "model": self.llm_client.model,
            "messages": messages,
            "stream": True,
            "tools": self.tool_registry.get_tools_definitions(),
        }

        # 发起流式请求
        response = await self.llm_client.client.chat.completions.create(
            **request_params
        )

        # 发送开始信号
        await websocket.send_json({"type": "assistant_start", "messageId": message_id})

        # 收集响应数据
        tool_calls_dict = {}
        content_buffer = ""

        # 处理流式响应
        async for chunk in response:
            # 检查取消信号
            if self.session_manager.get_cancel_flag(session_id):
                return False

            # 检查 choices 是否为空（流式输出结束时可能为空）
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # 处理工具调用
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    index = tool_call.index
                    if index not in tool_calls_dict:
                        tool_calls_dict[index] = {
                            "id": tool_call.id,
                            "type": tool_call.type or "function",
                            "function": {"name": "", "arguments": ""},
                        }

                    if tool_call.function:
                        if tool_call.function.name:
                            tool_calls_dict[index]["function"]["name"] = (
                                tool_call.function.name
                            )
                        if tool_call.function.arguments:
                            tool_calls_dict[index]["function"]["arguments"] += (
                                tool_call.function.arguments
                            )

            # 处理内容流
            if delta.content:
                content_buffer += delta.content
                await websocket.send_json(
                    {
                        "type": "assistant_chunk",
                        "messageId": message_id,
                        "content": delta.content,
                    }
                )

        # 处理迭代结果
        tool_calls = list(tool_calls_dict.values()) if tool_calls_dict else None

        if tool_calls:
            logger.debug(
                f"[{self.name}] 迭代 {iteration} 检测到 {len(tool_calls)} 个工具调用"
            )
            # 有工具调用：保存 assistant 消息并执行工具
            messages.append(
                {
                    "role": "assistant",
                    "content": content_buffer if content_buffer else None,
                    "tool_calls": tool_calls,
                }
            )

            # 结束当前消息
            await websocket.send_json(
                {"type": "assistant_end", "messageId": message_id}
            )

            # 执行工具调用
            await self._execute_tools(websocket, session_id, messages, tool_calls)

            return True  # 需要继续迭代
        else:
            # 无工具调用：保存最终答案
            messages.append({"role": "assistant", "content": content_buffer})

            return False  # 结束迭代

    async def _execute_tools(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]],
    ) -> None:
        """
        执行工具调用

        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
            messages: 对话历史
            tool_calls: 工具调用列表
        """
        # 通知前端工具调用开始
        await websocket.send_json(
            {
                "type": "tool_calls_start",
                "tools": [
                    {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    }
                    for tc in tool_calls
                ],
            }
        )

        # 执行所有工具调用
        for tool_call in tool_calls:
            # 检查取消信号
            if self.session_manager.get_cancel_flag(session_id):
                return

            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]

            # 执行工具
            tool_result = await self.tool_registry.execute_tool(tool_name, tool_args)

            logger.debug(f"[{self.name}] 工具调用完成: {tool_name}")

            # 发送工具调用信息到前端
            await websocket.send_json(
                {"type": "tool_call", "toolName": tool_name, "toolResult": tool_result}
            )

            # 添加 tool 消息到历史（严格遵循 OpenAI 格式）
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_name,
                    "content": tool_result,
                }
            )

    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return [tool.name for tool in self.tool_registry.get_all_tools()]

    def get_info(self) -> Dict[str, Any]:
        """获取 Agent 信息"""
        base_info = super().get_info()
        base_info.update(
            {
                "max_iterations": self.max_iterations,
                "available_tools": self.get_available_tools(),
                "tool_count": len(self.get_available_tools()),
            }
        )
        return base_info
