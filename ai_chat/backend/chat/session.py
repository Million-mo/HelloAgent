"""Session management for chat conversations."""

from typing import Dict, List, Any
import asyncio
from utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages chat sessions, message history, and task control."""
    
    def __init__(self):
        """
        Initialize session manager.
        
        Note: SessionManager 不册管理 system_prompt，
        由各个Agent在运行时动态注入自己的 system_prompt
        """
        # 会话消息历史
        self._sessions: Dict[str, List[Dict[str, Any]]] = {}
        
        # 会话级流式任务与控制状态
        self._session_tasks: Dict[str, asyncio.Task] = {}
        self._session_cancel_flags: Dict[str, bool] = {}
        self._session_current_message: Dict[str, str] = {}
    
    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get or initialize messages for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of message dictionaries
        """
        if session_id not in self._sessions:
            # 初始化为空列表，由Agent动态注入system_prompt
            self._sessions[session_id] = []
        return self._sessions[session_id]
    
    def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """
        Add a message to session history.
        
        Args:
            session_id: Session identifier
            message: Message dictionary
        """
        messages = self.get_messages(session_id)
        messages.append(message)
    
    def set_task(self, session_id: str, task: asyncio.Task) -> None:
        """
        Set the current task for a session.
        
        Args:
            session_id: Session identifier
            task: Asyncio task
        """
        self._session_tasks[session_id] = task
    
    def get_task(self, session_id: str) -> asyncio.Task | None:
        """
        Get the current task for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Current task or None
        """
        return self._session_tasks.get(session_id)
    
    def remove_task(self, session_id: str) -> None:
        """
        Remove task from session.
        
        Args:
            session_id: Session identifier
        """
        self._session_tasks.pop(session_id, None)
    
    def set_cancel_flag(self, session_id: str, flag: bool) -> None:
        """
        Set cancel flag for a session.
        
        Args:
            session_id: Session identifier
            flag: Cancel flag value
        """
        self._session_cancel_flags[session_id] = flag
    
    def get_cancel_flag(self, session_id: str) -> bool:
        """
        Get cancel flag for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Cancel flag value
        """
        return self._session_cancel_flags.get(session_id, False)
    
    def set_current_message(self, session_id: str, message_id: str) -> None:
        """
        Set current message ID for a session.
        
        Args:
            session_id: Session identifier
            message_id: Message identifier
        """
        self._session_current_message[session_id] = message_id
    
    def get_current_message(self, session_id: str) -> str | None:
        """
        Get current message ID for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Message ID or None
        """
        return self._session_current_message.get(session_id)
    
    def remove_current_message(self, session_id: str) -> None:
        """
        Remove current message ID from session.
        
        Args:
            session_id: Session identifier
        """
        self._session_current_message.pop(session_id, None)
    
    def cleanup_session(self, session_id: str) -> None:
        """
        Clean up all session data.
        
        Args:
            session_id: Session identifier
        """
        # 取消正在运行的任务
        task = self.get_task(session_id)
        if task and not task.done():
            task.cancel()
            logger.debug(f"取消会话 {session_id} 的任务")
        
        # 清理所有会话数据
        self._sessions.pop(session_id, None)
        self._session_tasks.pop(session_id, None)
        self._session_cancel_flags.pop(session_id, None)
        self._session_current_message.pop(session_id, None)
        
        logger.info(f"会话 {session_id} 数据已清理")
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if session exists.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session exists
        """
        return session_id in self._sessions
