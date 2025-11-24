"""Tool registry for managing and executing tools."""

import json
from typing import Dict, List, Any, Optional, Callable
from .base import BaseTool
from utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """Registry for managing tools and executing tool calls."""
    
    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._progress_callback: Optional[Callable] = None
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
        logger.debug(f"工具已注册: {tool.name}")
    
    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name in self._tools:
            self._tools.pop(tool_name, None)
            logger.debug(f"工具已注销: {tool_name}")
        else:
            logger.warning(f"尝试注销不存在的工具: {tool_name}")
    
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
    
    def set_progress_callback(self, callback: Optional[Callable] = None) -> None:
        """
        设置进度回调函数
        
        Args:
            callback: 进度回调函数，接收 (tool_name, status, progress) 参数
        """
        self._progress_callback = callback
    
    async def execute_tool(self, tool_name: str, arguments_str: str) -> str:
        """
        Execute a tool with given arguments.
        
        Args:
            tool_name: Name of tool to execute
            arguments_str: JSON string of tool arguments
            
        Returns:
            Tool execution result
        """
        # Get tool
        tool = self.get_tool(tool_name)
        if not tool:
            error_msg = f"错误：未知工具 {tool_name}"
            logger.error(error_msg)
            return error_msg
        
        # Parse arguments
        try:
            arguments = json.loads(arguments_str)
            logger.debug(f"执行工具: {tool_name}, 参数: {arguments}")
        except json.JSONDecodeError as e:
            error_msg = f"错误：参数必须是有效的 JSON 格式。\n输入: {arguments_str}\n错误: {str(e)}"
            logger.error(f"工具 {tool_name} 参数解析失败: {e}")
            return error_msg
        
        # 通知工具执行开始
        if self._progress_callback:
            await self._progress_callback(tool_name, "executing", arguments)
        
        # Execute tool
        try:
            # 如果工具支持进度回调，传递给它
            if hasattr(tool, 'set_progress_callback'):
                tool.set_progress_callback(self._progress_callback)
            
            result = await tool.execute(**arguments)
            logger.info(f"工具执行成功: {tool_name} -> {result[:100] if len(result) > 100 else result}")
            
            # 通知工具执行完成
            if self._progress_callback:
                await self._progress_callback(tool_name, "completed", None)
            
            return result
        except TypeError as e:
            error_msg = f"错误：参数不匹配 - {str(e)}"
            logger.error(f"工具 {tool_name} 参数不匹配: {e}")
            
            if self._progress_callback:
                await self._progress_callback(tool_name, "error", str(e))
            
            return error_msg
        except Exception as e:
            error_msg = f"错误：工具执行失败 - {str(e)}"
            logger.error(f"工具 {tool_name} 执行失败: {e}", exc_info=True)
            
            if self._progress_callback:
                await self._progress_callback(tool_name, "error", str(e))
            
            return error_msg
    
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
