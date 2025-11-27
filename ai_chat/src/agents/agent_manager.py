"""Agent管理器 - 管理多Agent实例及其协作."""

from typing import Dict, List, Any, Optional
from fastapi import WebSocket

from .base_agent import BaseAgent
from ..chat.session import SessionManager
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AgentManager:
    """
    Agent 管理器
    
    功能:
    1. 注册和管理多个Agent实例
    2. 根据任务类型或用户指定选择合适的Agent
    3. 支持Agent之间的切换和协作
    4. 维护Agent使用历史
    """
    
    def __init__(self, session_manager: SessionManager):
        """
        初始化Agent管理器
        
        Args:
            session_manager: 会话管理器
        """
        self.session_manager = session_manager
        self._agents: Dict[str, BaseAgent] = {}
        self._default_agent: Optional[str] = None
        self._session_agents: Dict[str, str] = {}  # session_id -> agent_name
        
    def register_agent(self, agent: BaseAgent, is_default: bool = False) -> None:
        """
        注册Agent
        
        Args:
            agent: Agent实例
            is_default: 是否设为默认Agent
        """
        self._agents[agent.name] = agent
        logger.info(f"Agent '{agent.name}' (类型: {agent.agent_type}) 已注册")
        
        if is_default or self._default_agent is None:
            self._default_agent = agent.name
            logger.info(f"Agent '{agent.name}' 设为默认Agent")
    
    def unregister_agent(self, agent_name: str) -> bool:
        """
        注销Agent
        
        Args:
            agent_name: Agent名称
            
        Returns:
            是否成功注销
        """
        if agent_name in self._agents:
            del self._agents[agent_name]
            if self._default_agent == agent_name:
                self._default_agent = next(iter(self._agents.keys()), None)
            logger.info(f"Agent '{agent_name}' 已注销")
            return True
        logger.warning(f"尝试注销不存在的Agent: {agent_name}")
        return False
    
    def get_agent(self, agent_name: Optional[str] = None) -> Optional[BaseAgent]:
        """
        获取Agent实例
        
        Args:
            agent_name: Agent名称，None则返回默认Agent
            
        Returns:
            Agent实例
        """
        if agent_name is None:
            agent_name = self._default_agent
        return self._agents.get(agent_name)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """
        获取所有Agent信息列表
        
        Returns:
            Agent信息列表
        """
        return [
            {
                **agent.get_info(),
                "is_default": agent.name == self._default_agent,
                "available_tools": agent.get_available_tools()
            }
            for agent in self._agents.values()
        ]
    
    def set_session_agent(self, session_id: str, agent_name: str) -> bool:
        """
        为会话指定Agent
        
        Args:
            session_id: 会话ID
            agent_name: Agent名称
            
        Returns:
            是否设置成功
        """
        if agent_name in self._agents:
            self._session_agents[session_id] = agent_name
            logger.info(f"会话 {session_id} 切换到 Agent '{agent_name}'")
            return True
        logger.warning(f"会话 {session_id} 尝试切换到不存在的Agent: {agent_name}")
        return False
    
    def get_session_agent(self, session_id: str) -> Optional[BaseAgent]:
        """
        获取会话使用的Agent
        
        Args:
            session_id: 会话ID
            
        Returns:
            Agent实例
        """
        agent_name = self._session_agents.get(session_id, self._default_agent)
        return self._agents.get(agent_name)
    
    async def run(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]],
        agent_name: Optional[str] = None
    ) -> None:
        """
        执行Agent任务
        
        Args:
            websocket: WebSocket连接
            session_id: 会话ID
            user_input: 用户输入
            messages: 对话历史
            agent_name: 指定Agent名称（可选）
        """
        # 选择Agent
        if agent_name:
            agent = self.get_agent(agent_name)
        else:
            agent = self.get_session_agent(session_id)
        
        if not agent:
            error_msg = f"未找到可用的Agent"
            logger.error(error_msg)
            await websocket.send_json({
                "type": "error",
                "message": error_msg
            })
            return
        
        logger.debug(f"使用 Agent '{agent.name}' 处理请求 (session: {session_id})")
        
        # 执行Agent
        await agent.run(websocket, session_id, user_input, messages)
    
    def switch_agent(
        self,
        session_id: str,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        切换会话使用的Agent
        
        Args:
            session_id: 会话ID
            agent_name: 目标Agent名称
            
        Returns:
            切换结果信息
        """
        if agent_name not in self._agents:
            logger.warning(f"Agent '{agent_name}' 不存在")
            return {
                "success": False,
                "message": f"Agent '{agent_name}' 不存在",
                "available_agents": list(self._agents.keys())
            }
        
        old_agent_name = self._session_agents.get(session_id, self._default_agent)
        self._session_agents[session_id] = agent_name
        
        logger.info(f"会话 {session_id} 从 '{old_agent_name}' 切换到 '{agent_name}'")
        
        return {
            "success": True,
            "message": f"已从 '{old_agent_name}' 切换到 '{agent_name}'",
            "old_agent": old_agent_name,
            "new_agent": agent_name,
            "agent_info": self._agents[agent_name].get_info()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取管理器统计信息
        
        Returns:
            统计信息
        """
        return {
            "total_agents": len(self._agents),
            "default_agent": self._default_agent,
            "active_sessions": len(self._session_agents),
            "agents": list(self._agents.keys())
        }
