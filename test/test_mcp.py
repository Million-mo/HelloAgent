"""
MCP (Model Context Protocol) 使用测试

这个测试演示了如何使用MCP协议与外部工具和资源进行交互。
MCP是一个开放协议，允许AI应用与各种数据源和工具进行标准化通信。

测试内容：
1. MCP客户端初始化
2. 工具发现和列举
3. 工具调用和参数传递
4. 资源访问
5. 提示词模板使用
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


# ============ MCP 协议基础定义 ============

class MCPMessageType(Enum):
    """MCP消息类型"""
    INITIALIZE = "initialize"
    LIST_TOOLS = "list_tools"
    CALL_TOOL = "call_tool"
    LIST_RESOURCES = "list_resources"
    READ_RESOURCE = "read_resource"
    LIST_PROMPTS = "list_prompts"


@dataclass
class MCPTool:
    """MCP工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPResource:
    """MCP资源定义"""
    uri: str
    name: str
    description: str
    mime_type: str


@dataclass
class MCPPrompt:
    """MCP提示词模板"""
    name: str
    description: str
    arguments: List[Dict[str, Any]]


# ============ 模拟MCP服务器 ============

class MockMCPServer:
    """模拟的MCP服务器，提供工具、资源和提示词"""
    
    def __init__(self):
        self.tools = [
            MCPTool(
                name="search_weather",
                description="搜索指定城市的天气信息",
                input_schema={
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称"
                        },
                        "units": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "温度单位",
                            "default": "celsius"
                        }
                    },
                    "required": ["city"]
                }
            ),
            MCPTool(
                name="calculate",
                description="执行数学计算",
                input_schema={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式，如 '2 + 2' 或 '10 * 5'"
                        }
                    },
                    "required": ["expression"]
                }
            ),
            MCPTool(
                name="get_current_time",
                description="获取当前时间",
                input_schema={
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "时区，如 'Asia/Shanghai'",
                            "default": "UTC"
                        }
                    }
                }
            )
        ]
        
        self.resources = [
            MCPResource(
                uri="file:///docs/manual.txt",
                name="用户手册",
                description="产品使用手册",
                mime_type="text/plain"
            ),
            MCPResource(
                uri="file:///data/config.json",
                name="配置文件",
                description="系统配置参数",
                mime_type="application/json"
            )
        ]
        
        self.prompts = [
            MCPPrompt(
                name="code_review",
                description="代码审查提示词模板",
                arguments=[
                    {"name": "language", "description": "编程语言", "required": True},
                    {"name": "code", "description": "待审查的代码", "required": True}
                ]
            )
        ]
        
        # 模拟的天气数据
        self.weather_data = {
            "beijing": {"temp": 18, "condition": "晴天", "humidity": 45},
            "shanghai": {"temp": 22, "condition": "多云", "humidity": 60},
            "hangzhou": {"temp": 20, "condition": "晴天", "humidity": 50},
        }
        
        # 模拟的资源内容
        self.resource_data = {
            "file:///docs/manual.txt": "这是产品使用手册的内容...",
            "file:///data/config.json": json.dumps({"version": "1.0", "debug": False})
        }
    
    async def list_tools(self) -> List[MCPTool]:
        """列出所有可用工具"""
        return self.tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        if name == "search_weather":
            city = arguments.get("city", "").lower()
            units = arguments.get("units", "celsius")
            
            if city in self.weather_data:
                data = self.weather_data[city]
                temp = data["temp"]
                if units == "fahrenheit":
                    temp = temp * 9/5 + 32
                
                return {
                    "city": city,
                    "temperature": f"{temp}{'°C' if units == 'celsius' else '°F'}",
                    "condition": data["condition"],
                    "humidity": f"{data['humidity']}%"
                }
            else:
                return {"error": f"未找到城市 {city} 的天气数据"}
        
        elif name == "calculate":
            expression = arguments.get("expression", "")
            try:
                # 注意：实际使用中应该使用安全的表达式求值
                result = eval(expression)
                return {"expression": expression, "result": result}
            except Exception as e:
                return {"error": f"计算错误: {str(e)}"}
        
        elif name == "get_current_time":
            from datetime import datetime
            timezone = arguments.get("timezone", "UTC")
            now = datetime.now()
            return {
                "timezone": timezone,
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": now.timestamp()
            }
        
        else:
            return {"error": f"未知工具: {name}"}
    
    async def list_resources(self) -> List[MCPResource]:
        """列出所有可用资源"""
        return self.resources
    
    async def read_resource(self, uri: str) -> str:
        """读取资源内容"""
        return self.resource_data.get(uri, "")
    
    async def list_prompts(self) -> List[MCPPrompt]:
        """列出所有提示词模板"""
        return self.prompts


# ============ MCP 客户端 ============

class MCPClient:
    """MCP协议客户端"""
    
    def __init__(self, server: MockMCPServer):
        self.server = server
        self.initialized = False
        self.available_tools: List[MCPTool] = []
        self.available_resources: List[MCPResource] = []
        self.available_prompts: List[MCPPrompt] = []
    
    async def initialize(self) -> bool:
        """初始化MCP连接"""
        print("🔌 初始化MCP客户端...")
        
        # 发现可用工具
        self.available_tools = await self.server.list_tools()
        print(f"✅ 发现 {len(self.available_tools)} 个工具")
        
        # 发现可用资源
        self.available_resources = await self.server.list_resources()
        print(f"✅ 发现 {len(self.available_resources)} 个资源")
        
        # 发现可用提示词
        self.available_prompts = await self.server.list_prompts()
        print(f"✅ 发现 {len(self.available_prompts)} 个提示词模板")
        
        self.initialized = True
        return True
    
    async def list_tools(self) -> List[MCPTool]:
        """列出所有工具"""
        if not self.initialized:
            await self.initialize()
        return self.available_tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        if not self.initialized:
            await self.initialize()
        
        # 验证工具是否存在
        tool = next((t for t in self.available_tools if t.name == name), None)
        if not tool:
            raise ValueError(f"工具 {name} 不存在")
        
        print(f"\n🔧 调用工具: {name}")
        print(f"📥 参数: {json.dumps(arguments, ensure_ascii=False)}")
        
        result = await self.server.call_tool(name, arguments)
        
        print(f"📤 结果: {json.dumps(result, ensure_ascii=False)}")
        return result
    
    async def read_resource(self, uri: str) -> str:
        """读取资源"""
        if not self.initialized:
            await self.initialize()
        
        print(f"\n📖 读取资源: {uri}")
        content = await self.server.read_resource(uri)
        print(f"📄 内容: {content[:100]}..." if len(content) > 100 else f"📄 内容: {content}")
        return content


# ============ 测试用例 ============

async def test_mcp_initialization():
    """测试1: MCP客户端初始化"""
    print("\n" + "="*60)
    print("测试1: MCP客户端初始化")
    print("="*60)
    
    server = MockMCPServer()
    client = MCPClient(server)
    
    success = await client.initialize()
    assert success, "初始化失败"
    assert len(client.available_tools) > 0, "未发现任何工具"
    
    print("\n✅ 测试通过: 客户端初始化成功")


async def test_list_tools():
    """测试2: 工具列举"""
    print("\n" + "="*60)
    print("测试2: 工具列举")
    print("="*60)
    
    server = MockMCPServer()
    client = MCPClient(server)
    
    tools = await client.list_tools()
    
    print("\n可用工具列表:")
    for i, tool in enumerate(tools, 1):
        print(f"\n{i}. {tool.name}")
        print(f"   描述: {tool.description}")
        print(f"   参数: {json.dumps(tool.input_schema, ensure_ascii=False, indent=2)}")
    
    assert len(tools) == 3, "工具数量不正确"
    print("\n✅ 测试通过: 成功列举所有工具")


async def test_weather_tool():
    """测试3: 天气查询工具调用"""
    print("\n" + "="*60)
    print("测试3: 天气查询工具调用")
    print("="*60)
    
    server = MockMCPServer()
    client = MCPClient(server)
    
    # 测试摄氏度
    result1 = await client.call_tool("search_weather", {
        "city": "beijing",
        "units": "celsius"
    })
    assert "temperature" in result1, "结果中缺少温度信息"
    
    # 测试华氏度
    result2 = await client.call_tool("search_weather", {
        "city": "shanghai",
        "units": "fahrenheit"
    })
    assert "temperature" in result2, "结果中缺少温度信息"
    
    print("\n✅ 测试通过: 天气查询工具正常工作")


async def test_calculator_tool():
    """测试4: 计算器工具调用"""
    print("\n" + "="*60)
    print("测试4: 计算器工具调用")
    print("="*60)
    
    server = MockMCPServer()
    client = MCPClient(server)
    
    # 测试加法
    result1 = await client.call_tool("calculate", {
        "expression": "2 + 2"
    })
    assert result1["result"] == 4, "计算结果错误"
    
    # 测试乘法
    result2 = await client.call_tool("calculate", {
        "expression": "10 * 5"
    })
    assert result2["result"] == 50, "计算结果错误"
    
    print("\n✅ 测试通过: 计算器工具正常工作")


async def test_time_tool():
    """测试5: 时间工具调用"""
    print("\n" + "="*60)
    print("测试5: 时间工具调用")
    print("="*60)
    
    server = MockMCPServer()
    client = MCPClient(server)
    
    result = await client.call_tool("get_current_time", {
        "timezone": "Asia/Shanghai"
    })
    
    assert "time" in result, "结果中缺少时间信息"
    assert "timestamp" in result, "结果中缺少时间戳"
    
    print("\n✅ 测试通过: 时间工具正常工作")


async def test_resource_access():
    """测试6: 资源访问"""
    print("\n" + "="*60)
    print("测试6: 资源访问")
    print("="*60)
    
    server = MockMCPServer()
    client = MCPClient(server)
    await client.initialize()
    
    print("\n可用资源列表:")
    for i, resource in enumerate(client.available_resources, 1):
        print(f"\n{i}. {resource.name}")
        print(f"   URI: {resource.uri}")
        print(f"   描述: {resource.description}")
        print(f"   类型: {resource.mime_type}")
    
    # 读取资源
    content1 = await client.read_resource("file:///docs/manual.txt")
    assert len(content1) > 0, "资源内容为空"
    
    content2 = await client.read_resource("file:///data/config.json")
    config = json.loads(content2)
    assert "version" in config, "配置文件格式错误"
    
    print("\n✅ 测试通过: 资源访问正常")


async def test_error_handling():
    """测试7: 错误处理"""
    print("\n" + "="*60)
    print("测试7: 错误处理")
    print("="*60)
    
    server = MockMCPServer()
    client = MCPClient(server)
    
    # 测试不存在的城市
    result1 = await client.call_tool("search_weather", {
        "city": "unknown_city"
    })
    assert "error" in result1, "应该返回错误信息"
    print(f"✓ 正确处理了不存在的城市")
    
    # 测试错误的表达式
    result2 = await client.call_tool("calculate", {
        "expression": "invalid expression"
    })
    assert "error" in result2, "应该返回错误信息"
    print(f"✓ 正确处理了无效的计算表达式")
    
    # 测试不存在的工具
    try:
        await client.call_tool("non_existent_tool", {})
        assert False, "应该抛出异常"
    except ValueError as e:
        print(f"✓ 正确抛出了工具不存在的异常: {e}")
    
    print("\n✅ 测试通过: 错误处理正常")


async def test_mcp_workflow():
    """测试8: 完整MCP工作流"""
    print("\n" + "="*60)
    print("测试8: 完整MCP工作流示例")
    print("="*60)
    
    server = MockMCPServer()
    client = MCPClient(server)
    
    print("\n场景: AI助手帮用户查询天气并进行计算")
    
    # 1. 查询北京天气
    print("\n步骤1: 查询北京天气")
    weather = await client.call_tool("search_weather", {
        "city": "beijing",
        "units": "celsius"
    })
    
    # 2. 查询上海天气
    print("\n步骤2: 查询上海天气")
    weather2 = await client.call_tool("search_weather", {
        "city": "shanghai",
        "units": "celsius"
    })
    
    # 3. 计算温差
    print("\n步骤3: 计算两地温差")
    temp_diff = await client.call_tool("calculate", {
        "expression": "22 - 18"
    })
    
    # 4. 获取当前时间
    print("\n步骤4: 获取查询时间")
    current_time = await client.call_tool("get_current_time", {
        "timezone": "Asia/Shanghai"
    })
    
    # 5. 读取配置资源
    print("\n步骤5: 读取系统配置")
    config = await client.read_resource("file:///data/config.json")
    
    print("\n" + "-"*60)
    print("工作流总结:")
    print(f"✓ 查询了 2 个城市的天气")
    print(f"✓ 执行了 1 次数学计算")
    print(f"✓ 获取了当前时间")
    print(f"✓ 读取了 1 个资源")
    print("-"*60)
    
    print("\n✅ 测试通过: 完整工作流执行成功")


# ============ 主测试函数 ============

async def main():
    """运行所有测试"""
    print("\n" + "🚀"*30)
    print("MCP (Model Context Protocol) 使用测试套件")
    print("🚀"*30)
    
    try:
        await test_mcp_initialization()
        await test_list_tools()
        await test_weather_tool()
        await test_calculator_tool()
        await test_time_tool()
        await test_resource_access()
        await test_error_handling()
        await test_mcp_workflow()
        
        print("\n" + "🎉"*30)
        print("所有测试通过! ✅")
        print("🎉"*30)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
