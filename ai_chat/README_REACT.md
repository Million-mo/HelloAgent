# React Agent 架构升级说明

## 概述

已成功将原有的单次工具调用系统升级为支持多轮工具调用的 **React Agent 架构**。

## 主要变更

### 1. 后端改造

#### 新增文件
- **`chat/react_processor.py`**: React Agent 核心处理器
  - 支持多轮 Thought → Action → Observation 循环
  - 最大支持 10 步迭代（可配置）
  - 完整的流式输出支持

#### 修改文件
- **`app.py`**: 
  - 集成 `ReactAgentProcessor`
  - 支持模式选择（`mode`: `react` 或 `simple`）
  - 默认使用 React Agent 模式

### 2. 前端改造

#### 修改文件
- **`script.js`**:
  - 添加 React Agent 消息处理逻辑
  - 新增可视化方法：
    - `addReactContainer()`: 创建 React 容器
    - `addReactStep()`: 添加步骤
    - `showReactThought()`: 显示思考过程
    - `showReactAction()`: 显示行动
    - `showToolCallStart/End()`: 工具调用可视化
    - `showReactObservation()`: 显示观察结果
    - `showReactFinish()`: 显示最终答案

- **`style.css`**:
  - 完整的 React Agent UI 样式
  - 差异化的 Thought、Action、Observation 显示
  - 工具调用状态指示（进行中、成功、失败）

## React Agent 工作流程

```
用户问题
  ↓
Step 1: Thought (分析问题) → Action (调用工具/返回答案) → Observation (获取结果)
  ↓
Step 2: Thought (基于观察继续分析) → Action → Observation
  ↓
... (最多 10 步)
  ↓
Finish[最终答案]
```

## 使用方式

### 启动后端
```bash
cd test/ai_chat/backend
python app.py
```

### 启动前端
直接打开 `frontend/index.html` 或使用 HTTP 服务器：
```bash
cd test/ai_chat/frontend
python -m http.server 8080
```

### 消息格式

发送消息时可指定模式：
```javascript
{
    "type": "message",
    "content": "帮我查询北京的天气",
    "mode": "react"  // 或 "simple"
}
```

- **`react`**: 使用 React Agent（默认）- 支持多轮工具调用
- **`simple`**: 使用简单模式 - 单次工具调用

## React Agent 消息类型

### 后端 → 前端

| 消息类型 | 说明 | 数据字段 |
|---------|------|---------|
| `react_start` | React 流程开始 | `messageId`, `maxSteps` |
| `react_step_start` | 步骤开始 | `step`, `messageId` |
| `react_chunk` | 流式内容片段 | `step`, `content` |
| `react_thought` | 思考过程 | `step`, `thought` |
| `react_action` | 行动决策 | `step`, `action` |
| `tool_call_start` | 工具调用开始 | `toolName`, `toolInput` |
| `tool_call_end` | 工具调用成功 | `toolName`, `toolResult` |
| `tool_call_error` | 工具调用失败 | `toolName`, `error` |
| `react_observation` | 观察结果 | `observation` |
| `react_step_end` | 步骤结束 | `step` |
| `react_finish` | 完成并返回答案 | `answer`, `totalSteps` |
| `react_max_steps` | 达到最大步数 | `answer` |
| `react_error` | 错误 | `message` |

## 特性

### ✅ 已实现
1. **多轮工具调用**: 支持 React 模式的迭代推理
2. **流式输出**: 所有 LLM 响应支持流式传输
3. **可观测性**: 完整的 Thought、Action、Observation 可视化
4. **停止控制**: 支持暂停流式输出
5. **错误处理**: 完善的异常处理和用户反馈
6. **双模式支持**: React Agent 和简单模式可切换

### 🎯 核心优势
- **智能推理**: LLM 可以多轮调用工具，逐步解决复杂问题
- **透明过程**: 用户可以看到 AI 的完整思考和决策过程
- **灵活扩展**: 易于添加新工具和扩展能力

## 示例对话

**用户**: "北京今天天气如何？如果下雨就计算 100+200"

**React Agent 流程**:
```
步骤 1:
  Thought: 我需要先查询北京的天气
  Action: get_weather[北京]
  Observation: 北京今天晴天，温度 25℃

步骤 2:
  Thought: 天气是晴天，不需要计算
  Action: Finish[北京今天天气晴朗，温度 25℃，无需计算]
```

## 配置参数

### ReactAgentProcessor 参数
```python
ReactAgentProcessor(
    llm_client=llm_client,
    tool_registry=tool_registry,
    session_manager=session_manager,
    max_steps=10  # 最大执行步数，可根据需要调整
)
```

## 注意事项

1. **Prompt 工程**: React 提示词模板位于 `chat/react_processor.py` 中的 `REACT_PROMPT_TEMPLATE`
2. **工具注册**: 确保所有工具已正确注册到 `ToolRegistry`
3. **LLM 能力**: React 模式对 LLM 的推理能力有较高要求，建议使用 GPT-4 或类似模型
4. **停止条件**: LLM 需要主动调用 `Finish[答案]` 来结束流程

## 下一步优化方向

1. [ ] 添加模式切换 UI 控件
2. [ ] 支持自定义 React 提示词模板
3. [ ] 添加步骤重试机制
4. [ ] 优化 Action 解析的鲁棒性
5. [ ] 支持更多 Agent 模式（如 Plan-and-Solve）
