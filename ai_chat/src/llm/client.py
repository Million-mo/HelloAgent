"""LLM client management."""

import httpx
from openai import AsyncOpenAI
from typing import Optional

from ..config import LLMConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """Manages LLM client lifecycle and provides access to OpenAI client."""
    
    def __init__(self, config: LLMConfig):
        """
        Initialize LLM client.
        
        Args:
            config: LLM configuration
        """
        self.config = config
        self._http_client: Optional[httpx.AsyncClient] = None
        self._openai_client: Optional[AsyncOpenAI] = None
    
    def initialize(self) -> AsyncOpenAI:
        """
        Initialize and return OpenAI client.
        
        Returns:
            Initialized AsyncOpenAI client
        """
        if self._openai_client is None:
            logger.info(f"初始化 OpenAI 客户端: {self.config.base_url}")
            # 创建自定义 HTTP 客户端用于连接复用
            self._http_client = httpx.AsyncClient()
            
            # 创建 OpenAI 客户端
            self._openai_client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                http_client=self._http_client
            )
            logger.info(f"使用模型: {self.config.model}")
        
        return self._openai_client
    
    @property
    def client(self) -> AsyncOpenAI:
        """
        Get OpenAI client, initialize if needed.
        
        Returns:
            AsyncOpenAI client
        """
        if self._openai_client is None:
            return self.initialize()
        return self._openai_client
    
    @property
    def model(self) -> str:
        """
        Get configured model name.
        
        Returns:
            Model name
        """
        return self.config.model
    
    async def close(self) -> None:
        """Close HTTP client and release resources."""
        if self._http_client is not None:
            logger.info("关闭 HTTP 客户端")
            await self._http_client.aclose()
            self._http_client = None
            self._openai_client = None
            logger.debug("HTTP 客户端已释放")
    
    def __del__(self):
        """Cleanup on deletion."""
        # Note: __del__ with async is tricky, better to call close() explicitly
        pass
