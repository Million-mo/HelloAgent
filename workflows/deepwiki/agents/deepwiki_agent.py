"""DeepWiki Agent - 专注于深度知识探索的 Agent."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../ai_chat/backend'))

from typing import Dict, List, Any, Optional
from fastapi import WebSocket

from agents.function_call_agent import FunctionCallAgent
from tools.registry import ToolRegistry
from chat.session import SessionManager


class DeepWikiAgent(FunctionCallAgent):
    """
    DeepWiki Agent - 深度知识探索助手
    
    特点:
    1. 基于 Function Call 模式
    2. 集成搜索和网页抓取能力
    3. 支持深度信息挖掘和分析
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
        初始化 DeepWiki Agent.
        
        Args:
            name: Agent 名称
            llm_client: LLM 客户端
            tool_registry: 工具注册表
            session_manager: 会话管理器
            max_iterations: 最大迭代次数（深度探索需要更多迭代）
            system_prompt: 自定义系统提示词
        """
        # 默认的 DeepWiki 系统提示词
        default_prompt = """你是 DeepWiki，一个专注于深度知识探索的 AI 助手。

你的核心能力：
1. 使用搜索工具查找相关信息
2. 使用网页抓取工具深入阅读内容
3. 综合多个来源，提供全面的分析

工作流程：
1. 理解用户的知识需求
2. 搜索相关信息源
3. 深入抓取和分析内容
4. 整合信息，给出深度见解

请始终保持批判性思维，交叉验证信息来源。"""
        
        super().__init__(
            name=name,
            llm_client=llm_client,
            tool_registry=tool_registry,
            session_manager=session_manager,
            max_iterations=max_iterations,
            system_prompt=system_prompt or default_prompt
        )
    
    def get_info(self) -> Dict[str, Any]:
        """获取 Agent 信息."""
        info = super().get_info()
        info.update({
            "agent_class": "DeepWikiAgent",
            "description": "深度知识探索助手",
            "capabilities": [
                "网络搜索",
                "网页内容抓取",
                "信息综合分析"
            ]
        })
        return info
