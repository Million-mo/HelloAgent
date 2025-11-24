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
    
    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            llm=LLMConfig.from_env(),
            server=ServerConfig.from_env(),
        )


# 全局配置实例
config = Config.load()
