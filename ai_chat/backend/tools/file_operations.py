"""File operation tools."""

import os
import aiofiles
from pathlib import Path
from typing import Dict, Any
from .base import BaseTool


class ReadFileTool(BaseTool):
    """Tool for reading file contents."""
    
    def __init__(self, base_dir: str = ".", max_size: int = 1024 * 1024):  # 1MB default
        """
        Initialize read file tool.
        
        Args:
            base_dir: Base directory for relative paths
            max_size: Maximum file size to read in bytes
        """
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.max_size = max_size
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "Read contents of a text file. Returns the file content as string."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read (absolute or relative to working directory)"
                }
            },
            "required": ["file_path"]
        }
    
    async def execute(self, file_path: str, **kwargs) -> str:
        """
        Read file contents.
        
        Args:
            file_path: Path to file (absolute or relative to base_dir)
            **kwargs: Additional arguments (ignored)
            
        Returns:
            File contents or error message
        """
        try:
            path = Path(file_path).expanduser()
            
            # 如果是相对路径，则相对于base_dir
            if not path.is_absolute():
                path = self.base_dir / path
            
            path = path.resolve()
            
            # 检查文件是否存在
            if not path.exists():
                return f"错误：文件不存在 '{file_path}'"
            
            if not path.is_file():
                return f"错误：'{file_path}' 不是一个文件"
            
            # 检查文件大小
            file_size = path.stat().st_size
            if file_size > self.max_size:
                return f"错误：文件太大（{file_size} 字节，限制 {self.max_size} 字节）"
            
            # 读取文件
            async with aiofiles.open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = await f.read()
            
            return f"文件 '{file_path}' 内容：\n{content}"
            
        except UnicodeDecodeError:
            return f"错误：文件 '{file_path}' 不是有效的文本文件"
        except PermissionError:
            return f"错误：没有权限读取文件 '{file_path}'"
        except Exception as e:
            return f"错误：读取文件时发生异常 - {str(e)}"


class WriteFileTool(BaseTool):
    """Tool for writing content to files."""
    
    def __init__(self, base_dir: str = "."):
        """
        Initialize write file tool.
        
        Args:
            base_dir: Base directory for relative paths
        """
        self.base_dir = Path(base_dir).expanduser().resolve()
    
    @property
    def name(self) -> str:
        return "write_file"
    
    @property
    def description(self) -> str:
        return "Write content to a file. Creates the file if it doesn't exist, overwrites if it does."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write (absolute or relative to working directory)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["file_path", "content"]
        }
    
    async def execute(self, file_path: str, content: str, **kwargs) -> str:
        """
        Write content to file.
        
        Args:
            file_path: Path to file (absolute or relative to base_dir)
            content: Content to write
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Success or error message
        """
        try:
            path = Path(file_path).expanduser()
            
            # 如果是相对路径，则相对于base_dir
            if not path.is_absolute():
                path = self.base_dir / path
            
            path = path.resolve()
            
            # 创建父目录（如果不存在）
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 直接写入文件（移除进度显示，因为写入速度很快）
            async with aiofiles.open(path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            return f"成功写入文件 '{file_path}'（{len(content)} 字符）"
            
        except PermissionError:
            return f"错误：没有权限写入文件 '{file_path}'"
        except Exception as e:
            return f"错误：写入文件时发生异常 - {str(e)}"


class ListDirectoryTool(BaseTool):
    """Tool for listing directory contents."""
    
    def __init__(self, base_dir: str = "."):
        """
        Initialize list directory tool.
        
        Args:
            base_dir: Base directory for relative paths
        """
        self.base_dir = Path(base_dir).expanduser().resolve()
    
    @property
    def name(self) -> str:
        return "list_directory"
    
    @property
    def description(self) -> str:
        return "List contents of a directory. Shows files and subdirectories."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "Path to the directory to list (absolute or relative to working directory, defaults to working directory if not specified)"
                }
            },
            "required": []
        }
    
    async def execute(self, directory_path: str = ".", **kwargs) -> str:
        """
        List directory contents.
        
        Args:
            directory_path: Path to directory (absolute or relative to base_dir)
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Directory listing or error message
        """
        try:
            path = Path(directory_path).expanduser()
            
            # 如果是相对路径，则相对于base_dir
            if not path.is_absolute():
                path = self.base_dir / path
            
            path = path.resolve()
            
            if not path.exists():
                return f"错误：目录不存在 '{directory_path}'"
            
            if not path.is_dir():
                return f"错误：'{directory_path}' 不是一个目录"
            
            # 获取目录内容
            items = list(path.iterdir())
            
            if not items:
                return f"目录 '{directory_path}' 为空"
            
            # 分类文件和目录
            dirs = [item for item in items if item.is_dir()]
            files = [item for item in items if item.is_file()]
            
            # 排序
            dirs.sort(key=lambda x: x.name.lower())
            files.sort(key=lambda x: x.name.lower())
            
            # 构建输出
            result = f"目录 '{directory_path}' 内容：\n\n"
            
            if dirs:
                result += "📁 目录：\n"
                for d in dirs:
                    result += f"  - {d.name}/\n"
            
            if files:
                result += "\n📄 文件：\n"
                for f in files:
                    size = f.stat().st_size
                    size_str = self._format_size(size)
                    result += f"  - {f.name} ({size_str})\n"
            
            result += f"\n共 {len(dirs)} 个目录，{len(files)} 个文件"
            
            return result
            
        except PermissionError:
            return f"错误：没有权限访问目录 '{directory_path}'"
        except Exception as e:
            return f"错误：列出目录时发生异常 - {str(e)}"
    
    def _format_size(self, size: int) -> str:
        """Format file size to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"
