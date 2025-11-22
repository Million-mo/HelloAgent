"""Tool registry for managing and executing tools."""

import json
from typing import Dict, List, Any, Optional
from .base import BaseTool


class ToolRegistry:
    """Registry for managing tools and executing tool calls."""
    
    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
    
    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
        """
        self._tools.pop(tool_name, None)
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Name of tool to get
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """
        Get all registered tools.
        
        Returns:
            List of all registered tools
        """
        return list(self._tools.values())
    
    def get_tools_definitions(self) -> List[Dict[str, Any]]:
        """
        Get all tools in OpenAI function calling format.
        
        Returns:
            List of tool definitions
        """
        return [tool.to_openai_format() for tool in self._tools.values()]
    
    async def execute_tool(self, tool_name: str, arguments_str: str) -> str:
        """
        Execute a tool with given arguments.
        
        Args:
            tool_name: Name of tool to execute
            arguments_str: JSON string of tool arguments
            
        Returns:
            Tool execution result
        """
        # Parse arguments
        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            return f"错误：无法解析参数: {arguments_str}"
        
        # Get tool
        tool = self.get_tool(tool_name)
        if not tool:
            return f"错误：未知工具 {tool_name}"
        
        # Execute tool
        try:
            result = await tool.execute(**arguments)
            return result
        except TypeError as e:
            return f"错误：参数不匹配 - {str(e)}"
        except Exception as e:
            return f"错误：工具执行失败 - {str(e)}"
    
    def tool_exists(self, tool_name: str) -> bool:
        """
        Check if a tool exists.
        
        Args:
            tool_name: Name of tool to check
            
        Returns:
            True if tool exists
        """
        return tool_name in self._tools
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
