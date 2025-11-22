from hello_agents.agents import FunctionCallAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.builtin import TerminalTool
import sys


def main() -> None:
    # 需提前配置 OPENAI_API_KEY，或在 HelloAgentsLLM 中传入 api_key/base_url
    llm = HelloAgentsLLM(
        model="qwen3-235b-a22b-instruct-2507",
        provider="qwen",
    )

    registry = ToolRegistry()
    
    # 注册文件系统探索工具
    terminal_tool = TerminalTool(
        workspace="/Users/million_mo/projects/agentscope/myagent",
        timeout=30,
    )
    registry.register_tool(terminal_tool, auto_expand=False)
    
    agent = FunctionCallAgent(
        name="explore-agent",
        system_prompt="""你是一个高效的代码库探索专家。你的任务是帮助用户深入理解项目结构、代码功能和设计架构。

## 核心职责
1. **项目结构分析**：探索目录层级、文件组织、模块划分
2. **功能解析**：分析模块和类的功能、职责、关键方法
3. **架构理解**：理解模块间的依赖关系、设计模式、数据流
4. **代码深度挖掘**：阅读关键代码实现，解释核心逻辑
5. **信息总结**：以清晰的方式呈现发现和分析结果

## 工作方法
- 使用terminal工具执行 `ls`, `cat`, `grep`, `find` 等命令探索文件
- 从高层目录开始，逐步深入到关键代码文件
- 追踪导入关系和依赖链
- 分析代码注释和文档字符串理解设计意图
- 在必要时使用搜索工具查找特定的实现或概念

## 输出规范
- 提供清晰的目录树和文件清单
- 用代码片段说明关键实现
- 用表格或列表组织信息
- 突出关键模块和核心功能
- 给出学习路径建议

## 注意事项
- 专注于理解 "是什么" 和 "为什么"，而不仅仅是 "怎么做"
- 识别项目的核心价值和独特之处
- 指出可能的优化或改进方向
- 保持探索的系统性和逻辑清晰
""",
        llm=llm,
        tool_registry=registry,
    )

    question = "我想查看/Users/million_mo/projects/agentscope/myagent/hello_agents/utils下有哪些文件，主要是做什么的？"


    print("Agent: ", end="", flush=True)
    for chunk in agent.stream_run(question):
        print(chunk, end="", flush=True)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
