"""Web scraper tool for reading website content."""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
import time

from .base import BaseTool
from utils.logger import get_logger

logger = get_logger(__name__)


class WebScraperTool(BaseTool):
    """Tool for reading and extracting content from websites."""
    
    @property
    def name(self) -> str:
        return "read_website"
    
    @property
    def description(self) -> str:
        return (
            "Read and extract text content from a website URL. "
            "Supports multiple extraction modes: standard (all text) or reader (main content). "
            "Can handle various access restrictions and encoding issues. "
            "Returns the main text content of the webpage."
        )
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the website to read, must start with http:// or https://"
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum length of content to return (in characters). Default is 5000.",
                    "default": 5000
                },
                "mode": {
                    "type": "string",
                    "enum": ["standard", "reader"],
                    "description": "Extraction mode: 'standard' (all text), 'reader' (main content). Default is 'standard'.",
                    "default": "standard"
                },
                "use_browser": {
                    "type": "boolean",
                    "description": "Use Selenium browser for JavaScript-rendered pages. Default is False.",
                    "default": False
                },
                "wait_time": {
                    "type": "integer",
                    "description": "Wait time in seconds after page load for dynamic content. Default is 0.",
                    "default": 0
                }
            },
            "required": ["url"]
        }
    
    async def execute(
        self, 
        url: str, 
        max_length: int = 5000,
        mode: str = "standard",
        use_browser: bool = False,
        wait_time: int = 0,
        **kwargs
    ) -> str:
        """
        Read content from a website.
        
        Args:
            url: The website URL to read
            max_length: Maximum length of content to return
            mode: Extraction mode - 'standard' or 'reader'
            use_browser: Use Selenium browser for JS-rendered pages
            wait_time: Wait time in seconds after page load
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Extracted text content from the website
        """
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            return f"错误：URL 必须以 http:// 或 https:// 开头。当前URL: {url}"
        
        # Use browser mode if requested
        if use_browser:
            return await self._fetch_with_selenium(url, max_length, mode, wait_time)
        
        try:
            # Set timeout and headers
            timeout = aiohttp.ClientTimeout(total=60)
            headers = self._get_headers()
            
            logger.info(f"正在访问网站: {url}，模式: {mode}")
            
            # Fetch the webpage
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    url, 
                    headers=headers,
                    allow_redirects=True,
                    ssl=False
                ) as response:
                    # Check status code
                    if response.status == 403:
                        return f"错误：访问被拒绝（HTTP 403）\n可能原因：网站检测到爬虫或限制访问"
                    elif response.status == 429:
                        return "错误：访问频率过高，网站返回429状态码。建议稍后再试。"
                    elif response.status != 200:
                        return f"错误：HTTP {response.status} - 无法访问网站"
                    
                    # Get content with encoding handling
                    try:
                        html = await response.text()
                    except UnicodeDecodeError:
                        raw = await response.read()
                        html = raw.decode('gbk', errors='ignore')
                    
                    # Parse HTML and extract text
                    soup = BeautifulSoup(html, 'html.parser')
                    text = self._extract_reader_mode(soup) if mode == "reader" else self._extract_standard_mode(soup)
                    
                    # Clean up text
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = '\n'.join(chunk for chunk in chunks if chunk)
                    
                    # Limit length
                    if len(text) > max_length:
                        text = text[:max_length] + f"\n\n... (内容已截断，总长度: {len(text)} 字符)"
                    
                    # Build result
                    result = f"✓ 网站内容读取成功\n"
                    result += f"URL: {url}\n"
                    result += f"内容长度: {len(text)} 字符\n"
                    result += f"提取模式: {'阅读器模式' if mode == 'reader' else '标准模式'}\n"
                    result += f"\n--- 网页内容 ---\n{text}"
                    
                    return result
                    
        except aiohttp.ClientConnectorError as e:
            return f"错误：无法连接到网站 - {str(e)}"
        except asyncio.TimeoutError:
            return f"错误：访问超时 - 网站响应时间过长"
        except aiohttp.ClientError as e:
            return f"错误：网络请求失败 - {str(e)}"
        except Exception as e:
            logger.error(f"读取网站内容失败: {e}", exc_info=True)
            return f"错误：读取网站内容失败 - {str(e)}"
    
    async def _fetch_with_selenium(
        self,
        url: str,
        max_length: int,
        mode: str,
        wait_time: int
    ) -> str:
        """
        使用 Selenium 浏览器获取网页内容（支持 JavaScript 渲染）
        """
        driver = None
        try:
            logger.info(f"使用 Selenium 浏览器访问: {url}")
            
            # 配置 Chrome 选项
            chrome_options = ChromeOptions()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # 创建驱动程序
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(60)
            
            # 访问网页
            logger.info("正在加载页面...")
            driver.get(url)
            
            # 等待页面加载完成或动态内容加载
            try:
                WebDriverWait(driver, 10).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
            except:
                logger.warning("页面加载等待超时，继续处理")
            
            # 额外等待时间（用于动态内容）
            if wait_time > 0:
                logger.info(f"等待 {wait_time} 秒以加载动态内容...")
                time.sleep(wait_time)
            else:
                time.sleep(2)  # 默认等待 2 秒
            
            # 获取页面 HTML
            html = driver.page_source
            
            # 提取内容
            soup = BeautifulSoup(html, 'html.parser')
            text = self._extract_reader_mode(soup) if mode == "reader" else self._extract_standard_mode(soup)
            
            # 清理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # 限制长度
            if len(text) > max_length:
                text = text[:max_length] + f"\n\n... (内容已截断，总长度: {len(text)} 字符)"
            
            # 构建结果
            result = f"✓ 网站内容读取成功 (Selenium 浏览器模式)\n"
            result += f"URL: {url}\n"
            result += f"浏览器: Chrome (Selenium)\n"
            result += f"内容长度: {len(text)} 字符\n"
            result += f"提取模式: {'阅读器模式' if mode == 'reader' else '标准模式'}\n"
            result += f"\n--- 网页内容 ---\n{text}"
            
            return result
            
        except Exception as e:
            logger.error(f"Selenium 浏览器访问失败: {e}", exc_info=True)
            return f"错误：Selenium 浏览器访问失败 - {str(e)}\n\n建议：\n1. 确保已安装 ChromeDriver\n2. 检查 Chrome 浏览器是否已安装\n3. 尝试更新 Selenium: pip install --upgrade selenium"
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _get_headers(self) -> Dict[str, str]:
        """获取浏览器请求头"""
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
    

    
    def _extract_standard_mode(self, soup: BeautifulSoup) -> str:
        """标准模式提取内容"""
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    

    
    def _extract_reader_mode(self, soup: BeautifulSoup) -> str:
        """阅读器模式提取主要内容"""
        # 尝试找到主要内容区域
        main_content = None
        
        # 常用的内容选择器
        selectors = [
            ('article', None),
            ('main', None),
            ('div', 'article'),
            ('div', 'content'),
            ('div', 'post-content'),
            ('div', 'entry-content'),
            ('div', 'article-content'),
        ]
        
        for tag, class_name in selectors:
            if class_name:
                main_content = soup.find(tag, class_=lambda x: x and class_name in x.lower() if x else False)
            else:
                main_content = soup.find(tag)
            
            if main_content:
                break
        
        # 未找到则使用body或整个页面
        main_content = main_content or soup.body or soup
        
        # 清理内容
        for element in main_content.find_all(['script', 'style', 'nav', 'footer', 'aside', 'iframe', 'noscript']):
            element.decompose()
        
        # 提取并清理文本
        text = main_content.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    

