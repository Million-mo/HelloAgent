"""Message processor for handling streaming chat with tool calls."""

import asyncio
import uuid
from typing import Dict, List, Any
from fastapi import WebSocket

from ..tools.registry import ToolRegistry
from .session import SessionManager
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MessageProcessor:
    """Handles streaming message processing with tool calling support."""
    
    def __init__(
        self,
        llm_client,  # LLMClient instance
        tool_registry: ToolRegistry,
        session_manager: SessionManager
    ):
        """
        Initialize message processor.
        
        Args:
            llm_client: LLMClient instance
            tool_registry: Tool registry for executing tools
            session_manager: Session manager for state management
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.session_manager = session_manager
    
    async def process_streaming(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """
        Process a user message with streaming response and tool calling.
        
        Args:
            websocket: WebSocket connection
            session_id: Session identifier
            user_input: User's input message
            messages: Conversation history
        """
        # 1. 添加用户消息
        messages.append({"role": "user", "content": user_input})
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        self.session_manager.set_cancel_flag(session_id, False)
        self.session_manager.set_current_message(session_id, message_id)
        
        try:
            # 2. 第一次流式调用 (可能包含工具调用)
            tool_calls = await self._stream_llm_response(
                websocket, session_id, messages, message_id
            )
            
            # 3. 处理工具调用
            if tool_calls:
                # 先结束第一条消息
                await websocket.send_json({
                    "type": "assistant_end",
                    "messageId": message_id
                })
                # 然后处理工具调用
                await self._handle_tool_calls(
                    websocket, session_id, messages, tool_calls, message_id
                )
            else:
                # 没有工具调用，结束消息
                await websocket.send_json({
                    "type": "assistant_end",
                    "messageId": message_id
                })
        
        except asyncio.CancelledError:
            # 任务被取消：发送结束消息
            logger.info(f"处理被取消 (session: {session_id})")
            current_id = self.session_manager.get_current_message(session_id) or message_id
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": current_id
            })
            return
        except Exception as e:
            logger.error(f"处理消息错误 (session: {session_id}): {e}", exc_info=True)
            await websocket.send_json({
                "type": "error",
                "message": f"处理消息时出错: {str(e)}"
            })
        finally:
            # 清理当前消息和取消标记
            self.session_manager.set_cancel_flag(session_id, False)
            self.session_manager.remove_current_message(session_id)
    
    async def _stream_llm_response(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        message_id: str,
        include_tools: bool = True
    ) -> List[Dict[str, Any]] | None:
        """
        Stream LLM response and collect tool calls.
        
        Args:
            websocket: WebSocket connection
            session_id: Session identifier
            messages: Conversation history
            message_id: Current message ID
            include_tools: Whether to include tools in the request
            
        Returns:
            List of tool calls if any, None otherwise
        """
        # 准备请求参数
        request_params = {
            "model": self.llm_client.model,
            "messages": messages,
            "stream": True
        }
        if include_tools:
            request_params["tools"] = self.tool_registry.get_tools_definitions()
        
        # 发起流式请求
        response = await self.llm_client.client.chat.completions.create(**request_params)
        
        # 通知前端开始接收助手消息
        await websocket.send_json({
            "type": "assistant_start",
            "messageId": message_id
        })
        
        # 收集工具调用和内容
        tool_calls_dict = {}
        content_buffer = ""
        
        async for chunk in response:
            # 检查是否收到停止信号
            if self.session_manager.get_cancel_flag(session_id):
                await websocket.send_json({
                    "type": "assistant_end",
                    "messageId": message_id
                })
                return None
            
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
        
        # 保存助手消息
        tool_calls = list(tool_calls_dict.values()) if tool_calls_dict else None
        if tool_calls:
            # 有工具调用，保存带工具调用的消息
            messages.append({
                "role": "assistant",
                "content": content_buffer if content_buffer else None,
                "tool_calls": tool_calls
            })
        else:
            # 没有工具调用，保存普通消息
            messages.append({"role": "assistant", "content": content_buffer})
        
        return tool_calls
    
    async def _handle_tool_calls(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]],
        original_message_id: str
    ) -> None:
        """
        Execute tool calls and generate final response.
        
        Args:
            websocket: WebSocket connection
            session_id: Session identifier
            messages: Conversation history
            tool_calls: List of tool calls to execute
            original_message_id: Original message ID
        """
        # 通知工具调用开始
        await websocket.send_json({
            "type": "tool_calls_start",
            "tools": [
                {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"]
                }
                for tc in tool_calls
            ]
        })
        
        # 执行所有工具调用并添加 tool 消息
        for tool_call in tool_calls:
            # 停止检查
            if self.session_manager.get_cancel_flag(session_id):
                await websocket.send_json({
                    "type": "assistant_end",
                    "messageId": original_message_id
                })
                return
            
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]
            tool_result = await self.tool_registry.execute_tool(tool_name, tool_args)
            
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
        
        # 第二次流式调用 (获取最终回复)
        final_message_id = f"msg_{uuid.uuid4().hex[:8]}"
        self.session_manager.set_current_message(session_id, final_message_id)
        
        # 不再包含工具定义，避免循环调用
        await self._stream_llm_response(
            websocket, session_id, messages, final_message_id, include_tools=False
        )
        
        # 结束消息
        await websocket.send_json({
            "type": "assistant_end",
            "messageId": final_message_id
        })
