"""Terminal command execution tool."""

import asyncio
import subprocess
from typing import Dict, Any
from .base import BaseTool


class TerminalTool(BaseTool):
    """Tool for executing terminal commands."""
    
    def __init__(self, timeout: int = 30):
        """
        Initialize terminal tool.
        
        Args:
            timeout: Command execution timeout in seconds
        """
        self.timeout = timeout
    
    @property
    def name(self) -> str:
        return "execute_command"
    
    @property
    def description(self) -> str:
        return "Execute a shell command in the terminal. Use this to run commands, check system info, list files, etc."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute, e.g. 'ls -la', 'pwd', 'echo hello'"
                }
            },
            "required": ["command"]
        }
    
    async def execute(self, command: str, **kwargs) -> str:
        """
        Execute a shell command.
        
        Args:
            command: Command to execute
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Command output or error message
        """
        # 安全检查：禁止危险命令
        dangerous_commands = ['rm -rf', 'mkfs', 'dd if=', ':(){:|:&};:', 'format']
        if any(dangerous in command.lower() for dangerous in dangerous_commands):
            return f"错误：不允许执行危险命令 '{command}'"
        
        try:
            # 使用 asyncio.subprocess 执行命令
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            
            # 等待命令完成，带超时
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return f"错误：命令执行超时（>{self.timeout}秒）"
            
            # 解码输出
            stdout_text = stdout.decode('utf-8', errors='replace').strip()
            stderr_text = stderr.decode('utf-8', errors='replace').strip()
            
            # 构建返回结果
            if process.returncode == 0:
                result = f"命令执行成功：\n{stdout_text}" if stdout_text else "命令执行成功（无输出）"
            else:
                result = f"命令执行失败（退出码：{process.returncode}）：\n{stderr_text if stderr_text else stdout_text}"
            
            return result
            
        except Exception as e:
            return f"错误：执行命令时发生异常 - {str(e)}"
