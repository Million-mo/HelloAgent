"""专门化Agent实现 - 针对不同任务场景的Agent."""

import asyncio
import uuid
from typing import Dict, List, Any, Optional
from fastapi import WebSocket

from ..tools.registry import ToolRegistry
from ..chat.session import SessionManager
from .base_agent import BaseAgent
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SimpleAgent(BaseAgent):
    """
    简单对话Agent - 仅支持基础对话，不调用工具
    
    适用场景:
    - 纯文本对话
    - 不需要工具辅助的任务
    """
    
    def __init__(
        self,
        name: str,
        llm_client,
        tool_registry: ToolRegistry,
        session_manager: SessionManager,
        system_prompt: Optional[str] = None
    ):
        super().__init__(
            name=name,
            agent_type="simple",
            llm_client=llm_client,
            tool_registry=tool_registry,
            session_manager=session_manager,
            system_prompt=system_prompt
        )
        logger.info(f"SimpleAgent '{self.name}' 已初始化")
    
    async def run(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """执行简单对话"""
        # 确保消息历史中有本 Agent 的 system_prompt
        self._ensure_system_prompt(messages)
        
        messages.append({"role": "user", "content": user_input})
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        self.session_manager.set_cancel_flag(session_id, False)
        self.session_manager.set_current_message(session_id, message_id)
        
        try:
            # 准备请求参数（不包含工具）
            request_params = {
                "model": self.llm_client.model,
                "messages": messages,
                "stream": True
            }
            
            # 发起流式请求
            response = await self.llm_client.client.chat.completions.create(**request_params)
            
            # 发送开始信号
            await websocket.send_json({
                "type": "assistant_start",
                "messageId": message_id
            })
            
            # 流式输出
            content_buffer = ""
            async for chunk in response:
                if self.session_manager.get_cancel_flag(session_id):
                    break
                
                delta = chunk.choices[0].delta
                if delta.content:
                    content_buffer += delta.content
                    await websocket.send_json({
                        "type": "assistant_chunk",
                        "messageId": message_id,
                        "content": delta.content
                    })
            
            # 保存消息
            messages.append({"role": "assistant", "content": content_buffer})
            
            # 发送结束信号
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": message_id
            })
        
        except Exception as e:
            print(f"[SimpleAgent] 错误: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"处理消息时出错: {str(e)}"
            })
        finally:
            self.session_manager.set_cancel_flag(session_id, False)
            self.session_manager.remove_current_message(session_id)


class AnalysisAgent(BaseAgent):
    """
    分析型Agent - 专注于数据分析和推理
    
    适用场景:
    - 数据分析
    - 逻辑推理
    - 问题分解
    """
    
    def __init__(
        self,
        name: str,
        llm_client,
        tool_registry: ToolRegistry,
        session_manager: SessionManager,
        system_prompt: Optional[str] = None,
        thinking_depth: int = 3
    ):
        custom_prompt = system_prompt or (
            "你是一个专业的分析师AI助手。\n"
            "你的特长是:\n"
            "1. 深入分析问题的本质\n"
            "2. 提供多角度的解决方案\n"
            "3. 进行逻辑推理和数据分析\n"
            "4. 分步骤拆解复杂问题\n"
            "请用清晰的结构化方式回答问题。"
        )
        
        super().__init__(
            name=name,
            agent_type="analysis",
            llm_client=llm_client,
            tool_registry=tool_registry,
            session_manager=session_manager,
            system_prompt=custom_prompt,
            thinking_depth=thinking_depth
        )
        self.thinking_depth = thinking_depth
        logger.info(f"AnalysisAgent '{self.name}' 已初始化 (思考深度: {thinking_depth})")
    
    async def run(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """执行分析任务"""
        # 确保消息历史中有本 Agent 的 system_prompt
        self._ensure_system_prompt(messages)
        
        # 添加分析提示
        enhanced_input = f"请深入分析以下问题:\n{user_input}\n\n要求:\n1. 分步骤思考\n2. 提供多个角度的分析\n3. 给出结论和建议"
        messages.append({"role": "user", "content": enhanced_input})
        
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        self.session_manager.set_cancel_flag(session_id, False)
        self.session_manager.set_current_message(session_id, message_id)
        
        try:
            request_params = {
                "model": self.llm_client.model,
                "messages": messages,
                "stream": True,
                "tools": self.tool_registry.get_tools_definitions()
            }
            
            response = await self.llm_client.client.chat.completions.create(**request_params)
            
            await websocket.send_json({
                "type": "assistant_start",
                "messageId": message_id
            })
            
            content_buffer = ""
            async for chunk in response:
                if self.session_manager.get_cancel_flag(session_id):
                    break
                
                delta = chunk.choices[0].delta
                if delta.content:
                    content_buffer += delta.content
                    await websocket.send_json({
                        "type": "assistant_chunk",
                        "messageId": message_id,
                        "content": delta.content
                    })
            
            messages.append({"role": "assistant", "content": content_buffer})
            
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": message_id
            })
        
        except Exception as e:
            print(f"[AnalysisAgent] 错误: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"处理消息时出错: {str(e)}"
            })
        finally:
            self.session_manager.set_cancel_flag(session_id, False)
            self.session_manager.remove_current_message(session_id)


class CodeAgent(BaseAgent):
    """
    编程助手Agent - 专注于代码相关任务
    
    适用场景:
    - 代码编写
    - 代码审查
    - 问题调试
    - 技术文档
    """
    
    def __init__(
        self,
        name: str,
        llm_client,
        tool_registry: ToolRegistry,
        session_manager: SessionManager,
        system_prompt: Optional[str] = None,
        max_iterations: int = 5
    ):
        custom_prompt = system_prompt or (
            "你是一个专业的编程助手。\n"
            "你的能力包括:\n"
            "1. 编写高质量、可维护的代码\n"
            "2. 解释代码逻辑和原理\n"
            "3. 调试和优化代码\n"
            "4. 提供最佳实践建议\n"
            "5. 使用文件操作和终端工具来完成任务\n"
            "请提供清晰的代码示例和详细的说明。"
        )
        
        super().__init__(
            name=name,
            agent_type="code",
            llm_client=llm_client,
            tool_registry=tool_registry,
            session_manager=session_manager,
            system_prompt=custom_prompt,
            max_iterations=max_iterations
        )
        self.max_iterations = max_iterations
        logger.info(f"CodeAgent '{self.name}' 已初始化 (最大迭代: {max_iterations})")
    
    async def run(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """执行代码相关任务"""
        # 确保消息历史中有本 Agent 的 system_prompt
        self._ensure_system_prompt(messages)
        
        messages.append({"role": "user", "content": user_input})
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        self.session_manager.set_cancel_flag(session_id, False)
        self.session_manager.set_current_message(session_id, message_id)
        
        try:
            # 支持工具调用的迭代
            for iteration in range(self.max_iterations):
                print(f"[CodeAgent] 迭代 {iteration + 1}/{self.max_iterations}")
                
                if self.session_manager.get_cancel_flag(session_id):
                    await websocket.send_json({
                        "type": "assistant_end",
                        "messageId": message_id
                    })
                    return
                
                if iteration > 0:
                    message_id = f"msg_{uuid.uuid4().hex[:8]}"
                    self.session_manager.set_current_message(session_id, message_id)
                
                request_params = {
                    "model": self.llm_client.model,
                    "messages": messages,
                    "stream": True,
                    "tools": self.tool_registry.get_tools_definitions()
                }
                
                response = await self.llm_client.client.chat.completions.create(**request_params)
                
                await websocket.send_json({
                    "type": "assistant_start",
                    "messageId": message_id
                })
                
                tool_calls_dict = {}
                content_buffer = ""
                
                async for chunk in response:
                    if self.session_manager.get_cancel_flag(session_id):
                        return
                    
                    delta = chunk.choices[0].delta
                    
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
                    
                    if delta.content:
                        content_buffer += delta.content
                        await websocket.send_json({
                            "type": "assistant_chunk",
                            "messageId": message_id,
                            "content": delta.content
                        })
                
                tool_calls = list(tool_calls_dict.values()) if tool_calls_dict else None
                
                if tool_calls:
                    messages.append({
                        "role": "assistant",
                        "content": content_buffer if content_buffer else None,
                        "tool_calls": tool_calls
                    })
                    
                    await websocket.send_json({
                        "type": "assistant_end",
                        "messageId": message_id
                    })
                    
                    # 执行工具
                    await self._execute_tools(websocket, session_id, messages, tool_calls)
                    continue
                else:
                    messages.append({"role": "assistant", "content": content_buffer})
                    break
            
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": message_id
            })
        
        except Exception as e:
            print(f"[CodeAgent] 错误: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"处理消息时出错: {str(e)}"
            })
        finally:
            self.session_manager.set_cancel_flag(session_id, False)
            self.session_manager.remove_current_message(session_id)
    
    async def _execute_tools(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]]
    ) -> None:
        """执行工具调用"""
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
        
        for tool_call in tool_calls:
            if self.session_manager.get_cancel_flag(session_id):
                return
            
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]
            tool_result = await self.tool_registry.execute_tool(tool_name, tool_args)
            
            print(f"[CodeAgent] 工具调用: {tool_name}")
            
            await websocket.send_json({
                "type": "tool_call",
                "toolName": tool_name,
                "toolResult": tool_result
            })
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": tool_name,
                "content": tool_result
            })
