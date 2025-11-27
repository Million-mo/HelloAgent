"""AI Chat - A multi-agent system with LLM integration."""

__version__ = "0.1.0"
__author__ = "AI Chat Team"

# 导出主要模块
from . import agents
from . import chat
from . import llm
from . import tools
from . import utils
from . import config

__all__ = [
    "agents",
    "chat",
    "llm",
    "tools",
    "utils",
    "config",
]
