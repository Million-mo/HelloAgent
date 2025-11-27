"""Code analysis tools for understanding projects."""

import os
import re
from pathlib import Path
from typing import Dict, Any, List, Set
from .base import BaseTool


class AnalyzeProjectStructureTool(BaseTool):
    """Tool for analyzing project structure and generating a tree view."""
    
    def __init__(self, base_dir: str = ".", max_depth: int = 4, ignore_patterns: List[str] = None):
        """
        Initialize project structure analysis tool.
        
        Args:
            base_dir: Base directory to analyze
            max_depth: Maximum depth for directory tree
            ignore_patterns: Patterns to ignore (e.g., ['.git', '__pycache__', 'node_modules'])
        """
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.max_depth = max_depth
        self.ignore_patterns = ignore_patterns or [
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            '.idea', '.vscode', '*.pyc', '.DS_Store', 'dist', 'build'
        ]
    
    @property
    def name(self) -> str:
        return "analyze_project_structure"
    
    @property
    def description(self) -> str:
        return "分析项目目录结构，生成项目文件树视图。可以帮助理解项目的组织结构。"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "要分析的项目目录路径（相对或绝对路径，默认为当前工作目录）"
                },
                "max_depth": {
                    "type": "integer",
                    "description": "目录树的最大深度（默认4层）"
                }
            },
            "required": []
        }
    
    async def execute(self, directory_path: str = ".", max_depth: int = None, **kwargs) -> str:
        """
        Analyze project structure.
        
        Args:
            directory_path: Path to project directory
            max_depth: Maximum depth for tree (overrides default)
            **kwargs: Additional arguments
            
        Returns:
            Project structure tree as string
        """
        try:
            path = Path(directory_path).expanduser()
            if not path.is_absolute():
                path = self.base_dir / path
            path = path.resolve()
            
            if not path.exists():
                return f"错误：目录不存在 '{directory_path}'"
            
            if not path.is_dir():
                return f"错误：'{directory_path}' 不是一个目录"
            
            depth = max_depth if max_depth is not None else self.max_depth
            
            result = f"项目结构分析：{path.name}\n"
            result += f"路径：{path}\n\n"
            result += self._build_tree(path, depth=depth)
            
            return result
            
        except PermissionError:
            return f"错误：没有权限访问目录 '{directory_path}'"
        except Exception as e:
            return f"错误：分析项目结构时发生异常 - {str(e)}"
    
    def _should_ignore(self, name: str) -> bool:
        """Check if file/directory should be ignored."""
        for pattern in self.ignore_patterns:
            if pattern.startswith('*'):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        return False
    
    def _build_tree(self, path: Path, prefix: str = "", depth: int = 4, is_last: bool = True) -> str:
        """Build directory tree recursively."""
        if depth <= 0:
            return ""
        
        tree = ""
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            items = [item for item in items if not self._should_ignore(item.name)]
            
            for i, item in enumerate(items):
                is_last_item = (i == len(items) - 1)
                current_prefix = "└── " if is_last_item else "├── "
                tree += prefix + current_prefix + item.name
                
                if item.is_dir():
                    tree += "/\n"
                    extension = "    " if is_last_item else "│   "
                    tree += self._build_tree(item, prefix + extension, depth - 1, is_last_item)
                else:
                    tree += "\n"
        except PermissionError:
            pass
        
        return tree


class SearchCodeTool(BaseTool):
    """Tool for searching code content in files."""
    
    def __init__(self, base_dir: str = ".", file_extensions: List[str] = None):
        """
        Initialize code search tool.
        
        Args:
            base_dir: Base directory to search in
            file_extensions: File extensions to search (e.g., ['.py', '.js'])
        """
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.file_extensions = file_extensions or [
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', 
            '.go', '.rs', '.rb', '.php', '.css', '.html', '.md'
        ]
        self.ignore_dirs = {
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            '.idea', '.vscode', 'dist', 'build'
        }
    
    @property
    def name(self) -> str:
        return "search_code"
    
    @property
    def description(self) -> str:
        return "在代码文件中搜索特定文本或正则表达式模式。支持多种编程语言文件。"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "要搜索的文本或正则表达式模式"
                },
                "directory_path": {
                    "type": "string",
                    "description": "搜索目录路径（默认为当前工作目录）"
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "是否区分大小写（默认false）"
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回的最大结果数（默认20）"
                }
            },
            "required": ["pattern"]
        }
    
    async def execute(
        self, 
        pattern: str, 
        directory_path: str = ".", 
        case_sensitive: bool = False,
        max_results: int = 20,
        **kwargs
    ) -> str:
        """
        Search code for pattern.
        
        Args:
            pattern: Text or regex pattern to search
            directory_path: Directory to search in
            case_sensitive: Whether to do case-sensitive search
            max_results: Maximum number of results to return
            **kwargs: Additional arguments
            
        Returns:
            Search results as formatted string
        """
        try:
            path = Path(directory_path).expanduser()
            if not path.is_absolute():
                path = self.base_dir / path
            path = path.resolve()
            
            if not path.exists():
                return f"错误：目录不存在 '{directory_path}'"
            
            if not path.is_dir():
                return f"错误：'{directory_path}' 不是一个目录"
            
            # Compile regex pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return f"错误：无效的正则表达式 - {str(e)}"
            
            # Search files
            results = []
            file_count = 0
            
            for file_path in self._iter_code_files(path):
                if len(results) >= max_results:
                    break
                
                file_count += 1
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        if regex.search(line):
                            rel_path = file_path.relative_to(path)
                            results.append({
                                'file': str(rel_path),
                                'line': line_num,
                                'content': line.rstrip()
                            })
                            
                            if len(results) >= max_results:
                                break
                except Exception:
                    continue
            
            # Format results
            if not results:
                return f"未找到匹配 '{pattern}' 的结果（搜索了 {file_count} 个文件）"
            
            output = f"搜索 '{pattern}' 的结果（共 {len(results)} 个匹配，搜索了 {file_count} 个文件）:\n\n"
            for result in results:
                output += f"📄 {result['file']}:{result['line']}\n"
                output += f"   {result['content']}\n\n"
            
            if len(results) >= max_results:
                output += f"（结果已限制为 {max_results} 条，可能还有更多匹配）"
            
            return output
            
        except PermissionError:
            return f"错误：没有权限访问目录 '{directory_path}'"
        except Exception as e:
            return f"错误：搜索代码时发生异常 - {str(e)}"
    
    def _iter_code_files(self, root_path: Path):
        """Iterate over code files in directory."""
        for item in root_path.rglob('*'):
            if item.is_file() and item.suffix in self.file_extensions:
                # Check if any parent is in ignore_dirs
                if not any(parent.name in self.ignore_dirs for parent in item.parents):
                    yield item


class FindFilesTool(BaseTool):
    """Tool for finding files by name pattern."""
    
    def __init__(self, base_dir: str = "."):
        """
        Initialize find files tool.
        
        Args:
            base_dir: Base directory to search in
        """
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.ignore_dirs = {
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            '.idea', '.vscode', 'dist', 'build'
        }
    
    @property
    def name(self) -> str:
        return "find_files"
    
    @property
    def description(self) -> str:
        return "根据文件名模式查找文件。支持通配符搜索（如 *.py, test_*.js）。"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name_pattern": {
                    "type": "string",
                    "description": "文件名模式，支持通配符（如 *.py, config.*, *test*）"
                },
                "directory_path": {
                    "type": "string",
                    "description": "搜索目录路径（默认为当前工作目录）"
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回的最大结果数（默认50）"
                }
            },
            "required": ["name_pattern"]
        }
    
    async def execute(
        self, 
        name_pattern: str, 
        directory_path: str = ".",
        max_results: int = 50,
        **kwargs
    ) -> str:
        """
        Find files by name pattern.
        
        Args:
            name_pattern: File name pattern with wildcards
            directory_path: Directory to search in
            max_results: Maximum number of results
            **kwargs: Additional arguments
            
        Returns:
            List of matching files
        """
        try:
            path = Path(directory_path).expanduser()
            if not path.is_absolute():
                path = self.base_dir / path
            path = path.resolve()
            
            if not path.exists():
                return f"错误：目录不存在 '{directory_path}'"
            
            if not path.is_dir():
                return f"错误：'{directory_path}' 不是一个目录"
            
            # Convert wildcard pattern to regex
            regex_pattern = name_pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
            regex = re.compile(regex_pattern, re.IGNORECASE)
            
            # Find matching files
            results = []
            for item in path.rglob('*'):
                if len(results) >= max_results:
                    break
                
                if item.is_file() and regex.match(item.name):
                    # Check if any parent is in ignore_dirs
                    if not any(parent.name in self.ignore_dirs for parent in item.parents):
                        rel_path = item.relative_to(path)
                        results.append(str(rel_path))
            
            # Format results
            if not results:
                return f"未找到匹配模式 '{name_pattern}' 的文件"
            
            output = f"找到 {len(results)} 个匹配 '{name_pattern}' 的文件:\n\n"
            for file_path in sorted(results):
                output += f"📄 {file_path}\n"
            
            if len(results) >= max_results:
                output += f"\n（结果已限制为 {max_results} 个文件）"
            
            return output
            
        except PermissionError:
            return f"错误：没有权限访问目录 '{directory_path}'"
        except Exception as e:
            return f"错误：查找文件时发生异常 - {str(e)}"


class AnalyzeFileTool(BaseTool):
    """Tool for analyzing a code file's structure (imports, classes, functions, etc.)."""
    
    def __init__(self, base_dir: str = "."):
        """
        Initialize file analysis tool.
        
        Args:
            base_dir: Base directory for relative paths
        """
        self.base_dir = Path(base_dir).expanduser().resolve()
    
    @property
    def name(self) -> str:
        return "analyze_file"
    
    @property
    def description(self) -> str:
        return "分析代码文件的结构，提取导入语句、类定义、函数定义等关键信息。"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要分析的文件路径"
                }
            },
            "required": ["file_path"]
        }
    
    async def execute(self, file_path: str, **kwargs) -> str:
        """
        Analyze file structure.
        
        Args:
            file_path: Path to file to analyze
            **kwargs: Additional arguments
            
        Returns:
            File analysis results
        """
        try:
            path = Path(file_path).expanduser()
            if not path.is_absolute():
                path = self.base_dir / path
            path = path.resolve()
            
            if not path.exists():
                return f"错误：文件不存在 '{file_path}'"
            
            if not path.is_file():
                return f"错误：'{file_path}' 不是一个文件"
            
            # Read file
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Analyze based on file type
            ext = path.suffix.lower()
            
            if ext == '.py':
                return self._analyze_python(path.name, content, lines)
            elif ext in ['.js', '.ts', '.jsx', '.tsx']:
                return self._analyze_javascript(path.name, content, lines)
            else:
                return self._analyze_generic(path.name, content, lines)
            
        except PermissionError:
            return f"错误：没有权限读取文件 '{file_path}'"
        except Exception as e:
            return f"错误：分析文件时发生异常 - {str(e)}"
    
    def _analyze_python(self, filename: str, content: str, lines: List[str]) -> str:
        """Analyze Python file."""
        result = f"Python 文件分析：{filename}\n"
        result += f"总行数：{len(lines)}\n\n"
        
        # Find imports
        imports = []
        for line in lines:
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append(line)
        
        if imports:
            result += f"📦 导入语句 ({len(imports)}):\n"
            for imp in imports[:20]:  # Limit to 20
                result += f"  {imp}\n"
            if len(imports) > 20:
                result += f"  ... 还有 {len(imports) - 20} 个导入\n"
            result += "\n"
        
        # Find classes
        classes = []
        for i, line in enumerate(lines):
            if line.strip().startswith('class '):
                match = re.match(r'class\s+(\w+)', line.strip())
                if match:
                    classes.append((match.group(1), i + 1))
        
        if classes:
            result += f"🏛️ 类定义 ({len(classes)}):\n"
            for class_name, line_num in classes:
                result += f"  {class_name} (行 {line_num})\n"
            result += "\n"
        
        # Find functions
        functions = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('def ') or stripped.startswith('async def '):
                match = re.match(r'(?:async\s+)?def\s+(\w+)', stripped)
                if match:
                    functions.append((match.group(1), i + 1))
        
        if functions:
            result += f"⚙️ 函数定义 ({len(functions)}):\n"
            for func_name, line_num in functions[:30]:  # Limit to 30
                result += f"  {func_name} (行 {line_num})\n"
            if len(functions) > 30:
                result += f"  ... 还有 {len(functions) - 30} 个函数\n"
            result += "\n"
        
        return result
    
    def _analyze_javascript(self, filename: str, content: str, lines: List[str]) -> str:
        """Analyze JavaScript/TypeScript file."""
        result = f"JavaScript/TypeScript 文件分析：{filename}\n"
        result += f"总行数：{len(lines)}\n\n"
        
        # Find imports
        imports = []
        for line in lines:
            line = line.strip()
            if line.startswith('import ') or line.startswith('export '):
                imports.append(line)
        
        if imports:
            result += f"📦 导入/导出语句 ({len(imports)}):\n"
            for imp in imports[:20]:
                result += f"  {imp}\n"
            if len(imports) > 20:
                result += f"  ... 还有 {len(imports) - 20} 个\n"
            result += "\n"
        
        # Find classes
        classes = re.findall(r'class\s+(\w+)', content)
        if classes:
            result += f"🏛️ 类定义 ({len(classes)}):\n"
            for class_name in classes:
                result += f"  {class_name}\n"
            result += "\n"
        
        # Find functions
        functions = re.findall(r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\()', content)
        func_names = [f[0] or f[1] for f in functions]
        if func_names:
            result += f"⚙️ 函数定义 ({len(func_names)}):\n"
            for func_name in func_names[:30]:
                result += f"  {func_name}\n"
            if len(func_names) > 30:
                result += f"  ... 还有 {len(func_names) - 30} 个函数\n"
            result += "\n"
        
        return result
    
    def _analyze_generic(self, filename: str, content: str, lines: List[str]) -> str:
        """Analyze generic file."""
        result = f"文件分析：{filename}\n"
        result += f"总行数：{len(lines)}\n"
        result += f"文件大小：{len(content)} 字符\n\n"
        
        # Count non-empty lines
        non_empty = sum(1 for line in lines if line.strip())
        result += f"非空行数：{non_empty}\n"
        
        # Count comments (simple heuristic)
        comment_lines = sum(1 for line in lines if line.strip().startswith(('#', '//', '/*', '*')))
        result += f"注释行数（估计）：{comment_lines}\n"
        
        return result
