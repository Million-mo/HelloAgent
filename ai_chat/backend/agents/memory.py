"""Memory Management Module - Agent记忆功能模块."""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from utils.logger import get_logger

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
        max_memories: int = 10
    ) -> str:
        """
        生成记忆上下文文本，供LLM使用
        
        Args:
            include_types: 包含的记忆类型列表
            max_memories: 最大记忆数量
        
        Returns:
            格式化的记忆上下文字符串
        """
        # 收集要包含的记忆
        memories = []
        
        if include_types:
            for mem_type in include_types:
                memories.extend(self.get_memories_by_type(mem_type))
        else:
            memories = list(self.memories.values())
        
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
        
        if not memories:
            return ""
        
        # 生成格式化文本
        context_lines = ["## 相关记忆信息\n"]
        
        for memory in memories:
            context_lines.append(f"- [{memory.memory_type.value}] {memory.content}")
            if memory.tags:
                context_lines.append(f"  标签: {', '.join(memory.tags)}")
        
        return "\n".join(context_lines)
    
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
