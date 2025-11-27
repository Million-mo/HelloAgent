# AI Chat

A multi-agent system with LLM integration.

## Installation

Install the package in editable mode:

```bash
cd ai_chat
pip install -e .
```

## Usage

```python
from ai_chat.agents import FunctionCallAgent, MemoryFunctionCallAgent
from ai_chat.llm import LLMClient
from ai_chat.tools import ToolRegistry, WeatherTool, CalculatorTool
from ai_chat.chat import SessionManager
from ai_chat.config import LLMConfig

# Create LLM client
llm_config = LLMConfig()
llm_client = LLMClient(config=llm_config)

# Create tool registry
registry = ToolRegistry()
registry.register(WeatherTool())
registry.register(CalculatorTool())

# Create agent
agent = FunctionCallAgent(
    name="demo_agent",
    llm_client=llm_client,
    tool_registry=registry
)

# Use the agent
response = agent.reply("What's the weather in Beijing?")
print(response)
```

## Development

Install development dependencies:

```bash
pip install -e .[dev]
```

Run tests:

```bash
pytest
```
