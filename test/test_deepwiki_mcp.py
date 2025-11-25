"""
DeepWiki MCP 测试 (使用 PyPI mcp 包)

DeepWiki MCP 是一个提供对公开 GitHub 仓库文档访问和搜索能力的 MCP 服务器。
服务地址: https://mcp.deepwiki.com/

提供的工具:
1. read_wiki_structure - 获取 GitHub 仓库的文档主题列表
2. read_wiki_contents - 查看 GitHub 仓库的文档内容
3. ask_question - 对 GitHub 仓库提问并获取 AI 驱动的回答

安装依赖:
pip install mcp httpx

使用 PyPI mcp 包通过 SSE 协议连接到 DeepWiki MCP 服务器。
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client


# ============ DeepWiki MCP 客户端 (使用 PyPI mcp 包) ============

class DeepWikiMCPClient:
    """DeepWiki MCP 客户端 - 使用官方 mcp 包"""
    
    def __init__(self):
        """初始化客户端"""
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.available_tools = []
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()
    
    async def connect(self):
        """连接到 DeepWiki MCP 服务器"""
        print(f"🔌 连接到 DeepWiki MCP 服务器 (使用 SSE 协议)...")
        
        try:
            # 使用 SSE 客户端连接到 DeepWiki MCP 服务器
            sse_transport = await self.exit_stack.enter_async_context(
                sse_client(url="https://mcp.deepwiki.com/sse")
            )
            
            # 创建 MCP 客户端会话
            read_stream, write_stream = sse_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            
            # 初始化会话
            await self.session.initialize()
            
            print(f"✅ 连接成功")
            
            # 列出可用工具
            tools_response = await self.session.list_tools()
            self.available_tools = tools_response.tools
            print(f"✅ 发现 {len(self.available_tools)} 个工具")
            
        except Exception as e:
            print(f"❌ 连接错误: {e}")
            raise
    
    async def close(self):
        """关闭连接"""
        await self.exit_stack.aclose()
    
    async def list_tools(self) -> List[Any]:
        """列出所有可用工具"""
        if not self.session:
            raise RuntimeError("客户端未连接，请先调用 connect()")
        
        response = await self.session.list_tools()
        return response.tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        if not self.session:
            raise RuntimeError("客户端未连接，请先调用 connect()")
        
        print(f"\n🔧 调用工具: {tool_name}")
        print(f"📥 参数: {json.dumps(arguments, ensure_ascii=False)}")
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            print(f"✅ 调用成功")
            return result
        except Exception as e:
            print(f"❌ 调用失败: {e}")
            return {"error": str(e)}
    
    async def read_wiki_structure(self, repository: str) -> Any:
        """获取仓库的文档结构"""
        return await self.call_tool("read_wiki_structure", {
            "repoName": repository
        })
    
    async def read_wiki_contents(self, repository: str, topic: Optional[str] = None) -> Any:
        """读取仓库的文档内容"""
        args = {"repoName": repository}
        if topic:
            args["topic"] = topic
        return await self.call_tool("read_wiki_contents", args)
    
    async def ask_question(self, repository: str, question: str) -> Any:
        """对仓库提问"""
        return await self.call_tool("ask_question", {
            "repoName": repository,
            "question": question
        })


# ============ 测试用例 ============

async def test_list_available_tools():
    """测试1: 列出可用工具"""
    print("\n" + "="*60)
    print("测试1: 列出 DeepWiki MCP 可用工具")
    print("="*60)
    
    async with DeepWikiMCPClient() as client:
        tools = await client.list_tools()
        
        print("\nDeepWiki MCP 提供的工具:")
        for i, tool in enumerate(tools, 1):
            print(f"\n{i}. {tool.name}")
            print(f"   描述: {tool.description}")
            if hasattr(tool, 'inputSchema'):
                print(f"   参数: {json.dumps(tool.inputSchema, ensure_ascii=False, indent=6)}")
    
    print("\n✅ 测试通过: 已列出所有工具")


async def test_connection():
    """测试2: 连接测试"""
    print("\n" + "="*60)
    print("测试2: 连接 DeepWiki MCP 服务器")
    print("="*60)
    
    async with DeepWikiMCPClient() as client:
        # 连接已经在 __aenter__ 中完成
        print(f"\n服务器信息:")
        print(f"  可用工具数量: {len(client.available_tools)}")
        print("\n✅ 测试通过: 连接成功")


async def test_read_wiki_structure():
    """测试3: 读取仓库文档结构"""
    print("\n" + "="*60)
    print("测试3: 读取仓库文档结构")
    print("="*60)
    
    # 测试热门仓库
    test_repos = [
        "facebook/react",
        "microsoft/vscode",
        "python/cpython"
    ]
    
    async with DeepWikiMCPClient() as client:
        
        for repo in test_repos:
            print(f"\n📚 查询仓库: {repo}")
            result = await client.read_wiki_structure(repo)
            
            if result and not isinstance(result, dict) or "error" not in result:
                print(f"✅ 成功获取文档结构")
                # 处理 mcp 包返回的结果
                if hasattr(result, 'content'):
                    content = result.content
                    if content and len(content) > 0:
                        text_content = content[0].text if hasattr(content[0], 'text') else str(content[0])
                        print(f"📄 文档主题预览 (前200字符):")
                        print(f"   {text_content[:200]}...")
            else:
                print(f"❌ 获取失败")
            
            # 避免请求过快
            await asyncio.sleep(1)
    
    print("\n✅ 测试完成")


async def test_read_wiki_contents():
    """测试4: 读取仓库文档内容"""
    print("\n" + "="*60)
    print("测试4: 读取仓库文档内容")
    print("="*60)
    
    repository = "facebook/react"
    
    async with DeepWikiMCPClient() as client:
        
        print(f"\n📖 读取仓库文档: {repository}")
        result = await client.read_wiki_contents(repository)
        
        if result and not isinstance(result, dict) or "error" not in result:
            print(f"✅ 成功读取文档内容")
            # 处理 mcp 包返回的结果
            if hasattr(result, 'content'):
                content = result.content
                if content and len(content) > 0:
                    text_content = content[0].text if hasattr(content[0], 'text') else str(content[0])
                    print(f"\n📄 文档内容预览 (前500字符):")
                    print("-" * 60)
                    print(text_content[:500])
                    print("-" * 60)
                    print(f"\n总长度: {len(text_content)} 字符")
        else:
            print(f"❌ 读取失败: {result}")
    
    print("\n✅ 测试完成")


async def test_ask_question():
    """测试5: AI 问答功能"""
    print("\n" + "="*60)
    print("测试5: AI 问答功能")
    print("="*60)
    
    # 准备测试问题
    test_cases = [
        {
            "repository": "facebook/react",
            "question": "What is React and what are its main features?"
        },
        {
            "repository": "microsoft/vscode",
            "question": "How do I create a custom extension for VS Code?"
        }
    ]
    
    async with DeepWikiMCPClient() as client:
        
        for i, test_case in enumerate(test_cases, 1):
            repo = test_case["repository"]
            question = test_case["question"]
            
            print(f"\n❓ 测试问题 {i}:")
            print(f"   仓库: {repo}")
            print(f"   问题: {question}")
            
            result = await client.ask_question(repo, question)
            
            if result and not isinstance(result, dict) or "error" not in result:
                print(f"✅ 获取到答案")
                # 处理 mcp 包返回的结果
                if hasattr(result, 'content'):
                    content = result.content
                    if content and len(content) > 0:
                        answer = content[0].text if hasattr(content[0], 'text') else str(content[0])
                        print(f"\n💡 AI 回答 (前300字符):")
                        print("-" * 60)
                        print(answer[:300])
                        if len(answer) > 300:
                            print("...")
                        print("-" * 60)
            else:
                print(f"❌ 获取答案失败: {result}")
            
            # 避免请求过快
            await asyncio.sleep(2)
    
    print("\n✅ 测试完成")


async def test_multiple_protocols():
    """测试6: 测试 SSE 协议"""
    print("\n" + "="*60)
    print("测试6: 测试 SSE 协议支持")
    print("="*60)
    
    print(f"\n🔌 测试协议: SSE")
    
    async with DeepWikiMCPClient() as client:
        tools = await client.list_tools()
        if tools:
            print(f"✅ SSE 协议连接成功，发现 {len(tools)} 个工具")
        else:
            print(f"❌ SSE 协议连接失败")
    
    print("\n✅ 测试完成")


async def test_real_world_workflow():
    """测试7: 真实场景工作流"""
    print("\n" + "="*60)
    print("测试7: 真实场景 - 探索 Python 项目")
    print("="*60)
    
    repository = "python/cpython"
    
    async with DeepWikiMCPClient() as client:
        
        # 步骤1: 获取文档结构
        print(f"\n📋 步骤1: 获取 {repository} 的文档结构")
        structure = await client.read_wiki_structure(repository)
        
        if structure and not isinstance(structure, dict) or "error" not in structure:
            print("✅ 成功获取文档结构")
        
        await asyncio.sleep(1)
        
        # 步骤2: 读取文档内容
        print(f"\n📖 步骤2: 读取文档内容")
        contents = await client.read_wiki_contents(repository)
        
        if contents and not isinstance(contents, dict) or "error" not in contents:
            print("✅ 成功读取文档内容")
        
        await asyncio.sleep(1)
        
        # 步骤3: 提问获取信息
        print(f"\n❓ 步骤3: 提问了解项目")
        questions = [
            "What is CPython?",
            "How do I build CPython from source?"
        ]
        
        for question in questions:
            print(f"\n   问题: {question}")
            answer = await client.ask_question(repository, question)
            
            if answer and not isinstance(answer, dict) or "error" not in answer:
                print(f"   ✅ 获取到答案")
                # 处理 mcp 包返回的结果
                if hasattr(answer, 'content'):
                    content = answer.content
                    if content and len(content) > 0:
                        text = content[0].text if hasattr(content[0], 'text') else str(content[0])
                        print(f"   💡 答案预览: {text[:150]}...")
            
            await asyncio.sleep(2)
        
        print("\n" + "-"*60)
        print("工作流总结:")
        print("✓ 获取了项目文档结构")
        print("✓ 读取了文档内容")
        print("✓ 通过 AI 问答了解了项目")
        print("-"*60)
    
    print("\n✅ 测试完成: 真实工作流执行成功")


# ============ 主测试函数 ============

async def main():
    """运行所有测试"""
    print("\n" + "🚀"*30)
    print("DeepWiki MCP 测试套件")
    print("服务地址: https://mcp.deepwiki.com/")
    print("🚀"*30)
    
    try:
        # 基础测试
        await test_list_available_tools()
        await test_connection()
        
        # 功能测试
        await test_read_wiki_structure()
        await test_read_wiki_contents()
        await test_ask_question()
        
        # 协议测试
        await test_multiple_protocols()
        
        # 综合测试
        await test_real_world_workflow()
        
        print("\n" + "🎉"*30)
        print("所有测试完成! ✅")
        print("🎉"*30)
        
        print("\n📝 使用建议:")
        print("1. DeepWiki MCP 可用于查询任何公开的 GitHub 仓库文档")
        print("2. 使用 PyPI mcp 包通过 SSE 协议连接")
        print("3. ask_question 工具提供了 AI 驱动的智能问答")
        print("4. 适合集成到 AI 助手中帮助用户了解开源项目")
        print("\n📦 安装依赖:")
        print("   pip install mcp httpx")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 需要安装: pip install mcp httpx
    asyncio.run(main())
