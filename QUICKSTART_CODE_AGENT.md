# 代码理解Agent - 快速启动指南

## 🚀 快速开始

### 1. 启动服务器

```bash
cd ai_chat/backend
python run_server.py
```

服务器启动后会看到：
```
INFO: CodeUnderstandingAgent 已注册
INFO: 已注册 11 个工具: ...
```

### 2. 测试工具功能（可选）

在新终端中运行：

```bash
cd test
python demo_code_tools.py
```

这会演示所有代码分析工具的功能。

### 3. 测试Agent对话

#### 方式A: 自动化测试

```bash
cd test
python test_code_understanding_agent.py
```

会自动运行4个测试场景：
- 分析项目结构
- 查找所有Agent
- 分析具体文件
- 搜索WebSocket相关代码

#### 方式B: 交互式对话

```bash
cd test
python test_code_understanding_agent.py interactive
```

然后可以直接输入问题与代码理解助手对话。

### 4. 在前端使用

1. 打开前端页面 `ai_chat/frontend/index.html`
2. 在消息发送前，通过API切换到代码理解助手：

```bash
curl -X POST "http://localhost:8000/agent/switch/your_session_id?agent_name=代码理解助手"
```

或者在WebSocket消息中指定agent_name（如果前端支持）。

## 💡 示例对话

### 示例1: 了解项目结构

**你**: 请分析一下这个项目的整体结构

**助手**: 
- 调用 `analyze_project_structure` 工具
- 展示项目目录树
- 解释主要模块的作用

### 示例2: 查找特定代码

**你**: 项目中有哪些Agent？请说明它们的功能

**助手**:
- 调用 `find_files` 查找 *agent*.py 文件
- 调用 `search_code` 搜索类定义
- 调用 `analyze_file` 分析各文件
- 总结各Agent的功能差异

### 示例3: 理解具体实现

**你**: 请帮我分析 function_call_agent.py 文件

**助手**:
- 调用 `analyze_file` 提取文件结构
- 调用 `read_file` 读取完整内容
- 解释核心功能和工作流程

### 示例4: 代码搜索

**你**: 在项目中查找所有使用了 WebSocket 的地方

**助手**:
- 调用 `search_code` 搜索 "WebSocket"
- 列出所有匹配的文件和代码位置
- 说明WebSocket的使用方式

## 🛠️ 可用工具

代码理解助手配备了以下工具：

1. **analyze_project_structure** - 分析项目目录结构
2. **search_code** - 在代码中搜索文本/正则表达式
3. **find_files** - 按文件名查找文件（支持通配符）
4. **analyze_file** - 分析单个文件的结构（类、函数等）
5. **read_file** - 读取文件内容
6. **list_directory** - 列出目录内容

## 📊 查看Agent状态

### 查看所有Agent

```bash
curl http://localhost:8000/agent/info
```

会返回所有已注册的Agent信息，包括"代码理解助手"。

### 查看Agent统计

```bash
curl http://localhost:8000/agent/stats
```

返回Agent系统的统计信息。

## 🎯 典型使用场景

### 场景1: 新项目入职
快速了解项目结构和核心模块

### 场景2: 代码审查
查找特定模式的代码，分析实现方式

### 场景3: 重构准备
理解模块依赖和调用关系

### 场景4: 问题定位
搜索特定功能的实现位置

### 场景5: 学习研究
分析优秀项目的架构设计

## 📝 提示和技巧

### 提问技巧

✅ **好的提问**:
- "分析 agents 目录的结构"
- "查找所有继承自 BaseAgent 的类"
- "解释 function_call_agent.py 的工作原理"

❌ **不太好的提问**:
- "看看代码"（太模糊）
- "有bug吗"（需要更具体的描述）

### 使用技巧

1. **分步提问**: 复杂问题可以分多次提问
2. **指定范围**: 在大项目中指定具体目录
3. **利用上下文**: Agent会记住对话历史
4. **明确意图**: 说清楚想了解什么方面

## 🔧 配置调整

### 修改工具限制

在 `ai_chat/backend/tools/code_analysis.py` 中可以调整：

```python
# 修改搜索结果数量
SearchCodeTool(..., max_results=50)

# 修改目录深度
AnalyzeProjectStructureTool(..., max_depth=6)

# 修改文件大小限制
AnalyzeFileTool(..., max_size=2*1024*1024)  # 2MB
```

### 修改Agent行为

在 `ai_chat/backend/app.py` 中：

```python
code_understanding_agent = CodeUnderstandingAgent(
    name="代码理解助手",
    llm_client=llm_client,
    tool_registry=tool_registry,
    session_manager=session_manager,
    max_iterations=20,  # 增加最大迭代次数
    system_prompt="自定义提示词..."  # 自定义行为
)
```

## 🐛 故障排查

### Agent未注册
检查 `app.py` 中是否正确创建和注册了Agent

### 工具执行失败
检查文件路径是否正确，是否有访问权限

### 搜索结果为空
检查搜索模式是否正确，目录路径是否存在

### 响应缓慢
减少搜索范围，限制结果数量

## 📚 更多文档

- **详细使用指南**: `CODE_UNDERSTANDING_AGENT_GUIDE.md`
- **实现总结**: `IMPLEMENTATION_SUMMARY.md`
- **代码注释**: 查看源代码中的docstring

## ✅ 验证安装

运行以下命令验证所有组件正常：

```bash
cd ai_chat/backend
python -c "from agents import CodeUnderstandingAgent; from tools.code_analysis import *; print('✓ 安装成功！')"
```

如果看到 "✓ 安装成功！"，说明所有组件都已正确安装。

---

**祝使用愉快！如有问题请查看详细文档或提issue。** 🎉
