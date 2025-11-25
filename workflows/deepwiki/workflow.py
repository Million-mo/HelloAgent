"""DeepWiki Workflow - 工作流编排."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../ai_chat/backend'))

from typing import Optional
from fastapi import WebSocket

from tools.registry import ToolRegistry
from chat.session import SessionManager
from llm.client import LLMClient

from .agents.deepwiki_agent import DeepWikiAgent
from .tools.search_tool import SearchTool
from .tools.scraper_tool import ScraperTool


class DeepWikiWorkflow:
    """
    DeepWiki 工作流
    
    负责初始化和编排整个 DeepWiki 应用的组件。
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        session_manager: Optional[SessionManager] = None
    ):
        """
        初始化工作流.
        
        Args:
            llm_client: LLM 客户端（如果为 None，会创建默认客户端）
            session_manager: 会话管理器（如果为 None，会创建新实例）
        """
        # 初始化 LLM 客户端
        self.llm_client = llm_client or LLMClient()
        
        # 初始化会话管理器
        self.session_manager = session_manager or SessionManager()
        
        # 初始化工具注册表
        self.tool_registry = ToolRegistry()
        
        # 注册 DeepWiki 专用工具
        self._register_tools()
        
        # 初始化 Agent
        self.agent = DeepWikiAgent(
            name="DeepWiki",
            llm_client=self.llm_client,
            tool_registry=self.tool_registry,
            session_manager=self.session_manager,
            max_iterations=15
        )
    
    def _register_tools(self) -> None:
        """注册工作流所需的工具."""
        # 注册搜索工具
        self.tool_registry.register(SearchTool())
        
        # 注册网页抓取工具
        self.tool_registry.register(ScraperTool())
        
        # 可以继续注册更多工具...
    
    async def run(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str
    ) -> None:
        """
        运行工作流.
        
        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
            user_input: 用户输入
        """
        # 获取或创建会话历史
        messages = self.session_manager.get_history(session_id)
        
        # 执行 Agent
        await self.agent.run(
            websocket=websocket,
            session_id=session_id,
            user_input=user_input,
            messages=messages
        )
    
    def get_info(self) -> dict:
        """获取工作流信息."""
        return {
            "workflow_name": "DeepWiki",
            "description": "深度知识探索工作流",
            "agent": self.agent.get_info(),
            "tools": [tool.name for tool in self.tool_registry.get_all_tools()],
            "tool_count": len(self.tool_registry.get_all_tools())
        }
