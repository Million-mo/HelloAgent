"""Documentation Agent - 专门用于分析代码项目并生成技术文档."""

import asyncio
import uuid
from typing import Dict, List, Any, Optional
from fastapi import WebSocket

from tools.registry import ToolRegistry
from chat.session import SessionManager
from .base_agent import BaseAgent
from .memory import MemoryManager, Memory, MemoryType, MemoryImportance
from utils.logger import get_logger

logger = get_logger(__name__)


class DocumentationAgent(BaseAgent):
    """
    Documentation Agent - 专门用于分析代码项目并生成技术文档
    
    功能特性:
    1. 架构分析：理解项目整体架构设计，识别主要模块及其职责
    2. 数据流分析：分析系统内部的数据流向和处理过程
    3. 功能交互识别：识别各功能模块间的调用关系和交互方式
    4. 用户交互分析：分析系统的用户界面和交互流程
    5. 模块关系映射：梳理模块间的依赖关系和接口连接
    
    文档生成能力:
    - 生成结构化的Markdown文档内容
    - 使用Mermaid图表语法描述架构和流程
    - 提供清晰的架构设计概述
    - 生成数据流图和模块关系图
    
    适用场景:
    - 项目技术文档生成
    - 架构设计文档编写
    - 新人入职文档准备
    - 技术评审文档支持
    """
    
    def __init__(
        self,
        name: str,
        llm_client,
        tool_registry: ToolRegistry,
        session_manager: SessionManager,
        max_iterations: int = 20,
        system_prompt: Optional[str] = None,
        enable_memory: bool = False
    ):
        """
        初始化 Documentation Agent
        
        Args:
            name: Agent 名称
            llm_client: LLM 客户端实例
            tool_registry: 工具注册表
            session_manager: 会话管理器
            max_iterations: 最大工具调用迭代次数
            system_prompt: 系统提示词（如果不提供则使用默认）
        """
        # 默认系统提示词
        default_system_prompt = """你是一个专业的技术文档生成专家，专门帮助开发者分析代码项目并生成高质量的技术文档。

你的核心能力：
1. **架构分析**：深入理解项目架构设计，识别关键模块、组件和它们的职责
2. **数据流分析**：追踪数据在系统中的流动路径，理解数据的产生、处理和消费过程
3. **交互关系识别**：识别模块间的依赖关系、调用关系和接口连接方式
4. **用户交互分析**：理解前端界面设计和用户交互流程（如有前端部分）
5. **文档生成**：将分析结果组织成结构化、易读的技术文档

你可以使用的工具：
- analyze_project_structure: 分析项目目录结构，了解项目组织
- search_code: 搜索特定代码模式（如类定义、函数调用、导入语句）
- find_files: 查找特定类型的文件
- analyze_file: 分析单个文件的结构（类、函数、导入等）
- read_file: 读取文件完整内容进行深入分析
- list_directory: 列出目录内容

分析方法论：
1. **整体架构分析**
   - 使用 analyze_project_structure 了解项目组织
   - 识别主要目录和模块划分（backend/frontend/tools/agents等）
   - 找出配置文件、入口文件和核心模块

2. **模块职责分析**
   - 使用 find_files 和 search_code 定位关键文件
   - 使用 analyze_file 提取类和函数定义
   - 使用 read_file 深入理解具体实现逻辑
   - 总结每个模块的核心职责

3. **数据流追踪**
   - 搜索数据模型定义（class、interface、type等）
   - 追踪数据的创建、传递和转换过程
   - 识别数据存储和持久化机制
   - 分析API接口的请求和响应

4. **交互关系梳理**
   - 搜索导入语句了解模块依赖
   - 查找函数/方法调用关系
   - 识别事件监听和回调机制
   - 分析WebSocket/HTTP等通信方式

5. **前端分析（如适用）**
   - 分析HTML/CSS/JS文件结构
   - 识别UI组件和页面布局
   - 理解用户交互事件处理
   - 分析前后端数据交互

文档生成规范：
1. **使用Markdown格式**，包含清晰的标题层级
2. **使用Mermaid图表**描述架构、流程和关系：
   - 架构图：`graph TD` 或 `graph LR`
   - 流程图：`sequenceDiagram`
   - 类图：`classDiagram`
   - 状态图：`stateDiagram-v2`
3. **结构化组织**：
   - 概述：项目简介和核心功能
   - 架构设计：整体架构和技术栈
   - 模块说明：各模块职责和功能
   - 数据流：数据流向和处理流程
   - 接口设计：API和模块接口
   - 部署运行：如何启动和使用
4. **代码引用**：引用具体文件名和关键代码片段
5. **图文并茂**：文字描述 + Mermaid图表

注意事项：
- 必须使用工具实际分析代码，不要凭空假设
- 文档内容要准确反映实际代码结构
- 对于复杂项目，采用分步分析策略
- 生成的文档要清晰易懂，适合技术和非技术读者
- 在对话中直接输出Markdown格式的文档内容
- 不要创建文件，只在对话中生成文档内容供用户复制使用

工作流程示例：
用户："请为这个项目生成架构文档"
→ 1. 使用 analyze_project_structure 分析整体结构
→ 2. 使用 find_files 找到入口文件和配置文件
→ 3. 使用 search_code 查找关键类和函数定义
→ 4. 使用 analyze_file 分析核心文件结构
→ 5. 使用 read_file 深入理解关键实现
→ 6. 组织信息并生成Markdown格式的架构文档
→ 7. 在对话中直接输出完整文档"""

        super().__init__(
            name=name,
            agent_type="documentation",
            llm_client=llm_client,
            tool_registry=tool_registry,
            session_manager=session_manager,
            system_prompt=system_prompt or default_system_prompt,
            max_iterations=max_iterations
        )
        self.max_iterations = max_iterations
        
        # 记忆管理器（可选）
        self.enable_memory = enable_memory
        self._session_memories: Dict[str, MemoryManager] = {}
        self.max_short_term_memories = 50
        self.max_long_term_memories = 100
        
        logger.info(f"DocumentationAgent '{self.name}' 已初始化 (记忆: {'启用' if enable_memory else '禁用'})")
        tool_names = [tool.name for tool in self.tool_registry.get_all_tools()]
        logger.debug(f"可用工具 ({len(tool_names)}): {', '.join(tool_names)}")
        logger.debug(f"最大迭代次数: {self.max_iterations}")
    
    def _get_memory_manager(self, session_id: str) -> Optional[MemoryManager]:
        """获取记忆管理器"""
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
                    logger.info(f"[{self.name}] 已生成文档内容，结束迭代 (session: {session_id})")
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
            "specialization": "技术文档生成与架构分析",
            "memory_enabled": self.enable_memory
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
            logger.warning(f"[{self.name}] 记忆功能未启用")
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
