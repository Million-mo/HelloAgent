"""Function Call Agent Processor - 基于原生Function Calling机制的智能体处理器.

核心特点:
1. 直接利用LLM的原生Function Calling能力，不使用ReAct提示词
2. 支持流式输出
3. 支持自动多轮工具调用（LLM决定是否继续调用工具）
4. 完整的上下文管理（保存tool_calls和tool消息）
"""

import asyncio
import uuid
import json
from typing import Dict, List, Any, Optional
from fastapi import WebSocket

from tools.registry import ToolRegistry
from .session import SessionManager


class FunctionCallProcessor:
    """基于Function Calling的智能体处理器.
    
    工作流程:
    1. 用户输入 -> messages
    2. 调用LLM (stream=True, tools=定义)
    3. LLM返回: 可能包含 content 或 tool_calls
    4. 如果有 tool_calls:
       - 执行工具
       - 添加 tool 消息到历史
       - 回到步骤2 (让LLM继续思考)
    5. 如果只有 content (无 tool_calls):
       - 返回最终答案
       - 结束
    """
    
    def __init__(
        self,
        llm_client,
        tool_registry: ToolRegistry,
        session_manager: SessionManager,
        max_iterations: int = 10
    ):
        """
        初始化Function Call处理器.
        
        Args:
            llm_client: LLM客户端实例
            tool_registry: 工具注册表
            session_manager: 会话管理器
            max_iterations: 最大迭代次数，防止无限循环
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.session_manager = session_manager
        self.max_iterations = max_iterations
    
    async def process_streaming(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """
        处理用户消息，支持流式输出和自动工具调用.
        
        Args:
            websocket: WebSocket连接
            session_id: 会话ID
            user_input: 用户输入
            messages: 对话历史
        """
        # 添加用户消息
        messages.append({"role": "user", "content": user_input})
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        self.session_manager.set_cancel_flag(session_id, False)
        self.session_manager.set_current_message(session_id, message_id)
        
        try:
            # 多轮迭代处理
            for iteration in range(self.max_iterations):
                print(f"[FunctionCallAgent] 迭代 {iteration + 1}/{self.max_iterations}")
                
                # 检查取消信号
                if self.session_manager.get_cancel_flag(session_id):
                    await websocket.send_json({
                        "type": "assistant_end",
                        "messageId": message_id
                    })
                    return
                
                # 如果不是第一次迭代，创建新的 message_id
                if iteration > 0:
                    message_id = f"msg_{uuid.uuid4().hex[:8]}"
                    self.session_manager.set_current_message(session_id, message_id)
                
                # 调用LLM并处理响应
                has_tool_calls = await self._llm_iteration(
                    websocket, session_id, messages, message_id, iteration
                )
                
                print(f"[FunctionCallAgent] 迭代 {iteration + 1} 完成，是否有工具调用: {has_tool_calls}")
                
                # 如果没有工具调用，说明LLM已给出最终答案，结束循环
                if not has_tool_calls:
                    print(f"[FunctionCallAgent] LLM已返回最终答案，结束迭代")
                    break
            
            # 发送结束信号
            print(f"[FunctionCallAgent] 所有迭代完成，共 {iteration + 1} 次")
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": message_id
            })
        
        except asyncio.CancelledError:
            current_id = self.session_manager.get_current_message(session_id) or message_id
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": current_id
            })
            return
        except Exception as e:
            print(f"Error in FunctionCallProcessor: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"处理消息时出错: {str(e)}"
            })
        finally:
            self.session_manager.set_cancel_flag(session_id, False)
            self.session_manager.remove_current_message(session_id)
    
    async def _llm_iteration(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        message_id: str,
        iteration: int
    ) -> bool:
        """
        单次LLM调用迭代.
        
        Args:
            websocket: WebSocket连接
            session_id: 会话ID
            messages: 对话历史
            message_id: 消息ID
            iteration: 当前迭代次数
            
        Returns:
            是否有工具调用（True表示需要继续迭代）
        """
        # 准备请求参数
        request_params = {
            "model": self.llm_client.model,
            "messages": messages,
            "stream": True,
            "tools": self.tool_registry.get_tools_definitions()
        }
        
        # 发起流式请求
        response = await self.llm_client.client.chat.completions.create(**request_params)
        
        # 发送开始信号（每次迭代都发送）
        await websocket.send_json({
            "type": "assistant_start",
            "messageId": message_id
        })
        
        # 收集响应数据
        tool_calls_dict = {}
        content_buffer = ""
        
        async for chunk in response:
            # 检查取消信号
            if self.session_manager.get_cancel_flag(session_id):
                return False
            
            delta = chunk.choices[0].delta
            
            # 处理工具调用
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
            
            # 处理内容流
            if delta.content:
                content_buffer += delta.content
                await websocket.send_json({
                    "type": "assistant_chunk",
                    "messageId": message_id,
                    "content": delta.content
                })
        
        # 处理本次迭代的结果
        tool_calls = list(tool_calls_dict.values()) if tool_calls_dict else None
        
        print(f"[FunctionCallAgent] 迭代 {iteration} - tool_calls: {len(tool_calls) if tool_calls else 0}, content: {len(content_buffer)} 字符")
        
        if tool_calls:
            # 有工具调用：保存assistant消息并执行工具
            messages.append({
                "role": "assistant",
                "content": content_buffer if content_buffer else None,
                "tool_calls": tool_calls
            })
            
            # 先结束当前消息
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": message_id
            })
            
            # 执行工具调用
            await self._execute_tool_calls(websocket, session_id, messages, tool_calls)
            
            return True  # 需要继续迭代
        else:
            # 无工具调用：保存最终答案
            messages.append({
                "role": "assistant",
                "content": content_buffer
            })
            
            return False  # 结束迭代
    
    async def _execute_tool_calls(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]]
    ) -> None:
        """
        执行工具调用并添加tool消息.
        
        Args:
            websocket: WebSocket连接
            session_id: 会话ID
            messages: 对话历史
            tool_calls: 工具调用列表
        """
        # 通知前端工具调用开始
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
        
        # 执行所有工具调用
        for tool_call in tool_calls:
            # 检查取消信号
            if self.session_manager.get_cancel_flag(session_id):
                return
            
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]
            
            # 执行工具
            tool_result = await self.tool_registry.execute_tool(tool_name, tool_args)
            
            # 发送工具调用信息到前端
            await websocket.send_json({
                "type": "tool_call",
                "toolName": tool_name,
                "toolResult": tool_result
            })
            
            # 添加tool消息到历史（严格遵循OpenAI格式）
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": tool_name,
                "content": tool_result
            })
