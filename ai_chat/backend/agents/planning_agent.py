"""Planning Agent - 具备任务规划和管理能力的Agent."""

import asyncio
import uuid
import json
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict
from fastapi import WebSocket

from tools.registry import ToolRegistry
from chat.session import SessionManager
from .base_agent import BaseAgent
from utils.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 待办
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    BLOCKED = "blocked"          # 阻塞


class TaskPriority(str, Enum):
    """任务优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Task:
    """任务数据模型"""
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[str] = None  # 依赖的任务ID列表
    assigned_agent: Optional[str] = None  # 分配的Agent名称
    result: Optional[str] = None  # 任务执行结果
    error: Optional[str] = None  # 错误信息
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "assigned_agent": self.assigned_agent,
            "result": self.result,
            "error": self.error
        }


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.execution_order: List[str] = []
    
    def add_task(self, task: Task) -> None:
        """添加任务"""
        self.tasks[task.id] = task
        logger.debug(f"添加任务: {task.title} (ID: {task.id})")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, result: str = None, error: str = None) -> None:
        """更新任务状态"""
        task = self.tasks.get(task_id)
        if task:
            task.status = status
            if result:
                task.result = result
            if error:
                task.error = error
            logger.info(f"任务状态更新: {task.title} -> {status.value}")
    
    def get_executable_tasks(self) -> List[Task]:
        """获取可执行的任务（依赖已满足且状态为PENDING）"""
        executable = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            
            # 检查依赖是否都已完成
            dependencies_met = all(
                self.tasks.get(dep_id) and self.tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            
            if dependencies_met:
                executable.append(task)
        
        # 按优先级排序
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3
        }
        executable.sort(key=lambda t: priority_order.get(t.priority, 999))
        
        return executable
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def get_progress(self) -> Dict[str, Any]:
        """获取整体进度"""
        total = len(self.tasks)
        if total == 0:
            return {"total": 0, "completed": 0, "in_progress": 0, "pending": 0, "failed": 0, "progress": 0}
        
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS)
        pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
        
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "failed": failed,
            "progress": int((completed / total) * 100)
        }


class PlanningAgent(BaseAgent):
    """
    Planning Agent - 任务规划Agent
    
    **设计原则：职责单一**
    - PlanningAgent 仅负责任务分解和生成TodoList
    - 不考虑由哪个Agent执行，系统自动分配默认执行Agent
    - 通过Function Call获取信息辅助规划
    
    **核心功能：**
    1. 任务分解：将复杂任务分解为具体的子任务序列
    2. 依赖分析：识别任务之间的依赖关系
    3. 优先级设定：根据重要性和紧急程度设置优先级
    4. TodoList生成：生成结构化的待办事项清单
    5. 进度管理：跟踪任务状态(待办、进行中、已完成、失败)
    
    **工作流程：**
    1. 接收用户需求
    2. 使用LLM分析并生成TodoList
    3. 委托默认Agent按顺序执行
    4. 更新任务状态
    5. 汇总执行结果
    """
    
    def __init__(
        self,
        name: str,
        llm_client,
        tool_registry: ToolRegistry,
        session_manager: SessionManager,
        agent_manager=None,
        max_iterations: int = 20,
        system_prompt: Optional[str] = None
    ):
        """
        初始化 Planning Agent
        
        Args:
            name: Agent 名称
            llm_client: LLM 客户端实例
            tool_registry: 工具注册表(用于辅助规划)
            session_manager: 会话管理器
            agent_manager: Agent管理器(必须,用于调度其他Agent)
            max_iterations: 最大迭代次数
            system_prompt: 系统提示词
        """
        default_prompt = """你是一个专业的任务规划助手(Planning Agent)。

**你的核心职责:**
1. 项目理解: 先分析当前项目环境、代码结构、已有文件等上下文信息
2. 任务分解: 基于项目理解，将用户需求分解为具体、可执行的子任务
3. 依赖分析: 识别任务之间的依赖关系，确保执行顺序合理
4. 优先级设定: 根据任务的重要性和紧急程度设置优先级
5. 进度跟踪: 生成清晰的TodoList，便于跟踪任务进度

**重要原则:**
- **先理解项目，再规划任务** - 这是最重要的原则
- 你可以使用工具(list_directory, read_file等)分析项目结构
- 基于项目实际情况制定合理的任务计划
- 你只负责规划，不直接执行任务
- 系统会自动分配Agent执行任务

**工作流程:**
1. 接收用户需求
2. 使用工具分析项目结构(list_directory, read_file)
3. 理解现有代码和文件组织
4. 基于项目上下文制定任务计划
5. 生成结构化的TodoList

请以结构化的方式规划任务，生成清晰的待办事项清单。"""
        
        super().__init__(
            name=name,
            agent_type="planning",
            llm_client=llm_client,
            tool_registry=tool_registry,
            session_manager=session_manager,
            system_prompt=system_prompt or default_prompt,
            max_iterations=max_iterations
        )
        
        self.agent_manager = agent_manager
        self.max_iterations = max_iterations
        
        # 验证agent_manager是否存在
        if not self.agent_manager:
            logger.warning(f"PlanningAgent '{self.name}' 初始化时未提供agent_manager,将无法委托任务")
        
        # 会话级任务管理器
        self._session_task_managers: Dict[str, TaskManager] = {}
        
        logger.info(f"PlanningAgent '{self.name}' 已初始化")
        logger.debug(f"最大迭代次数: {self.max_iterations}")
    
    def _get_task_manager(self, session_id: str) -> TaskManager:
        """获取会话的任务管理器"""
        if session_id not in self._session_task_managers:
            self._session_task_managers[session_id] = TaskManager()
        return self._session_task_managers[session_id]
    
    async def run(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """
        执行 Planning Agent 主循环
        
        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
            user_input: 用户输入
            messages: 对话历史
        """
        self._ensure_system_prompt(messages)
        
        # 添加用户消息
        messages.append({"role": "user", "content": user_input})
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        self.session_manager.set_cancel_flag(session_id, False)
        self.session_manager.set_current_message(session_id, message_id)
        
        task_manager = self._get_task_manager(session_id)
        
        try:
            # 第一步：项目理解阶段 - 使用工具分析项目
            await websocket.send_json({
                "type": "planning_start",
                "messageId": message_id
            })
            
            # 先进行项目分析，获取上下文信息
            project_context = await self._analyze_project_context(
                websocket, session_id, messages, message_id, user_input
            )
            
            # 更新planning气泡状态为"正在生成任务计划..."
            await websocket.send_json({
                "type": "planning_status_update",
                "messageId": message_id,
                "status": "正在生成任务计划..."
            })
            
            # 第二步：基于项目理解生成任务计划
            tasks = await self._plan_tasks(
                websocket, session_id, messages, message_id, user_input, project_context
            )
            
            if not tasks:
                await websocket.send_json({
                    "type": "assistant_start",
                    "messageId": message_id
                })
                await websocket.send_json({
                    "type": "assistant_chunk",
                    "messageId": message_id,
                    "content": "抱歉，我无法为这个任务制定执行计划。请提供更多信息或换一个任务。"
                })
                await websocket.send_json({
                    "type": "assistant_end",
                    "messageId": message_id
                })
                return
            
            # 添加任务到管理器
            for task in tasks:
                task_manager.add_task(task)
            
            # 发送任务列表到前端（TodoList形式）
            await websocket.send_json({
                "type": "todo_list",
                "messageId": message_id,
                "tasks": [task.to_dict() for task in tasks]
            })
            
            # 第二步：逐个执行任务
            await self._execute_tasks_sequentially(websocket, session_id, messages, message_id, task_manager)
            
            # 第三步：发送完成消息
            await self._send_completion_summary(websocket, session_id, message_id, task_manager)
            
        except asyncio.CancelledError:
            logger.info(f"[{self.name}] 任务被取消 (session: {session_id})")
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": message_id
            })
            return
        except Exception as e:
            logger.error(f"[{self.name}] 处理错误 (session: {session_id}): {e}", exc_info=True)
            await websocket.send_json({
                "type": "error",
                "message": f"处理消息时出错: {str(e)}"
            })
        finally:
            self.session_manager.set_cancel_flag(session_id, False)
            self.session_manager.remove_current_message(session_id)
    
    async def _analyze_project_context(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        message_id: str,
        user_input: str
    ) -> str:
        """
        分析项目上下文 - 使用工具了解项目结构
        
        Returns:
            项目上下文描述
        """
        logger.info(f"[{self.name}] 开始分析项目上下文")
        
        analysis_prompt = f"""用户需求: {user_input}

在制定任务计划之前，请先分析当前项目环境。

**分析步骤：**
1. 使用 list_directory 工具查看当前目录结构
2. 识别关键文件和目录
3. 如有必要，使用 read_file 工具查看重要配置文件或代码文件
4. 总结项目结构和技术栈

**输出要求：**
请用中文简洁描述项目情况，包括：
- 项目类型（如：Python后端、React前端、AI应用等）
- 关键目录和文件
- 技术栈和框架
- 与用户需求相关的现有代码

开始分析项目..."""
        
        # 创建项目分析的消息历史
        analysis_messages = messages.copy()
        analysis_messages.append({"role": "user", "content": analysis_prompt})
        
        # 调用LLM进行项目分析（允许使用工具）
        request_params = {
            "model": self.llm_client.model,
            "messages": analysis_messages,
            "stream": True,
            "tools": self.tool_registry.get_tools_definitions()  # 允许使用工具
        }
        
        response = await self.llm_client.client.chat.completions.create(**request_params)
        
        # 处理流式响应（支持工具调用）
        tool_calls_dict = {}
        content_buffer = ""
        max_tool_iterations = 5  # 最多允许5次工具调用
        iteration = 0
        
        while iteration < max_tool_iterations:
            async for chunk in response:
                if self.session_manager.get_cancel_flag(session_id):
                    return ""
                
                delta = chunk.choices[0].delta
                
                # 收集工具调用
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        index = tool_call.index
                        if index not in tool_calls_dict:
                            tool_calls_dict[index] = {
                                "id": tool_call.id,
                                "type": tool_call.type or "function",
                                "function": {"name": "", "arguments": ""}
                            }
                        
                        if tool_call.function:
                            if tool_call.function.name:
                                tool_calls_dict[index]["function"]["name"] = tool_call.function.name
                            if tool_call.function.arguments:
                                tool_calls_dict[index]["function"]["arguments"] += tool_call.function.arguments
                
                # 收集内容
                if delta.content:
                    content_buffer += delta.content
            
            # 检查是否有工具调用
            tool_calls = list(tool_calls_dict.values()) if tool_calls_dict else None
            
            if tool_calls:
                # 保存assistant消息
                analysis_messages.append({
                    "role": "assistant",
                    "content": content_buffer if content_buffer else None,
                    "tool_calls": tool_calls
                })
                
                # 通知前端工具调用开始
                tool_names = [tc["function"]["name"] for tc in tool_calls]
                await websocket.send_json({
                    "type": "tool_calls_start",
                    "tools": tool_names
                })
                
                # 执行工具调用
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = tool_call["function"]["arguments"]
                    
                    logger.info(f"[{self.name}] 项目分析中调用工具: {tool_name}")
                    
                    # 执行工具
                    tool_result = await self.tool_registry.execute_tool(tool_name, tool_args)
                    
                    # 通知前端工具调用结果
                    await websocket.send_json({
                        "type": "tool_call",
                        "toolName": tool_name,
                        "toolResult": tool_result
                    })
                    
                    # 添加工具结果
                    analysis_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": tool_name,
                        "content": tool_result
                    })
                
                # 继续对话，让LLM基于工具结果继续分析
                iteration += 1
                tool_calls_dict = {}
                content_buffer = ""
                
                request_params["messages"] = analysis_messages
                response = await self.llm_client.client.chat.completions.create(**request_params)
            else:
                # 没有工具调用，分析完成
                break
        
        # 保存最终分析结果
        if content_buffer:
            analysis_messages.append({"role": "assistant", "content": content_buffer})
        
        logger.info(f"[{self.name}] 项目分析完成")
        logger.debug(f"[{self.name}] 项目上下文: {content_buffer[:200]}...")
        
        # 向前端发送项目分析结果
        if content_buffer:
            analysis_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
            await websocket.send_json({
                "type": "assistant_start",
                "messageId": analysis_msg_id
            })
            await websocket.send_json({
                "type": "assistant_chunk",
                "messageId": analysis_msg_id,
                "content": f"**📊 项目分析结果：**\n\n{content_buffer}"
            })
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": analysis_msg_id
            })
        
        return content_buffer if content_buffer else "无法获取项目上下文信息"
    
    async def _plan_tasks(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        message_id: str,
        user_input: str,
        project_context: str
    ) -> List[Task]:
        """
        基于用户输入和项目上下文生成任务计划
        
        Args:
            websocket: WebSocket连接
            session_id: 会话ID
            messages: 历史消息
            message_id: 消息ID
            user_input: 用户输入
            project_context: 项目分析结果
        
        Returns:
            任务列表
        """
        planning_prompt = f"""现在你已经了解了项目情况：

**项目分析结果:**
{project_context}

**用户需求:**
{user_input}

请基于以上项目分析结果，将用户需求分解为具体的子任务，并返回JSON格式的任务列表。

**重要要求：**
1. 必须严格按照JSON格式返回
2. 不要添加任何解释性文字、markdown标记或其他内容
3. 直接输出JSON对象，不要用```json```包裹
4. 确保JSON格式正确，可以被直接解析
5. **关键**: 任务规划要基于项目实际结构，而不是凭空想象
6. 任务描述要具体、可执行，并考虑项目实际情况
7. 合理设置任务优先级和依赖关系

返回的JSON应包含一个tasks数组，每个任务包含以下字段：
- id: 任务唯一标识（简短字符串，如task1、task2）
- title: 任务标题（简洁明了）
- description: 详细描述（具体可执行的内容，基于项目实际结构）
- priority: 优先级（必须是: low、medium、high 或 critical）
- dependencies: 依赖的任务ID列表（数组，如果没有依赖则为空数组[]）

注意：不需要指定执行Agent，系统会自动分配。

输出示例：
{{
  "tasks": [
    {{
      "id": "task1",
      "title": "分析backend/agents/planning_agent.py",
      "description": "查看planning_agent.py的实现，理解当前任务规划逻辑",
      "priority": "high",
      "dependencies": []
    }},
    {{
      "id": "task2",
      "title": "添加项目分析功能",
      "description": "在planning_agent.py中添加_analyze_project_context方法",
      "priority": "high",
      "dependencies": ["task1"]
    }}
  ]
}}

现在请直接返回JSON对象："""
        
        # 调用LLM生成计划
        messages.append({"role": "user", "content": planning_prompt})
        
        request_params = {
            "model": self.llm_client.model,
            "messages": messages,
            "stream": True
        }
        
        response = await self.llm_client.client.chat.completions.create(**request_params)
        
        content_buffer = ""
        async for chunk in response:
            if self.session_manager.get_cancel_flag(session_id):
                return []
            
            delta = chunk.choices[0].delta
            if delta.content:
                content_buffer += delta.content
        
        messages.append({"role": "assistant", "content": content_buffer})
        
        # 记录原始输出用于调试
        logger.debug(f"[{self.name}] LLM原始输出: {content_buffer[:500]}...")
        
        # 解析JSON
        try:
            # 清理可能的markdown标记
            cleaned_content = content_buffer.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            if cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()
            
            # 提取JSON部分
            json_start = cleaned_content.find("{")
            json_end = cleaned_content.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = cleaned_content[json_start:json_end]
                logger.debug(f"[{self.name}] 提取的JSON: {json_str[:200]}...")
                
                task_data = json.loads(json_str)
                
                if "tasks" not in task_data:
                    logger.error(f"[{self.name}] JSON中缺少tasks字段")
                    await websocket.send_json({
                        "type": "error",
                        "message": "任务规划失败：返回的JSON格式不正确，缺少tasks字段"
                    })
                    return []
                
                tasks = []
                for i, task_dict in enumerate(task_data.get("tasks", [])):
                    try:
                        task = Task(
                            id=task_dict["id"],
                            title=task_dict["title"],
                            description=task_dict["description"],
                            priority=TaskPriority(task_dict.get("priority", "medium")),
                            dependencies=task_dict.get("dependencies", []),
                            assigned_agent=task_dict.get("assigned_agent")
                        )
                        tasks.append(task)
                        logger.debug(f"[{self.name}] 解析任务 {i+1}: {task.title}")
                    except Exception as task_error:
                        logger.error(f"[{self.name}] 解析任务{i+1}失败: {task_error}, 数据: {task_dict}")
                        continue
                
                if tasks:
                    logger.info(f"[{self.name}] 成功规划了 {len(tasks)} 个任务")
                    return tasks
                else:
                    logger.error(f"[{self.name}] 没有成功解析任何任务")
                    await websocket.send_json({
                        "type": "error",
                        "message": "任务规划失败：无法解析任务数据"
                    })
            else:
                logger.error(f"[{self.name}] 无法在返回内容中找到有效的JSON对象")
                logger.error(f"[{self.name}] 完整输出: {content_buffer}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"任务规划失败：模型未返回有效的JSON格式。返回内容: {content_buffer[:200]}"
                })
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] JSON解析错误: {e}")
            logger.error(f"[{self.name}] 尝试解析的内容: {json_str if 'json_str' in locals() else content_buffer}")
            await websocket.send_json({
                "type": "error",
                "message": f"任务规划失败：JSON解析错误 - {str(e)}"
            })
        except Exception as e:
            logger.error(f"[{self.name}] 解析任务计划失败: {e}", exc_info=True)
            logger.error(f"[{self.name}] 完整输出: {content_buffer}")
            await websocket.send_json({
                "type": "error",
                "message": f"任务规划失败：{str(e)}"
            })
        
        return []
    
    async def _execute_tasks_sequentially(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        message_id: str,
        task_manager: TaskManager
    ) -> None:
        """按顺序逐个执行任务"""
        iteration = 0
        
        while iteration < self.max_iterations:
            # 检查取消信号
            if self.session_manager.get_cancel_flag(session_id):
                logger.info(f"[{self.name}] 收到取消信号")
                return
            
            # 获取可执行的任务
            executable_tasks = task_manager.get_executable_tasks()
            
            if not executable_tasks:
                # 检查是否还有未完成的任务
                pending_or_progress = [
                    t for t in task_manager.get_all_tasks()
                    if t.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
                ]
                if not pending_or_progress:
                    logger.info(f"[{self.name}] 所有任务执行完成")
                    break
                else:
                    logger.warning(f"[{self.name}] 存在阻塞的任务")
                    break
            
            # 一次执行一个任务
            task = executable_tasks[0]
            await self._execute_single_task(websocket, session_id, messages, message_id, task, task_manager)
            iteration += 1
    
    async def _send_completion_summary(
        self,
        websocket: WebSocket,
        session_id: str,
        message_id: str,
        task_manager: TaskManager
    ) -> None:
        """发送任务完成总结""" 
        progress = task_manager.get_progress()
        
        summary_message_id = f"msg_{uuid.uuid4().hex[:8]}"
        await websocket.send_json({
            "type": "assistant_start",
            "messageId": summary_message_id
        })
        
        summary = f"\n✅ **任务执行完成**\n\n"
        summary += f"- 总任务数: {progress['total']}\n"
        summary += f"- 已完成: {progress['completed']}\n"
        summary += f"- 失败: {progress['failed']}\n"
        
        await websocket.send_json({
            "type": "assistant_chunk",
            "messageId": summary_message_id,
            "content": summary
        })
        
        await websocket.send_json({
            "type": "assistant_end",
            "messageId": summary_message_id
        })
    
    async def _execute_single_task(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        message_id: str,
        task: Task,
        task_manager: TaskManager
    ) -> None:
        """执行单个任务 - 委托给其他Agent"""
        logger.info(f"[{self.name}] 开始执行任务: {task.title}")
        
        # 更新状态为进行中
        task_manager.update_task_status(task.id, TaskStatus.IN_PROGRESS)
        
        # 通知前端任务开始
        await websocket.send_json({
            "type": "todo_update",
            "task_id": task.id,
            "status": "in_progress"
        })
        
        try:
            # PlanningAgent不直接执行任务,而是委托给其他Agent
            result = await self._delegate_to_agent(
                websocket, session_id, messages, task
            )
            
            # 更新状态为完成
            task_manager.update_task_status(task.id, TaskStatus.COMPLETED, result=result)
            
            # 通知前端任务完成
            await websocket.send_json({
                "type": "todo_update",
                "task_id": task.id,
                "status": "completed",
                "result": result
            })
            
        except Exception as e:
            logger.error(f"[{self.name}] 任务执行失败: {task.title}, 错误: {e}")
            task_manager.update_task_status(task.id, TaskStatus.FAILED, error=str(e))
            
            # 通知前端任务失败
            await websocket.send_json({
                "type": "todo_update",
                "task_id": task.id,
                "status": "failed",
                "error": str(e)
            })
    
    async def _delegate_to_agent(
        self,
        websocket: WebSocket,
        session_id: str,
        messages: List[Dict[str, Any]],
        task: Task
    ) -> str:
        """
        委托给其他Agent执行任务
        
        PlanningAgent的核心职责是规划和调度,不直接执行任务。
        所有任务都应该委托给专门的执行Agent。
        """
        # 确定要使用的Agent
        agent_name = task.assigned_agent
        
        # 如果任务没有指定Agent,智能选择默认执行Agent
        if not agent_name:
            # 使用通用助理(FunctionCallAgent)作为默认执行Agent
            agent_name = "通用助理"
            logger.info(f"[{self.name}] 任务 '{task.title}' 未指定Agent,使用默认: {agent_name}")
        
        # 获取目标Agent
        agent = self.agent_manager.get_agent(agent_name) if self.agent_manager else None
        
        if not agent:
            error_msg = f"无法找到Agent '{agent_name}' 来执行任务 '{task.title}'"
            logger.error(f"[{self.name}] {error_msg}")
            raise ValueError(error_msg)
        
        logger.info(f"[{self.name}] 委托给 Agent '{agent_name}' 执行任务: {task.title}")
        
        # 创建任务特定的消息历史(避免污染主对话)
        task_messages = []
        
        # 执行Agent并收集输出
        output_buffer = []
        
        class OutputCapturingWebSocket:
            """捕获Agent输出的WebSocket包装器"""
            def __init__(self, real_ws, buffer):
                self.real_ws = real_ws
                self.buffer = buffer
            
            async def send_json(self, data):
                # 捕获实际的回复内容
                if data.get("type") == "assistant_chunk":
                    self.buffer.append(data.get("content", ""))
                # 同时转发到前端显示
                if self.real_ws:
                    await self.real_ws.send_json(data)
        
        wrapped_ws = OutputCapturingWebSocket(websocket, output_buffer)
        
        # 执行委托的Agent
        await agent.run(wrapped_ws, session_id, task.description, task_messages)
        
        # 返回执行结果
        result = "".join(output_buffer)
        return result if result else "任务已完成"
    

    def get_info(self) -> Dict[str, Any]:
        """获取 Agent 信息"""
        base_info = super().get_info()
        base_info.update({
            "max_iterations": self.max_iterations,
            "capabilities": [
                "task_decomposition",
                "task_scheduling",
                "progress_tracking",
                "agent_collaboration"
            ]
        })
        return base_info
