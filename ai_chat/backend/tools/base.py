"""Base class for tools."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for function calling."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Tool parameters schema (JSON Schema format)."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """
        Execute the tool with given arguments.
        
        Args:
            **kwargs: Tool arguments
            
        Returns:
            Tool execution result as string
        """
        pass
    
    def to_openai_format(self) -> Dict[str, Any]:
        """
        Convert tool to OpenAI function calling format.
        
        Returns:
            Tool definition in OpenAI format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
