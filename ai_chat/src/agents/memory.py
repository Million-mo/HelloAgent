"""Memory Management Module - Agent记忆功能模块.

设计原则（新架构）：
- MemoryManager作为独立的服务对象，可被多个Agent共享
- MemoryService统一管理全局和会话级记忆
- Agent通过依赖注入接收MemoryManager，而非内部创建
- 支持灵活的记忆共享策略：全局共享/会话独立/Agent独立
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from ..utils.logger import get_logger

logger = get_logger(__name__)


class MemoryType(str, Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"      # 短期记忆：当前会话的对话历史
    LONG_TERM = "long_term"        # 长期记忆：跨会话的关键信息
    WORKING = "working"            # 工作记忆：任务执行中的中间结果


class MemoryImportance(str, Enum):
    """记忆重要性枚举"""
    LOW = "low"           # 低重要性：一般性信息
    MEDIUM = "medium"     # 中等重要性：有用的信息
    HIGH = "high"         # 高重要性：关键信息
    CRITICAL = "critical" # 极高重要性：必须记住的信息


@dataclass
class Memory:
    """
    单条记忆数据模型
    
    Attributes:
        id: 记忆唯一标识
        content: 记忆内容
        memory_type: 记忆类型
        importance: 重要性级别
        timestamp: 创建时间戳
        metadata: 附加元数据（如来源、关联任务等）
        tags: 标签列表，便于检索
    """
    id: str
    content: str
    memory_type: MemoryType
    importance: MemoryImportance = MemoryImportance.MEDIUM
    timestamp: str = None
    metadata: Dict[str, Any] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "importance": self.importance.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """从字典创建Memory对象"""
        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            importance=MemoryImportance(data.get("importance", "medium")),
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", [])
        )


class MemoryManager:
    """
    记忆管理器 - 负责存储、检索和管理Agent的记忆
    
    功能:
    1. 记忆存储：添加、更新、删除记忆
    2. 记忆检索：按类型、标签、重要性等条件查询
    3. 记忆整理：自动清理不重要的旧记忆
    4. 上下文生成：为LLM生成记忆相关的上下文
    """
    
    def __init__(self, max_short_term: int = 50, max_long_term: int = 100):
        """
        初始化记忆管理器
        
        Args:
            max_short_term: 短期记忆最大数量
            max_long_term: 长期记忆最大数量
        """
        self.memories: Dict[str, Memory] = {}
        self.max_short_term = max_short_term
        self.max_long_term = max_long_term
        
        logger.info(f"MemoryManager已初始化 (短期记忆上限: {max_short_term}, 长期记忆上限: {max_long_term})")
    
    def add_memory(
        self,
        content: str,
        memory_type: MemoryType,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        memory_id: str = None
    ) -> Memory:
        """
        添加新记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性
            tags: 标签列表
            metadata: 元数据
            memory_id: 记忆ID（可选，默认自动生成）
        
        Returns:
            创建的Memory对象
        """
        if memory_id is None:
            memory_id = f"mem_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self.memories[memory_id] = memory
        logger.debug(f"添加记忆: {memory_id} [{memory_type.value}] {content[:50]}...")
        
        # 自动清理超出限制的记忆
        self._cleanup_old_memories()
        
        return memory
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取指定ID的记忆"""
        return self.memories.get(memory_id)
    
    def get_memories_by_type(self, memory_type: MemoryType) -> List[Memory]:
        """获取指定类型的所有记忆"""
        return [m for m in self.memories.values() if m.memory_type == memory_type]
    
    def get_memories_by_tags(self, tags: List[str]) -> List[Memory]:
        """获取包含指定标签的记忆"""
        result = []
        for memory in self.memories.values():
            if any(tag in memory.tags for tag in tags):
                result.append(memory)
        return result
    
    def get_recent_memories(self, count: int = 10, memory_type: MemoryType = None) -> List[Memory]:
        """
        获取最近的记忆
        
        Args:
            count: 返回数量
            memory_type: 记忆类型过滤（可选）
        
        Returns:
            按时间倒序排列的记忆列表
        """
        memories = list(self.memories.values())
        
        # 按类型过滤
        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]
        
        # 按时间戳排序
        memories.sort(key=lambda m: m.timestamp, reverse=True)
        
        return memories[:count]
    
    def get_important_memories(self, min_importance: MemoryImportance = MemoryImportance.HIGH) -> List[Memory]:
        """获取重要的记忆"""
        importance_order = {
            MemoryImportance.LOW: 0,
            MemoryImportance.MEDIUM: 1,
            MemoryImportance.HIGH: 2,
            MemoryImportance.CRITICAL: 3
        }
        
        threshold = importance_order[min_importance]
        result = [
            m for m in self.memories.values()
            if importance_order[m.importance] >= threshold
        ]
        
        # 按重要性和时间排序
        result.sort(key=lambda m: (importance_order[m.importance], m.timestamp), reverse=True)
        return result
    
    def search_memories(self, keyword: str) -> List[Memory]:
        """搜索包含关键词的记忆"""
        result = []
        keyword_lower = keyword.lower()
        
        for memory in self.memories.values():
            # 在内容和标签中搜索
            if keyword_lower in memory.content.lower():
                result.append(memory)
            elif any(keyword_lower in tag.lower() for tag in memory.tags):
                result.append(memory)
        
        # 按时间倒序
        result.sort(key=lambda m: m.timestamp, reverse=True)
        return result
    
    def update_memory(self, memory_id: str, **kwargs) -> bool:
        """
        更新记忆信息
        
        Args:
            memory_id: 记忆ID
            **kwargs: 要更新的字段
        
        Returns:
            更新是否成功
        """
        memory = self.memories.get(memory_id)
        if not memory:
            logger.warning(f"记忆不存在: {memory_id}")
            return False
        
        for key, value in kwargs.items():
            if hasattr(memory, key):
                setattr(memory, key, value)
                logger.debug(f"更新记忆 {memory_id}: {key}={value}")
        
        return True
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除指定记忆"""
        if memory_id in self.memories:
            del self.memories[memory_id]
            logger.debug(f"删除记忆: {memory_id}")
            return True
        return False
    
    def clear_memories(self, memory_type: MemoryType = None) -> None:
        """清空记忆（可按类型清空）"""
        if memory_type:
            to_delete = [m.id for m in self.memories.values() if m.memory_type == memory_type]
            for memory_id in to_delete:
                del self.memories[memory_id]
            logger.info(f"清空{memory_type.value}类型记忆: {len(to_delete)}条")
        else:
            count = len(self.memories)
            self.memories.clear()
            logger.info(f"清空所有记忆: {count}条")
    
    def _cleanup_old_memories(self) -> None:
        """自动清理超出限制的旧记忆"""
        # 清理短期记忆
        short_term = self.get_memories_by_type(MemoryType.SHORT_TERM)
        if len(short_term) > self.max_short_term:
            # 按时间排序，保留最新的
            short_term.sort(key=lambda m: m.timestamp)
            to_delete = short_term[:len(short_term) - self.max_short_term]
            for memory in to_delete:
                del self.memories[memory.id]
            logger.debug(f"清理{len(to_delete)}条旧的短期记忆")
        
        # 清理长期记忆（保留重要的）
        long_term = self.get_memories_by_type(MemoryType.LONG_TERM)
        if len(long_term) > self.max_long_term:
            # 按重要性和时间排序
            importance_order = {
                MemoryImportance.CRITICAL: 3,
                MemoryImportance.HIGH: 2,
                MemoryImportance.MEDIUM: 1,
                MemoryImportance.LOW: 0
            }
            long_term.sort(key=lambda m: (importance_order[m.importance], m.timestamp))
            to_delete = long_term[:len(long_term) - self.max_long_term]
            for memory in to_delete:
                del self.memories[memory.id]
            logger.debug(f"清理{len(to_delete)}条旧的长期记忆")
    
    def generate_memory_context(
        self,
        include_types: List[MemoryType] = None,
        max_memories: int = 10,
        user_input: str = None
    ) -> str:
        """
        生成记忆上下文文本，供LLM使用
        
        Args:
            include_types: 包含的记忆类型列表
            max_memories: 最大记忆数量
            user_input: 用户输入(可选)，用于智能检索
        
        Returns:
            格式化的记忆上下文字符串
        """
        # 收集要包含的记忆
        memories = []
        
        if user_input:
            # 智能检索：基于用户输入检索相关记忆
            memories = self._retrieve_relevant_memories(user_input, max_memories)
        else:
            # 手动检索：按类型获取
            if include_types:
                for mem_type in include_types:
                    memories.extend(self.get_memories_by_type(mem_type))
            else:
                memories = list(self.memories.values())
        
        if not memories:
            return ""
        
        # 按重要性和时间排序
        importance_order = {
            MemoryImportance.CRITICAL: 3,
            MemoryImportance.HIGH: 2,
            MemoryImportance.MEDIUM: 1,
            MemoryImportance.LOW: 0
        }
        memories.sort(key=lambda m: (importance_order[m.importance], m.timestamp), reverse=True)
        
        # 限制数量
        memories = memories[:max_memories]
        
        # 生成格式化文本
        context_lines = ["## 💭 相关记忆信息\n"]
        
        for memory in memories:
            context_lines.append(f"- {memory.content}")
            if memory.tags:
                context_lines.append(f"  标签: {', '.join(memory.tags)}")
        
        return "\n".join(context_lines)
    
    def _retrieve_relevant_memories(
        self,
        user_input: str,
        max_memories: int = 5
    ) -> List[Memory]:
        """
        检索与用户输入相关的记忆
        
        Args:
            user_input: 用户输入
            max_memories: 最大返回数量
        
        Returns:
            相关记忆列表
        """
        # 简单实现：关键词搜索
        keywords = user_input.split()[:5]
        
        relevant = []
        for keyword in keywords:
            if len(keyword) > 2:
                found = self.search_memories(keyword)
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
        
        return sorted_memories[:max_memories]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        total = len(self.memories)
        
        by_type = {}
        for mem_type in MemoryType:
            by_type[mem_type.value] = len(self.get_memories_by_type(mem_type))
        
        by_importance = {}
        for importance in MemoryImportance:
            count = len([m for m in self.memories.values() if m.importance == importance])
            by_importance[importance.value] = count
        
        return {
            "total": total,
            "by_type": by_type,
            "by_importance": by_importance
        }
    
    def export_memories(self) -> str:
        """导出所有记忆为JSON字符串"""
        data = {
            "memories": [m.to_dict() for m in self.memories.values()]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def import_memories(self, json_str: str) -> int:
        """
        从JSON字符串导入记忆
        
        Args:
            json_str: JSON字符串
        
        Returns:
            导入的记忆数量
        """
        try:
            data = json.loads(json_str)
            count = 0
            
            for mem_dict in data.get("memories", []):
                memory = Memory.from_dict(mem_dict)
                self.memories[memory.id] = memory
                count += 1
            
            logger.info(f"成功导入{count}条记忆")
            return count
        except Exception as e:
            logger.error(f"导入记忆失败: {e}", exc_info=True)
            return 0
    
    def __len__(self) -> int:
        """返回记忆总数"""
        return len(self.memories)
    
    def __repr__(self) -> str:
        stats = self.get_statistics()
        return f"<MemoryManager(total={stats['total']}, by_type={stats['by_type']})>"


class MemoryScope(str, Enum):
    """记忆范围枚举"""
    GLOBAL = "global"           # 全局共享：所有Agent和会话共享
    SESSION = "session"         # 会话级：同一会话内的所有Agent共享
    AGENT = "agent"             # Agent独立：某个Agent特有的记忆


class MemoryService:
    """
    记忆服务 - 统一管理全局和会话级记忆
    
    设计特点：
    1. 全局单例：整个应用程序只有一个MemoryService实例
    2. 多级记忆：支持全局/会话/Agent三级记忆管理
    3. 灵活共享：可配置记忆在不同Agent间的共享策略
    4. 生命周期管理：自动清理过期会话的记忆
    
    使用场景：
    - 全局共享知识：用户偏好、系统配置等
    - 会话上下文：当前对话的历史和状态
    - Agent专属记忆：某个Agent特定的工作状态
    """
    
    _instance = None  # 单例实例
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, 
                 global_max_short_term: int = 100,
                 global_max_long_term: int = 200,
                 session_max_short_term: int = 50,
                 session_max_long_term: int = 100,
                 agent_max_short_term: int = 30,
                 agent_max_long_term: int = 50):
        """
        初始化记忆服务
        
        Args:
            global_max_short_term: 全局短期记忆上限
            global_max_long_term: 全局长期记忆上限
            session_max_short_term: 会话短期记忆上限
            session_max_long_term: 会话长期记忆上限
            agent_max_short_term: Agent短期记忆上限
            agent_max_long_term: Agent长期记忆上限
        """
        # 避免重复初始化
        if self._initialized:
            return
        
        self._initialized = True
        
        # 全局记忆管理器（所有Agent和会话共享）
        self.global_memory = MemoryManager(
            max_short_term=global_max_short_term,
            max_long_term=global_max_long_term
        )
        
        # 会话级记忆：{session_id: MemoryManager}
        self._session_memories: Dict[str, MemoryManager] = {}
        
        # Agent独立记忆：{(session_id, agent_name): MemoryManager}
        self._agent_memories: Dict[tuple, MemoryManager] = {}
        
        # 配置参数
        self.session_max_short_term = session_max_short_term
        self.session_max_long_term = session_max_long_term
        self.agent_max_short_term = agent_max_short_term
        self.agent_max_long_term = agent_max_long_term
        
        logger.info("✅ MemoryService已初始化（全局单例）")
    
    def get_memory_manager(
        self, 
        scope: MemoryScope,
        session_id: str = None,
        agent_name: str = None
    ) -> MemoryManager:
        """
        获取记忆管理器
        
        Args:
            scope: 记忆范围
            session_id: 会话 ID（scope=SESSION/AGENT 时必需）
            agent_name: Agent名称（scope=AGENT 时必需）
        
        Returns:
            MemoryManager实例
        """
        if scope == MemoryScope.GLOBAL:
            return self.global_memory
        
        elif scope == MemoryScope.SESSION:
            if not session_id:
                raise ValueError("session_id is required for SESSION scope")
            
            if session_id not in self._session_memories:
                self._session_memories[session_id] = MemoryManager(
                    max_short_term=self.session_max_short_term,
                    max_long_term=self.session_max_long_term
                )
                logger.debug(f"创建会话记忆管理器: {session_id}")
            
            return self._session_memories[session_id]
        
        elif scope == MemoryScope.AGENT:
            if not session_id or not agent_name:
                raise ValueError("session_id and agent_name are required for AGENT scope")
            
            key = (session_id, agent_name)
            if key not in self._agent_memories:
                self._agent_memories[key] = MemoryManager(
                    max_short_term=self.agent_max_short_term,
                    max_long_term=self.agent_max_long_term
                )
                logger.debug(f"创建Agent记忆管理器: {agent_name} @ {session_id}")
            
            return self._agent_memories[key]
        
        else:
            raise ValueError(f"Unknown memory scope: {scope}")
    
    def clear_session_memories(self, session_id: str) -> None:
        """
        清除指定会话的所有记忆
        
        Args:
            session_id: 会话 ID
        """
        # 清除会话级记忆
        if session_id in self._session_memories:
            del self._session_memories[session_id]
            logger.info(f"已清除会话记忆: {session_id}")
        
        # 清除此会话的所有Agent记忆
        keys_to_remove = [k for k in self._agent_memories.keys() if k[0] == session_id]
        for key in keys_to_remove:
            del self._agent_memories[key]
            logger.debug(f"已清除Agent记忆: {key[1]} @ {session_id}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取记忆服务的统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "global_memory": self.global_memory.get_statistics(),
            "session_count": len(self._session_memories),
            "agent_memory_count": len(self._agent_memories),
            "total_sessions": list(self._session_memories.keys())
        }
    
    def reset(self) -> None:
        """重置所有记忆（仅用于测试）"""
        self.global_memory = MemoryManager(
            max_short_term=100,
            max_long_term=200
        )
        self._session_memories.clear()
        self._agent_memories.clear()
        logger.warning("⚠️ MemoryService已重置（所有记忆已清空）")
