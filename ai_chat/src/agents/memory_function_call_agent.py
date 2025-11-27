"""Memory-Enhanced Function Call Agent - 具备记忆功能的Function Call Agent."""

import asyncio
import uuid
from typing import Dict, List, Any, Optional
from fastapi import WebSocket

from ..tools.registry import ToolRegistry
from ..chat.session import SessionManager
from .base_agent import BaseAgent
from .memory import MemoryManager, Memory, MemoryType, MemoryImportance
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MemoryFunctionCallAgent(BaseAgent):
    """
    具备记忆功能的 Function Call Agent
    
    新增功能:
    1. 短期记忆：自动记录对话历史中的关键信息
    2. 长期记忆：保存用户偏好、重要事实等跨会话信息
    3. 工作记忆：记录任务执行过程中的中间结果
    4. 记忆检索：在生成回复时自动引用相关记忆
    5. 记忆管理：支持记忆的增删改查
    
    使用场景:
    - 需要上下文连贯性的对话
    - 需要记住用户偏好的场景
    - 需要跨会话保持信息的应用
    """
    
    def __init__(
        self,
        name: str,
        llm_client,
        tool_registry: ToolRegistry,
        session_manager: SessionManager,
        max_iterations: int = 10,
        system_prompt: Optional[str] = None,
        max_short_term_memories: int = 50,
        max_long_term_memories: int = 100
    ):
        """
        初始化具备记忆功能的 Function Call Agent
        
        Args:
            name: Agent 名称
            llm_client: LLM 客户端实例
            tool_registry: 工具注册表
            session_manager: 会话管理器
            max_iterations: 最大工具调用迭代次数
            system_prompt: 系统提示词
            max_short_term_memories: 短期记忆最大数量
            max_long_term_memories: 长期记忆最大数量
        """
        # 增强的系统提示词，包含记忆功能说明
        enhanced_prompt = system_prompt or """你是一个具备记忆功能的AI助手。

**记忆能力：**
你可以记住对话中的关键信息，包括：
1. 用户偏好和习惯
2. 之前讨论的重要话题
3. 任务执行的结果和经验
4. 用户提供的个人信息

**记忆使用原则：**
1. 在回答问题时，主动引用相关的记忆内容
2. 当用户提到之前的对话内容时，检索相关记忆
3. 识别并记住用户的新偏好或重要信息
4. 提供更个性化和连贯的对话体验

**工作流程：**
1. 检索与当前问题相关的记忆
2. 基于记忆和当前输入生成回复
3. 识别并保存新的关键信息到记忆中
"""
        
        super().__init__(
            name=name,
            agent_type="memory_function_call",
            llm_client=llm_client,
            tool_registry=tool_registry,
            session_manager=session_manager,
            system_prompt=enhanced_prompt,
            max_iterations=max_iterations
        )
        self.max_iterations = max_iterations
        
        # 记忆管理器（作为属性）
        self.enable_memory = True  # 本Agent默认启用记忆功能
        self._session_memories: Dict[str, MemoryManager] = {}
        self.max_short_term_memories = max_short_term_memories
        self.max_long_term_memories = max_long_term_memories
        
        logger.info(f"MemoryFunctionCallAgent '{self.name}' 已初始化 (记忆: 启用)")
        tool_names = [tool.name for tool in self.tool_registry.get_all_tools()]
        logger.debug(f"可用工具 ({len(tool_names)}): {', '.join(tool_names)}")
        logger.debug(f"最大迭代次数: {self.max_iterations}")
    
    def _get_memory_manager(self, session_id: str) -> Optional[MemoryManager]:
        """获取会话的记忆管理器"""
        if not self.enable_memory:
            return None
            
        if session_id not in self._session_memories:
            self._session_memories[session_id] = MemoryManager(
                max_short_term=self.max_short_term_memories,
                max_long_term=self.max_long_term_memories
            )
            logger.debug(f"为会话 {session_id} 创建MemoryManager")
        return self._session_memories[session_id]
    
    async def run(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """
        执行 Agent 主循环（增强版，包含记忆功能）
        
        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
            user_input: 用户输入
            messages: 对话历史
        """
        # 获取记忆管理器
        memory_manager = self._get_memory_manager(session_id)
        
        # 确保消息历史中有本 Agent 的 system_prompt
        self._ensure_system_prompt(messages)
        
        # 步骤1: 检索相关记忆
        relevant_memories = await self._retrieve_relevant_memories(
            user_input, memory_manager
        )
        
        # 步骤2: 构建增强的用户消息（包含记忆上下文）
        enhanced_input = user_input
        if relevant_memories:
            memory_context = self._format_memories_for_context(relevant_memories)
            enhanced_input = f"{memory_context}\n\n**当前问题:** {user_input}"
            logger.info(f"[{self.name}] 检索到 {len(relevant_memories)} 条相关记忆")
        
        # 添加用户消息
        messages.append({"role": "user", "content": enhanced_input})
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        self.session_manager.set_cancel_flag(session_id, False)
        self.session_manager.set_current_message(session_id, message_id)
        
        # 用于收集本次对话的内容，以便后续提取记忆
        conversation_content = []
        
        try:
            # 执行多轮迭代
            for iteration in range(self.max_iterations):
                logger.debug(f"[{self.name}] 迭代 {iteration + 1}/{self.max_iterations} (session: {session_id})")
                
                # 检查取消信号
                if self.session_manager.get_cancel_flag(session_id):
                    logger.info(f"[{self.name}] 收到取消信号，停止处理 (session: {session_id})")
                    await websocket.send_json({
                        "type": "assistant_end",
                        "messageId": message_id
                    })
                    return
                
                # 如果不是第一次迭代，创建新的 message_id
                if iteration > 0:
                    message_id = f"msg_{uuid.uuid4().hex[:8]}"
                    self.session_manager.set_current_message(session_id, message_id)
                
                # 调用 LLM 并处理响应
                has_tool_calls, content = await self._process_iteration(
                    websocket, session_id, messages, message_id, iteration
                )
                
                # 收集对话内容
                if content:
                    conversation_content.append(content)
                
                # 如果没有工具调用，说明已得到最终答案
                if not has_tool_calls:
                    logger.info(f"[{self.name}] 已获得最终答案，结束迭代 (session: {session_id})")
                    break
            
            # 步骤3: 从对话中提取并保存新记忆
            await self._extract_and_save_memories(
                user_input, 
                "\n".join(conversation_content),
                memory_manager,
                websocket
            )
            
            # 发送结束信号
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": message_id
            })
        
        except asyncio.CancelledError:
            logger.info(f"[{self.name}] 任务被取消 (session: {session_id})")
            current_id = self.session_manager.get_current_message(session_id) or message_id
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": current_id
            })
            return
        except Exception as e:
            logger.error(f"[{self.name}] 处理错误 (session: {session_id}): {e}", exc_info=True)
            await websocket.send_json({
                "type": "error",
                "message": f"处理消息时出错: {str(e)}"
            })
        finally:
            self.session_manager.set_cancel_flag(session_id, False)
            self.session_manager.remove_current_message(session_id)
    
    async def _extract_and_save_memories(
        self,
        user_input: str,
        assistant_response: str,
        memory_manager: Optional[MemoryManager],
        websocket: WebSocket
    ) -> None:
        """从对话中提取关键信息并保存为记忆"""
        if not memory_manager:
            return
            
        # 简化版：直接保存对话内容为短期记忆
        memory_manager.add_memory(
            content=f"用户: {user_input}\n助手: {assistant_response}",
            memory_type=MemoryType.SHORT_TERM,
            importance=MemoryImportance.MEDIUM,
            tags=["对话"],
            metadata={"user_input": user_input}
        )
        logger.debug(f"[{self.name}] 保存对话记忆")
    
    async def _process_iteration(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        message_id: str,
        iteration: int
    ) -> tuple[bool, str]:
        """
        处理单次迭代
        
        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
            messages: 对话历史
            message_id: 消息 ID
            iteration: 当前迭代次数
            
        Returns:
            (是否有工具调用, 内容文本)
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
        
        # 发送开始信号
        await websocket.send_json({
            "type": "assistant_start",
            "messageId": message_id
        })
        
        # 收集响应数据
        tool_calls_dict = {}
        content_buffer = ""
        
        # 处理流式响应
        async for chunk in response:
            # 检查取消信号
            if self.session_manager.get_cancel_flag(session_id):
                return False, ""
            
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
        
        # 处理迭代结果
        tool_calls = list(tool_calls_dict.values()) if tool_calls_dict else None
        
        if tool_calls:
            logger.debug(f"[{self.name}] 迭代 {iteration} 检测到 {len(tool_calls)} 个工具调用")
            # 有工具调用：保存 assistant 消息并执行工具
            messages.append({
                "role": "assistant",
                "content": content_buffer if content_buffer else None,
                "tool_calls": tool_calls
            })
            
            # 结束当前消息
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": message_id
            })
            
            # 执行工具调用
            await self._execute_tools(websocket, session_id, messages, tool_calls)
            
            return True, content_buffer  # 需要继续迭代
        else:
            # 无工具调用：保存最终答案
            messages.append({
                "role": "assistant",
                "content": content_buffer
            })
            
            return False, content_buffer  # 结束迭代
    
    async def _execute_tools(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]]
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
        
        # 获取记忆管理器
        memory_manager = self._get_memory_manager(session_id)
        
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
            
            # 将工具调用结果保存为工作记忆
            await self._save_tool_call_memory(tool_name, tool_result, memory_manager)
            
            # 发送工具调用信息到前端
            await websocket.send_json({
                "type": "tool_call",
                "toolName": tool_name,
                "toolResult": tool_result
            })
            
            # 添加 tool 消息到历史（严格遵循 OpenAI 格式）
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": tool_name,
                "content": tool_result
            })
    
    async def _retrieve_relevant_memories(
        self,
        user_input: str,
        memory_manager: Optional[MemoryManager]
    ) -> List[Memory]:
        """检索与用户输入相关的记忆"""
        if not memory_manager:
            return []
            
        # 使用MemoryManager的智能检索功能
        all_memories = list(memory_manager.memories.values())
        # 简单实现：返回最近的几条重要记忆
        sorted_memories = sorted(
            all_memories,
            key=lambda m: (m.importance.value, m.timestamp),
            reverse=True
        )
        return sorted_memories[:5]  # 返回最多5条
    
    def _format_memories_for_context(self, memories: List[Memory]) -> str:
        """格式化记忆为上下文字符串"""
        if not memories:
            return ""
        
        memory_texts = []
        memory_texts.append("**相关记忆:**")
        for i, memory in enumerate(memories, 1):
            memory_texts.append(f"{i}. {memory.content}")
        
        return "\n".join(memory_texts)
    
    async def _save_tool_call_memory(
        self,
        tool_name: str,
        tool_result: str,
        memory_manager: Optional[MemoryManager]
    ) -> None:
        """保存工具调用结果为工作记忆"""
        if not memory_manager:
            return
            
        memory_manager.add_memory(
            content=f"工具调用: {tool_name}\n结果: {tool_result}",
            memory_type=MemoryType.WORKING,
            importance=MemoryImportance.LOW,
            tags=["工具调用", tool_name],
            metadata={"tool_name": tool_name}
        )
    
    # 记忆管理公开API
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return [tool.name for tool in self.tool_registry.get_all_tools()]
    
    def get_info(self) -> Dict[str, Any]:
        """获取 Agent 信息"""
        base_info = super().get_info()
        base_info.update({
            "max_iterations": self.max_iterations,
            "available_tools": self.get_available_tools(),
            "tool_count": len(self.get_available_tools()),
            "features": ["记忆功能", "对话上下文", "工具调用"],
            "memory_enabled": self.enable_memory,
            "memory_config": {
                "max_short_term": self.max_short_term_memories,
                "max_long_term": self.max_long_term_memories
            }
        })
        return base_info
    
    # 记忆管理公开方法
    def add_long_term_memory(
        self,
        session_id: str,
        content: str,
        importance: MemoryImportance = MemoryImportance.HIGH,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[Memory]:
        """添加长期记忆"""
        memory_manager = self._get_memory_manager(session_id)
        if not memory_manager:
            return None
            
        return memory_manager.add_memory(
            content=content,
            memory_type=MemoryType.LONG_TERM,
            importance=importance,
            tags=tags or [],
            metadata=metadata or {}
        )
    
    def get_memory_statistics(self, session_id: str) -> Dict[str, Any]:
        """获取记忆统计信息"""
        memory_manager = self._get_memory_manager(session_id)
        if not memory_manager:
            return {"total": 0, "by_type": {}, "by_importance": {}}
        return memory_manager.get_statistics()
    
    def get_all_memories(self, session_id: str) -> List[Memory]:
        """获取所有记忆"""
        memory_manager = self._get_memory_manager(session_id)
        if not memory_manager:
            return []
        return list(memory_manager.memories.values())
    
    def search_memories(self, session_id: str, keyword: str) -> List[Memory]:
        """搜索记忆"""
        memory_manager = self._get_memory_manager(session_id)
        if not memory_manager:
            return []
        return memory_manager.search_memories(keyword)
    
    def clear_session_memories(
        self,
        session_id: str,
        memory_type: MemoryType = None
    ) -> None:
        """清空会话记忆"""
        memory_manager = self._get_memory_manager(session_id)
        if memory_manager:
            memory_manager.clear_memories(memory_type)
            logger.info(f"[{self.name}] 清空会话 {session_id} 的记忆")
