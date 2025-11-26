"""Configuration management for the AI Chat application."""

import os
from typing import Optional
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM configuration."""
    
    api_key: str = Field(
        default="sk-a39471beda78451f83d3068fce622d08",
        description="API key for LLM service"
    )
    base_url: str = Field(
        default="https://api.deepseek.com/v1",
        description="Base URL for LLM API"
    )
    model: str = Field(
        default="deepseek-chat",
        description="LLM model name"
    )
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create config from environment variables."""
        return cls(
            api_key=os.getenv("LLM_API_KEY", cls.model_fields["api_key"].default),
            base_url=os.getenv("LLM_BASE_URL", cls.model_fields["base_url"].default),
            model=os.getenv("LLM_MODEL", cls.model_fields["model"].default),
        )


class CORSConfig(BaseModel):
    """CORS configuration."""
    
    allow_origins: list[str] = Field(
        default=["*"],
        description="Allowed origins for CORS"
    )
    allow_credentials: bool = Field(
        default=True,
        description="Allow credentials"
    )
    allow_methods: list[str] = Field(
        default=["*"],
        description="Allowed HTTP methods"
    )
    allow_headers: list[str] = Field(
        default=["*"],
        description="Allowed HTTP headers"
    )


class ServerConfig(BaseModel):
    """Server configuration."""
    
    host: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    port: int = Field(
        default=8000,
        description="Server port"
    )
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Create config from environment variables."""
        return cls(
            host=os.getenv("SERVER_HOST", cls.model_fields["host"].default),
            port=int(os.getenv("SERVER_PORT", str(cls.model_fields["port"].default))),
        )


class LogConfig(BaseModel):
    """Logging configuration."""
    
    log_dir: str = Field(
        default="logs",
        description="Directory for log files"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    max_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum size of a single log file in bytes"
    )
    backup_count: int = Field(
        default=5,
        description="Number of backup log files to keep"
    )
    
    @classmethod
    def from_env(cls) -> "LogConfig":
        """Create config from environment variables."""
        return cls(
            log_dir=os.getenv("LOG_DIR", cls.model_fields["log_dir"].default),
            log_level=os.getenv("LOG_LEVEL", cls.model_fields["log_level"].default),
            max_bytes=int(os.getenv("LOG_MAX_BYTES", str(cls.model_fields["max_bytes"].default))),
            backup_count=int(os.getenv("LOG_BACKUP_COUNT", str(cls.model_fields["backup_count"].default))),
        )


class AppConfig(BaseModel):
    """Application configuration."""
    
    title: str = Field(
        default="AI Chat API",
        description="Application title"
    )
    version: str = Field(
        default="1.2.0 - Modular",
        description="Application version"
    )
    system_prompt: str = Field(
        default=(
            "你是一个智能助手，具有以下功能：\n"
            "1. 天气查询 (get_weather) - 查询城市天气信息\n"
            "2. 数学计算 (calculator) - 执行数学运算，支持加减乘除、幂运算和括号\n"
            "3. 时间日期 (get_current_time) - 获取当前时间和日期，支持不同时区\n"
            "4. 终端命令 (execute_command) - 执行shell命令，查看系统信息、目录内容等\n"
            "5. 读取文件 (read_file) - 读取文本文件内容\n"
            "6. 写入文件 (write_file) - 将内容写入文件\n"
            "7. 列出目录 (list_directory) - 列出目录中的文件和子目录\n"
            "8. 网站内容读取 (read_website) - 读取并提取网站的文本内容，支持HTTP和HTTPS协议\n"
            "9. 代码分析工具：\n"
            "   - analyze_project_structure: 分析项目目录结构\n"
            "   - search_code: 在代码中搜索特定内容\n"
            "   - find_files: 查找特定文件\n"
            "   - analyze_file: 分析文件的详细结构\n"
            "请根据用户需求，灵活使用合适的工具来帮助用户。"
        ),
        description="System prompt for AI assistant"
    )


class Config(BaseModel):
    """Global configuration."""
    
    llm: LLMConfig = Field(default_factory=LLMConfig)
    cors: CORSConfig = Field(default_factory=CORSConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    
    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            llm=LLMConfig.from_env(),
            server=ServerConfig.from_env(),
            log=LogConfig.from_env(),
        )


# 全局配置实例
config = Config.load()
