"""Memory Mixin - 为Agent提供可复用的记忆功能."""

from typing import Dict, List, Any, Optional
from fastapi import WebSocket

from .memory import MemoryManager, Memory, MemoryType, MemoryImportance
from utils.logger import get_logger

logger = get_logger(__name__)


class MemoryMixin:
    """
    记忆功能Mixin类
    
    为Agent提供完整的记忆管理能力，包括：
    1. 记忆存储和检索
    2. 相关记忆自动关联
    3. 记忆上下文生成
    4. 对话记忆自动保存
    
    使用方法：
        class MyAgent(MemoryMixin, BaseAgent):
            def __init__(self, ...):
                super().__init__(...)
                self._init_memory(max_short_term=50, max_long_term=100)
    """
    
    def _init_memory(
        self,
        max_short_term_memories: int = 50,
        max_long_term_memories: int = 100
    ) -> None:
        """
        初始化记忆功能
        
        Args:
            max_short_term_memories: 短期记忆最大数量
            max_long_term_memories: 长期记忆最大数量
        """
        self._session_memories: Dict[str, MemoryManager] = {}
        self.max_short_term_memories = max_short_term_memories
        self.max_long_term_memories = max_long_term_memories
        
        logger.debug(f"[{getattr(self, 'name', 'Agent')}] 记忆功能已初始化")
    
    def _get_memory_manager(self, session_id: str) -> MemoryManager:
        """
        获取会话的记忆管理器
        
        Args:
            session_id: 会话ID
        
        Returns:
            MemoryManager实例
        """
        if session_id not in self._session_memories:
            self._session_memories[session_id] = MemoryManager(
                max_short_term=self.max_short_term_memories,
                max_long_term=self.max_long_term_memories
            )
            logger.debug(f"为会话 {session_id} 创建新的MemoryManager")
        return self._session_memories[session_id]
    
    async def _retrieve_relevant_memories(
        self,
        user_input: str,
        memory_manager: MemoryManager,
        max_memories: int = 5
    ) -> List[Memory]:
        """
        检索与用户输入相关的记忆
        
        Args:
            user_input: 用户输入
            memory_manager: 记忆管理器
            max_memories: 最大返回数量
        
        Returns:
            相关记忆列表
        """
        # 简单实现：关键词搜索
        # 可以扩展为更复杂的语义搜索或向量检索
        keywords = user_input.split()[:5]  # 取前5个词作为关键词
        
        relevant = []
        for keyword in keywords:
            if len(keyword) > 2:  # 忽略太短的词
                found = memory_manager.search_memories(keyword)
                relevant.extend(found)
        
        # 去重并按重要性排序
        unique_memories = {m.id: m for m in relevant}.values()
        
        importance_order = {
            MemoryImportance.CRITICAL: 3,
            MemoryImportance.HIGH: 2,
            MemoryImportance.MEDIUM: 1,
            MemoryImportance.LOW: 0
        }
        
        sorted_memories = sorted(
            unique_memories,
            key=lambda m: (importance_order[m.importance], m.timestamp),
            reverse=True
        )
        
        # 返回最相关的记忆
        return sorted_memories[:max_memories]
    
    def _format_memories_for_context(self, memories: List[Memory]) -> str:
        """
        格式化记忆为上下文文本
        
        Args:
            memories: 记忆列表
        
        Returns:
            格式化的上下文字符串
        """
        if not memories:
            return ""
        
        lines = ["**💭 相关记忆：**"]
        for memory in memories:
            lines.append(f"- {memory.content}")
        
        return "\n".join(lines)
    
    async def _save_conversation_memory(
        self,
        user_input: str,
        assistant_response: str,
        memory_manager: MemoryManager
    ) -> None:
        """
        保存对话为短期记忆
        
        Args:
            user_input: 用户输入
            assistant_response: 助手回复
            memory_manager: 记忆管理器
        """
        # 保存用户输入为短期记忆
        memory_manager.add_memory(
            content=f"用户说: {user_input}",
            memory_type=MemoryType.SHORT_TERM,
            importance=MemoryImportance.LOW,
            tags=["对话历史"]
        )
        
        # 如果助手回复中包含实质内容，也保存
        if len(assistant_response) > 20:
            memory_manager.add_memory(
                content=f"我回复: {assistant_response[:200]}...",  # 保存摘要
                memory_type=MemoryType.SHORT_TERM,
                importance=MemoryImportance.LOW,
                tags=["对话历史"]
            )
        
        logger.debug(f"[{getattr(self, 'name', 'Agent')}] 保存了对话记忆")
    
    async def _save_tool_call_memory(
        self,
        tool_name: str,
        tool_result: str,
        memory_manager: MemoryManager
    ) -> None:
        """
        保存工具调用结果为工作记忆
        
        Args:
            tool_name: 工具名称
            tool_result: 工具执行结果
            memory_manager: 记忆管理器
        """
        memory_manager.add_memory(
            content=f"使用工具 {tool_name} 获得结果: {tool_result[:100]}...",
            memory_type=MemoryType.WORKING,
            importance=MemoryImportance.LOW,
            tags=["工具调用", tool_name],
            metadata={"tool_name": tool_name}
        )
    
    # 公开API方法
    
    def add_long_term_memory(
        self,
        session_id: str,
        content: str,
        importance: MemoryImportance = MemoryImportance.HIGH,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Memory:
        """
        手动添加长期记忆
        
        Args:
            session_id: 会话ID
            content: 记忆内容
            importance: 重要性级别
            tags: 标签列表
            metadata: 元数据
        
        Returns:
            创建的Memory对象
        """
        memory_manager = self._get_memory_manager(session_id)
        return memory_manager.add_memory(
            content=content,
            memory_type=MemoryType.LONG_TERM,
            importance=importance,
            tags=tags or [],
            metadata=metadata or {}
        )
    
    def get_memory_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        获取记忆统计信息
        
        Args:
            session_id: 会话ID
        
        Returns:
            统计信息字典
        """
        memory_manager = self._get_memory_manager(session_id)
        return memory_manager.get_statistics()
    
    def get_all_memories(self, session_id: str) -> List[Memory]:
        """
        获取所有记忆
        
        Args:
            session_id: 会话ID
        
        Returns:
            记忆列表
        """
        memory_manager = self._get_memory_manager(session_id)
        return list(memory_manager.memories.values())
    
    def get_memories_by_type(
        self,
        session_id: str,
        memory_type: MemoryType
    ) -> List[Memory]:
        """
        按类型获取记忆
        
        Args:
            session_id: 会话ID
            memory_type: 记忆类型
        
        Returns:
            指定类型的记忆列表
        """
        memory_manager = self._get_memory_manager(session_id)
        return memory_manager.get_memories_by_type(memory_type)
    
    def search_memories(
        self,
        session_id: str,
        keyword: str
    ) -> List[Memory]:
        """
        搜索包含关键词的记忆
        
        Args:
            session_id: 会话ID
            keyword: 搜索关键词
        
        Returns:
            匹配的记忆列表
        """
        memory_manager = self._get_memory_manager(session_id)
        return memory_manager.search_memories(keyword)
    
    def clear_session_memories(
        self,
        session_id: str,
        memory_type: MemoryType = None
    ) -> None:
        """
        清空会话记忆
        
        Args:
            session_id: 会话ID
            memory_type: 记忆类型（可选，为None则清空所有）
        """
        memory_manager = self._get_memory_manager(session_id)
        memory_manager.clear_memories(memory_type)
        logger.info(f"[{getattr(self, 'name', 'Agent')}] 清空会话 {session_id} 的记忆")
    
    def export_memories(self, session_id: str) -> str:
        """
        导出记忆为JSON字符串
        
        Args:
            session_id: 会话ID
        
        Returns:
            JSON格式的记忆数据
        """
        memory_manager = self._get_memory_manager(session_id)
        return memory_manager.export_memories()
    
    def import_memories(self, session_id: str, json_str: str) -> int:
        """
        从JSON字符串导入记忆
        
        Args:
            session_id: 会话ID
            json_str: JSON字符串
        
        Returns:
            导入的记忆数量
        """
        memory_manager = self._get_memory_manager(session_id)
        return memory_manager.import_memories(json_str)
