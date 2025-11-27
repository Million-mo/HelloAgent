# AI Chat Backend

A multi-agent system with LLM integration for intelligent conversational AI.

## Features

- 🤖 Multi-agent system with specialized agents
- 💬 Real-time chat processing with WebSocket support
- 🔧 Extensible tool system for function calling
- 🧠 Memory system for context management
- 🌐 Web scraping and external API integration

## Installation

### Development Installation

Install in editable mode for development:

```bash
cd ai_chat/backend
pip install -e .
```

### Production Installation

```bash
pip install -e ai_chat/backend
```

### With Development Dependencies

```bash
pip install -e "ai_chat/backend[dev]"
```

## Usage

### Import as a package

```python
from ai_chat_backend.agents import FunctionCallAgent, MemoryFunctionCallAgent
from ai_chat_backend.llm import LLMClient
from ai_chat_backend.tools import ToolRegistry, WeatherTool, CalculatorTool
from ai_chat_backend.chat import SessionManager, MessageProcessor
from ai_chat_backend.config import LLMConfig

# Create LLM client
llm_config = LLMConfig()
llm_client = LLMClient(config=llm_config)

# Register tools
registry = ToolRegistry()
registry.register(WeatherTool())
registry.register(CalculatorTool())

# Create agent
agent = FunctionCallAgent(
    name="my_agent",
    llm_client=llm_client,
    tool_registry=registry
)
```

### Use in workflows

After installing with `pip install -e`, you can import the backend modules from anywhere:

```python
# In your workflow file (e.g., workflows/deepwiki/workflow.py)
from ai_chat_backend.agents import MemoryFunctionCallAgent
from ai_chat_backend.llm import LLMClient
from ai_chat_backend.tools import ToolRegistry
from ai_chat_backend.config import LLMConfig

# Your workflow code...
```

### Run the server

```bash
ai-chat-server
```

Or:

```bash
python run_server.py
```

## Project Structure

```
ai_chat/backend/
├── agents/          # Agent implementations
├── chat/            # Chat session and message processing
├── llm/             # LLM client
├── tools/           # Tool implementations
├── utils/           # Utility functions
├── app.py           # FastAPI application
├── config.py        # Configuration
└── run_server.py    # Server entry point
```

## Requirements

- Python >= 3.8
- FastAPI
- OpenAI
- See `requirements.txt` for full list

## License

MIT
