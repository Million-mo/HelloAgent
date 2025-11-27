"""基础Agent抽象类 - 定义Agent接口规范."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from fastapi import WebSocket

from ..tools.registry import ToolRegistry
from ..chat.session import SessionManager


class BaseAgent(ABC):
    """
    Agent 基类，定义所有Agent必须实现的接口
    
    所有自定义Agent都应该继承此类并实现核心方法
    """
    
    def __init__(
        self,
        name: str,
        agent_type: str,
        llm_client,
        tool_registry: ToolRegistry,
        session_manager: SessionManager,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """
        初始化基础Agent
        
        Args:
            name: Agent名称
            agent_type: Agent类型标识
            llm_client: LLM客户端
            tool_registry: 工具注册表
            session_manager: 会话管理器
            system_prompt: 系统提示词
            **kwargs: 其他参数
        """
        self.name = name
        self.agent_type = agent_type
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.session_manager = session_manager
        self.system_prompt = system_prompt
        self.config = kwargs
    
    @abstractmethod
    async def run(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """
        执行Agent主逻辑（必须实现）
        
        Args:
            websocket: WebSocket连接
            session_id: 会话ID
            user_input: 用户输入
            messages: 对话历史
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "name": self.name,
            "type": self.agent_type,
            "model": self.llm_client.model,
            "system_prompt": self.system_prompt[:100] + "..." if self.system_prompt and len(self.system_prompt) > 100 else self.system_prompt,
            "config": self.config
        }
    
    def get_available_tools(self) -> List[str]:
        """
        获取可用工具列表
        
        返回的是该 Agent 实例所有可使用的工具。
        对于使用工具子集的 Agent，此方法仅返回该子集中的工具。
        
        Returns:
            工具名称列表
        """
        return [tool.name for tool in self.tool_registry.get_all_tools()]
    
    def _ensure_system_prompt(self, messages: List[Dict[str, Any]]) -> None:
        """
        确保消息历史中有system_prompt
        
        如果消息列表为空或第一条不是system消息，则添加Agent的system_prompt
        
        Args:
            messages: 对话历史
        """
        if not messages or messages[0].get("role") != "system":
            # 在开头插入system_prompt
            messages.insert(0, {
                "role": "system",
                "content": self.system_prompt or "你是一个乐于助人的AI助手。"
            })
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', type='{self.agent_type}')>"
