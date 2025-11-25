"""Code Understanding Agent - 专门用于理解和分析代码项目."""

import asyncio
import uuid
from typing import Dict, List, Any, Optional
from fastapi import WebSocket

from tools.registry import ToolRegistry
from chat.session import SessionManager
from .base_agent import BaseAgent
from .memory_mixin import MemoryMixin
from .memory import MemoryType, MemoryImportance
from utils.logger import get_logger

logger = get_logger(__name__)


class CodeUnderstandingAgent(MemoryMixin, BaseAgent):
    """
    Code Understanding Agent - 专门用于理解和分析代码项目
    
    功能特性:
    1. 分析本地代码仓库结构
    2. 理解项目的架构、文档和核心功能
    3. 回答关于项目的技术问题
    4. 支持代码搜索、文件浏览等操作
    5. 提供代码质量分析和改进建议
    
    适用场景:
    - 快速了解新项目
    - 代码库导航和探索
    - 技术架构分析
    - 代码审查和优化建议
    """
    
    def __init__(
        self,
        name: str,
        llm_client,
        tool_registry: ToolRegistry,
        session_manager: SessionManager,
        max_iterations: int = 15,
        system_prompt: Optional[str] = None
    ):
        """
        初始化 Code Understanding Agent
        
        Args:
            name: Agent 名称
            llm_client: LLM 客户端实例
            tool_registry: 工具注册表
            session_manager: 会话管理器
            max_iterations: 最大工具调用迭代次数
            system_prompt: 系统提示词（如果不提供则使用默认）
        """
        # 默认系统提示词
        default_system_prompt = """你是一个专业的代码理解助手，专门帮助开发者理解和分析代码项目。

你的核心能力：
1. **项目分析**：快速分析项目结构，理解技术架构和组织方式
2. **代码导航**：帮助用户找到特定功能、类、函数的实现位置
3. **技术解读**：解释代码的工作原理、设计模式和最佳实践
4. **问题诊断**：帮助定位和分析代码问题
5. **改进建议**：提供代码优化和重构建议

你可以使用的工具：
- analyze_project_structure: 分析项目目录结构
- search_code: 在代码中搜索特定文本或模式
- find_files: 根据文件名查找文件
- analyze_file: 分析单个文件的结构（类、函数等）
- read_file: 读取文件内容
- list_directory: 列出目录内容

工作方式：
1. 先通过项目结构分析了解整体架构
2. 根据用户问题，使用搜索和分析工具定位相关代码
3. 深入阅读和分析具体代码实现
4. 给出清晰、准确的答案和建议

注意事项：
- 优先使用工具获取准确信息，而不是猜测
- 回答要具体，引用文件名和代码位置
- 对于复杂问题，采用分步分析的方式
- 保持专业和简洁的沟通风格"""

        super().__init__(
            name=name,
            agent_type="code_understanding",
            llm_client=llm_client,
            tool_registry=tool_registry,
            session_manager=session_manager,
            system_prompt=system_prompt or default_system_prompt,
            max_iterations=max_iterations
        )
        
        # 初始化记忆功能
        self._init_memory(max_short_term_memories=50, max_long_term_memories=100)
        
        self.max_iterations = max_iterations
        
        logger.info(f"CodeUnderstandingAgent '{self.name}' 已初始化")
        tool_names = [tool.name for tool in self.tool_registry.get_all_tools()]
        logger.debug(f"可用工具 ({len(tool_names)}): {', '.join(tool_names)}")
        logger.debug(f"最大迭代次数: {self.max_iterations}")
    
    async def run(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]]
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
                has_tool_calls = await self._process_iteration(
                    websocket, session_id, messages, message_id, iteration
                )
                
                # 如果没有工具调用，说明已得到最终答案
                if not has_tool_calls:
                    logger.info(f"[{self.name}] 已获得最终答案，结束迭代 (session: {session_id})")
                    break
            
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
    
    async def _process_iteration(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        message_id: str,
        iteration: int
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
            
            return True  # 需要继续迭代
        else:
            # 无工具调用：保存最终答案
            messages.append({
                "role": "assistant",
                "content": content_buffer
            })
            
            return False  # 结束迭代
    
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
            "specialization": "代码理解与分析"
        })
        return base_info
