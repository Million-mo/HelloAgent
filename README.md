# AI Chat - 智能助手系统

一个基于 FastAPI 和 WebSocket 的现代化 AI 聊天系统，支持多 Agent 架构、工具调用和流式输出。

## ✨ 特性

- 🤖 **多 Agent 架构** - 支持多种专业化 Agent（通用助理、简单对话、分析专家、编程助手）
- 🔧 **工具集成** - 内置丰富的工具系统（天气、计算器、终端、文件操作等）
- 💬 **实时通信** - 基于 WebSocket 的双向流式通信
- 🎯 **Function Calling** - 原生支持 OpenAI Function Calling 模式
- 🔄 **ReAct 模式** - 支持推理-行动循环（Reasoning + Action）
- 📊 **会话管理** - 完整的对话历史和上下文维护
- 🎨 **现代化界面** - 响应式前端设计，支持 Markdown 渲染和代码高亮
- ⏸️ **流式控制** - 支持暂停/停止生成

## 🏗️ 项目结构

```
.
├── ai_chat/
│   ├── backend/                 # 后端服务
│   │   ├── agents/              # Agent 系统
│   │   │   ├── base_agent.py    # Agent 基类
│   │   │   ├── function_call_agent.py  # Function Call Agent
│   │   │   ├── specialized_agents.py   # 专业化 Agent
│   │   │   └── agent_manager.py        # Agent 管理器
│   │   ├── chat/                # 聊天处理
│   │   │   ├── session.py       # 会话管理
│   │   │   ├── processor.py     # 消息处理器
│   │   │   ├── react_processor.py      # ReAct 处理器
│   │   │   └── function_call_processor.py  # Function Call 处理器
│   │   ├── llm/                 # LLM 客户端
│   │   │   └── client.py        # OpenAI 客户端封装
│   │   ├── tools/               # 工具系统
│   │   │   ├── base.py          # 工具基类
│   │   │   ├── registry.py      # 工具注册表
│   │   │   ├── weather.py       # 天气工具
│   │   │   ├── calculator.py    # 计算器工具
│   │   │   ├── time_tool.py     # 时间工具
│   │   │   ├── terminal.py      # 终端工具
│   │   │   └── file_operations.py  # 文件操作工具
│   │   ├── app.py               # 应用主文件
│   │   ├── config.py            # 配置管理
│   │   └── requirements.txt     # Python 依赖
│   └── frontend/                # 前端界面
│       ├── index.html           # 主页面
│       ├── script.js            # 前端逻辑
│       └── style.css            # 样式文件
└── test/                        # 测试文件
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js（可选，用于前端开发）

### 安装依赖

```bash
cd ai_chat/backend
pip install -r requirements.txt
```

### 配置

在 `config.py` 中配置 LLM API：

```python
class LLMConfig(BaseModel):
    api_key: str = "your-api-key"
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"
```

或使用环境变量：

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="https://api.deepseek.com/v1"
export LLM_MODEL="deepseek-chat"
```

### 启动服务

**方式一：直接运行**

```bash
cd ai_chat/backend
python app.py
```

**方式二：使用启动脚本**

```bash
cd ai_chat/backend
python run_server.py
```

服务将在 `http://localhost:8000` 启动。

### 访问前端

在浏览器中打开 `ai_chat/frontend/index.html`，或使用 Live Server 等工具。

## 📖 使用指南

### Agent 类型

系统内置 4 种 Agent：

1. **通用助理** (FunctionCallAgent) - 默认 Agent，支持工具调用和多轮交互
2. **简单对话** (SimpleAgent) - 纯对话 Agent，不使用工具
3. **分析专家** (AnalysisAgent) - 专注于深度分析和推理
4. **编程助手** (CodeAgent) - 专注于编程相关任务

### 处理模式

- **Agent 模式** - 使用 Agent 管理器（推荐）
- **Function Call 模式** - 原生 Function Calling，自动多轮
- **ReAct 模式** - 推理-行动循环
- **Simple 模式** - 单次工具调用

### 内置工具

- **get_weather** - 查询城市天气信息
- **calculator** - 执行数学运算
- **get_current_time** - 获取当前时间和日期
- **execute_command** - 执行 shell 命令
- **read_file** - 读取文本文件
- **write_file** - 写入文件
- **list_directory** - 列出目录内容

## 🔌 API 接口

### REST API

- `GET /` - 健康检查
- `GET /health` - 服务状态
- `GET /agent/info` - 获取所有 Agent 信息
- `GET /agent/stats` - 获取 Agent 系统统计
- `POST /agent/switch/{session_id}` - 切换会话 Agent

### WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{session_id}');

// 发送消息
ws.send(JSON.stringify({
    type: 'message',
    content: '你好',
    mode: 'agent',
    agent_name: '通用助理'  // 可选
}));

// 停止生成
ws.send(JSON.stringify({
    type: 'stop'
}));
```

## 🛠️ 开发指南

### 创建自定义 Agent

```python
from agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, name, llm_client, tool_registry, session_manager):
        super().__init__(
            name=name,
            agent_type="custom",
            llm_client=llm_client,
            tool_registry=tool_registry,
            session_manager=session_manager,
            system_prompt="你的系统提示词"
        )
    
    async def run(self, websocket, session_id, user_input, messages):
        # 实现你的 Agent 逻辑
        pass
```

### 创建自定义工具

```python
from tools.base import BaseTool

class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "我的工具描述"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param": {
                    "type": "string",
                    "description": "参数描述"
                }
            },
            "required": ["param"]
        }
    
    async def execute(self, **kwargs) -> str:
        # 实现工具逻辑
        return "工具执行结果"
```

### 注册工具

```python
from tools.registry import ToolRegistry

tool_registry = ToolRegistry()
tool_registry.register(MyTool())
```

## 🎨 前端集成

### 消息格式

**用户消息：**
```javascript
{
    type: 'user_message_received',
    content: '用户输入的内容',
    mode: 'agent'
}
```

**AI 回复：**
```javascript
{
    type: 'response_chunk',
    content: '流式输出内容'
}
```

**工具调用：**
```javascript
{
    type: 'tool_call',
    tool_name: 'calculator',
    arguments: { expression: '1+1' }
}
```

**工具结果：**
```javascript
{
    type: 'tool_result',
    result: '2'
}
```

## 📝 配置说明

### 服务器配置

```python
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000
```

### LLM 配置

```python
class LLMConfig:
    api_key: str        # API 密钥
    base_url: str       # API 地址
    model: str          # 模型名称
```

### CORS 配置

```python
class CORSConfig:
    allow_origins: list = ["*"]
    allow_credentials: bool = True
    allow_methods: list = ["*"]
    allow_headers: list = ["*"]
```

## 🧪 测试

```bash
# 运行测试
cd test
python test.py
```

## 📦 依赖项

- **fastapi** - Web 框架
- **uvicorn** - ASGI 服务器
- **openai** - OpenAI SDK
- **websockets** - WebSocket 支持
- **aiofiles** - 异步文件操作
- **pydantic** - 数据验证

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🔗 相关链接

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [OpenAI API 文档](https://platform.openai.com/docs/)
- [DeepSeek API](https://api.deepseek.com/)

## 📧 联系方式

如有问题，请提交 Issue。

---

**版本：** 1.2.0 - Modular  
**更新时间：** 2025-11
