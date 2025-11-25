# 代码理解Agent使用指南

## 概述

代码理解Agent（CodeUnderstandingAgent）是一个专门用于理解和分析代码项目的智能助手。它可以帮助开发者快速了解项目结构、定位代码、分析功能实现等。

## 核心功能

### 1. 项目结构分析
- 分析整个项目的目录结构
- 识别项目的技术架构
- 理解项目组织方式

### 2. 代码搜索与导航
- 根据关键词搜索代码内容
- 支持正则表达式搜索
- 按文件名查找文件

### 3. 文件分析
- 分析单个文件的结构
- 提取类定义、函数定义
- 识别导入依赖

### 4. 技术问题解答
- 回答关于项目的技术问题
- 解释代码工作原理
- 提供改进建议

## 可用工具

代码理解Agent配备了以下专用工具：

### 1. analyze_project_structure
分析项目目录结构，生成项目文件树视图。

**参数:**
- `directory_path` (可选): 要分析的目录路径，默认为当前工作目录
- `max_depth` (可选): 目录树的最大深度，默认4层

**示例:**
```json
{
  "directory_path": ".",
  "max_depth": 4
}
```

### 2. search_code
在代码文件中搜索特定文本或正则表达式模式。

**参数:**
- `pattern` (必需): 要搜索的文本或正则表达式
- `directory_path` (可选): 搜索目录路径
- `case_sensitive` (可选): 是否区分大小写，默认false
- `max_results` (可选): 最大结果数，默认20

**示例:**
```json
{
  "pattern": "class.*Agent",
  "directory_path": "ai_chat/backend/agents",
  "case_sensitive": false,
  "max_results": 20
}
```

### 3. find_files
根据文件名模式查找文件，支持通配符。

**参数:**
- `name_pattern` (必需): 文件名模式，如 `*.py`, `config.*`
- `directory_path` (可选): 搜索目录路径
- `max_results` (可选): 最大结果数，默认50

**示例:**
```json
{
  "name_pattern": "*agent*.py",
  "directory_path": "ai_chat/backend"
}
```

### 4. analyze_file
分析代码文件的结构，提取导入语句、类定义、函数定义等。

**参数:**
- `file_path` (必需): 要分析的文件路径

**示例:**
```json
{
  "file_path": "ai_chat/backend/agents/base_agent.py"
}
```

### 5. read_file
读取文件完整内容。

**参数:**
- `file_path` (必需): 文件路径

### 6. list_directory
列出目录内容。

**参数:**
- `directory_path` (可选): 目录路径，默认当前目录

## 使用方法

### 1. 通过WebSocket API

在发送消息时指定agent_name为"代码理解助手"：

```javascript
{
  "type": "message",
  "content": "请分析这个项目的结构",
  "mode": "agent",
  "agent_name": "代码理解助手"
}
```

### 2. 通过HTTP API切换Agent

```bash
curl -X POST "http://localhost:8000/agent/switch/your_session_id?agent_name=代码理解助手"
```

### 3. 使用测试脚本

运行自动测试：
```bash
cd test
python test_code_understanding_agent.py
```

运行交互模式：
```bash
cd test
python test_code_understanding_agent.py interactive
```

## 典型使用场景

### 场景1: 快速了解新项目

**问题:** "请分析一下这个项目的整体结构，告诉我主要有哪些模块？"

**Agent行为:**
1. 使用 `analyze_project_structure` 分析目录结构
2. 识别主要模块和组件
3. 总结项目架构

### 场景2: 查找特定功能实现

**问题:** "项目中的WebSocket处理逻辑在哪里？"

**Agent行为:**
1. 使用 `search_code` 搜索 "WebSocket" 相关代码
2. 使用 `read_file` 读取相关文件
3. 解释WebSocket的实现方式

### 场景3: 理解某个文件

**问题:** "请帮我分析 base_agent.py 文件的功能"

**Agent行为:**
1. 使用 `analyze_file` 分析文件结构
2. 使用 `read_file` 读取完整内容
3. 解释类和方法的作用

### 场景4: 代码定位

**问题:** "找出所有定义了Agent的文件"

**Agent行为:**
1. 使用 `find_files` 查找包含"agent"的文件
2. 使用 `search_code` 搜索 "class.*Agent"
3. 列出所有Agent定义

## 最佳实践

### 1. 提供清晰的问题
- ✅ "请分析 agents 目录下的所有 Agent 类型"
- ❌ "看看代码"

### 2. 指定范围
- ✅ "在 backend/tools 目录中查找所有工具定义"
- ❌ "查找工具"

### 3. 分步骤提问
对于复杂问题，可以分多次提问：
1. "项目有哪些主要模块？"
2. "agents 模块是如何组织的？"
3. "FunctionCallAgent 的实现原理是什么？"

### 4. 利用上下文
Agent 会记住对话历史，可以进行连续提问：
- "分析 base_agent.py"
- "这个文件中的 BaseAgent 类有哪些子类？"
- "FunctionCallAgent 是如何继承 BaseAgent 的？"

## 配置说明

### 工具配置

在 `app.py` 中，代码分析工具使用默认配置：

```python
# 项目结构分析工具
AnalyzeProjectStructureTool()
# - base_dir: 当前工作目录
# - max_depth: 4层
# - 自动忽略 .git, __pycache__, node_modules 等

# 代码搜索工具
SearchCodeTool()
# - 支持的文件扩展名: .py, .js, .ts, .java, .cpp, .go 等
# - 自动忽略构建和依赖目录

# 查找文件工具
FindFilesTool()
# - 支持通配符搜索
# - 自动忽略构建和依赖目录

# 文件分析工具
AnalyzeFileTool()
# - 支持 Python 和 JavaScript/TypeScript 深度分析
# - 其他文件提供基础统计
```

### Agent配置

```python
code_understanding_agent = CodeUnderstandingAgent(
    name="代码理解助手",
    llm_client=llm_client,
    tool_registry=tool_registry,
    session_manager=session_manager,
    max_iterations=15,  # 最大迭代次数，足够处理复杂分析任务
)
```

## 限制和注意事项

### 1. 文件大小限制
- 读取文件的默认大小限制为 1MB
- 对于大文件，建议使用搜索工具定位关键部分

### 2. 搜索结果限制
- 代码搜索默认返回最多20个结果
- 文件查找默认返回最多50个文件
- 可以通过参数调整

### 3. 目录深度限制
- 项目结构分析默认深度为4层
- 可以通过参数调整，但过深会影响性能

### 4. 忽略的目录
默认忽略以下目录：
- `.git`
- `__pycache__`
- `node_modules`
- `.venv`, `venv`
- `.idea`, `.vscode`
- `dist`, `build`

## 扩展开发

### 添加新的代码分析工具

1. 在 `tools/code_analysis.py` 中创建新工具类
2. 继承 `BaseTool`
3. 实现必需的方法
4. 在 `app.py` 中注册工具

```python
class YourCustomTool(BaseTool):
    @property
    def name(self) -> str:
        return "your_tool_name"
    
    @property
    def description(self) -> str:
        return "工具描述"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                # 参数定义
            },
            "required": []
        }
    
    async def execute(self, **kwargs) -> str:
        # 工具实现
        pass
```

### 自定义 System Prompt

可以在创建 Agent 时提供自定义的 system_prompt：

```python
custom_agent = CodeUnderstandingAgent(
    name="自定义代码助手",
    llm_client=llm_client,
    tool_registry=tool_registry,
    session_manager=session_manager,
    max_iterations=15,
    system_prompt="你的自定义提示词..."
)
```

## 常见问题

### Q: 为什么搜索结果不完整？
A: 检查是否达到了结果数量限制，可以增加 `max_results` 参数。

### Q: 如何分析大型项目？
A: 建议分模块分析，先了解整体结构，再深入具体模块。

### Q: 工具执行失败怎么办？
A: 检查文件路径是否正确，是否有权限访问，文件是否存在。

### Q: 如何优化分析性能？
A: 
- 指定具体的搜索目录而非整个项目
- 使用精确的搜索模式
- 适当限制搜索深度和结果数量

## 更新日志

### v1.0.0 (当前版本)
- ✨ 实现代码理解Agent
- ✨ 支持项目结构分析
- ✨ 支持代码搜索和文件查找
- ✨ 支持文件内容和结构分析
- ✨ 支持多种编程语言

## 贡献

欢迎提交问题和改进建议！

## 许可证

与主项目保持一致
