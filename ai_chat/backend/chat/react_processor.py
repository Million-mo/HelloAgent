"""React Agent processor for multi-turn tool calling with streaming support."""

import asyncio
import uuid
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from fastapi import WebSocket

from tools.registry import ToolRegistry
from .session import SessionManager


class ReactAgentProcessor:
    """
    React Agent 消息处理器，支持多轮工具调用。
    
    工作流程：
    1. Thought: LLM 分析问题并制定行动计划
    2. Action: 调用工具或返回最终答案
    3. Observation: 获取工具执行结果
    4. 重复 1-3，直到得出最终答案或达到最大步数
    """
    
    # React 提示词模板
    REACT_PROMPT_TEMPLATE = """你是一个具备推理和行动能力的AI助手。你可以通过思考分析问题，然后调用合适的工具来获取信息，最终给出准确的答案。

## 可用工具
{tools}

## 工作流程
请严格按照以下格式进行回应，每次只能执行一个步骤：

**Thought:** 分析问题，确定需要什么信息，制定策略。

**Action:** 选择合适的工具获取信息，格式必须为：
- 调用工具：`工具名[{{"参数名": "参数值"}}]`（参数必须是有效的 JSON 对象）
- 完成任务：`Finish[最终答案]`

## 重要提醒
1. 每次回应必须包含 **Thought** 和 **Action** 两部分
2. 工具调用格式：`工具名[{{"参数名": "参数值"}}]`
3. **参数必须是 JSON 对象**，即使只有一个参数也要用 JSON 格式
4. **当你获得了工具返回的结果后，应该立即使用 `Finish[答案]` 回答用户**
5. 不要重复调用相同的工具，除非你需要不同的参数
6. 如果工具返回的信息不够，继续使用其他工具或相同工具的不同参数

## 执行历史
{history}

现在开始你的推理和行动："""

    def __init__(
        self,
        llm_client,
        tool_registry: ToolRegistry,
        session_manager: SessionManager,
        max_steps: int = 10
    ):
        """
        初始化 React Agent 处理器。
        
        Args:
            llm_client: LLM 客户端实例
            tool_registry: 工具注册表
            session_manager: 会话管理器
            max_steps: 最大执行步数
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.session_manager = session_manager
        self.max_steps = max_steps
    
    async def process_streaming(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """
        使用 React 模式处理用户消息，支持流式输出。
        
        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
            user_input: 用户输入
            messages: 对话历史
        """
        # 添加用户消息
        messages.append({"role": "user", "content": user_input})
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        self.session_manager.set_cancel_flag(session_id, False)
        self.session_manager.set_current_message(session_id, message_id)
        
        try:
            # 开始 React 循环
            await self._react_loop(websocket, session_id, user_input, messages, message_id)
        
        except asyncio.CancelledError:
            # 任务被取消
            current_id = self.session_manager.get_current_message(session_id) or message_id
            await websocket.send_json({
                "type": "assistant_end",
                "messageId": current_id
            })
            return
        except Exception as e:
            print(f"Error in React processing: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"处理消息时出错: {str(e)}"
            })
        finally:
            # 清理状态
            self.session_manager.set_cancel_flag(session_id, False)
            self.session_manager.remove_current_message(session_id)
    
    async def _react_loop(
        self,
        websocket: WebSocket,
        session_id: str,
        user_input: str,
        messages: List[Dict[str, Any]],
        message_id: str
    ) -> None:
        """
        React 主循环：Thought → Action → Observation → 重复
        
        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
            user_input: 用户输入
            messages: 对话历史
            message_id: 消息 ID
        """
        history = []
        current_step = 0
        
        # 通知开始 React 流程
        await websocket.send_json({
            "type": "react_start",
            "messageId": message_id,
            "maxSteps": self.max_steps
        })
        
        while current_step < self.max_steps:
            current_step += 1
            
            # 检查是否取消
            if self.session_manager.get_cancel_flag(session_id):
                await websocket.send_json({
                    "type": "assistant_end",
                    "messageId": message_id
                })
                return
            
            # 发送步骤开始
            await websocket.send_json({
                "type": "react_step_start",
                "step": current_step,
                "messageId": message_id
            })
            
            # 1. 构建 React 提示词
            react_prompt = await self._build_react_prompt(user_input, history)
            
            # 添加调试日志
            print(f"\n[DEBUG] Step {current_step} Prompt:")
            print(f"{'='*50}")
            print(react_prompt)
            print(f"{'='*50}\n")
            
            # 2. 流式调用 LLM 获取 Thought 和 Action
            thought, action = await self._stream_react_response(
                websocket, session_id, react_prompt, message_id, current_step
            )
            
            if not thought or not action:
                # 解析失败，终止
                await websocket.send_json({
                    "type": "react_error",
                    "message": "无法解析 LLM 输出，流程终止",
                    "messageId": message_id
                })
                break
            
            # 3. 检查是否完成
            print(f"[DEBUG] 检查 Finish: action={action}, startswith('Finish')={action.startswith('Finish') if action else False}")
            
            # 支持多种 Finish 格式
            is_finish = False
            if action:
                action_lower = action.lower().strip()
                is_finish = (
                    action.startswith("Finish") or 
                    action.startswith("`Finish") or
                    action_lower.startswith("finish") or
                    "finish[" in action_lower
                )
            
            if is_finish:
                final_answer = self._parse_action_input(action)
                print(f"[DEBUG] 检测到 Finish，最终答案: {final_answer}")
                
                # 发送最终答案
                await websocket.send_json({
                    "type": "react_finish",
                    "answer": final_answer,
                    "messageId": message_id,
                    "totalSteps": current_step
                })
                
                # 保存助手消息
                messages.append({"role": "assistant", "content": final_answer})
                
                # 结束消息
                await websocket.send_json({
                    "type": "assistant_end",
                    "messageId": message_id
                })
                return
            
            # 4. 执行工具调用
            tool_name, tool_input = self._parse_action(action)
            
            # 添加调试日志
            print(f"[DEBUG] Action 原文: {action}")
            print(f"[DEBUG] 解析结果 - tool_name: {tool_name}, tool_input: {tool_input}")
            
            if not tool_name:
                observation = f"错误：无效的 Action 格式\n原文: {action}\n解析: tool_name={tool_name}, tool_input={tool_input}"
                await websocket.send_json({
                    "type": "react_observation",
                    "observation": observation,
                    "messageId": message_id
                })
            else:
                # 执行工具
                observation = await self._execute_tool(
                    websocket, session_id, tool_name, tool_input, message_id
                )
            
            # 5. 更新历史
            history.append(f"Thought: {thought}")
            history.append(f"Action: {action}")
            history.append(f"Observation: {observation}")
            
            # 发送步骤结束
            await websocket.send_json({
                "type": "react_step_end",
                "step": current_step,
                "messageId": message_id
            })
        
        # 达到最大步数
        final_answer = "抱歉，我无法在限定步数内完成这个任务。"
        await websocket.send_json({
            "type": "react_max_steps",
            "answer": final_answer,
            "messageId": message_id
        })
        
        messages.append({"role": "assistant", "content": final_answer})
        
        await websocket.send_json({
            "type": "assistant_end",
            "messageId": message_id
        })
    
    async def _build_react_prompt(self, user_input: str, history: List[str]) -> str:
        """
        构建 React 提示词。
        
        Args:
            user_input: 用户问题
            history: 执行历史
            
        Returns:
            React 提示词
        """
        # 获取工具描述
        tools_desc = self._get_tools_description()
        
        # 构建历史字符串
        history_str = "\n".join(history) if history else "（暂无执行历史）"
        
        # 格式化提示词
        prompt = self.REACT_PROMPT_TEMPLATE.format(
            tools=tools_desc,
            history=history_str
        )
        
        # 添加用户问题
        prompt += f"\n\n**用户问题:** {user_input}\n"
        
        return prompt
    
    def _get_tools_description(self) -> str:
        """获取工具描述列表"""
        tools = self.tool_registry.get_tools_definitions()
        if not tools:
            return "（暂无可用工具）"
        
        descriptions = []
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "未知")
            desc = func.get("description", "无描述")
            params = func.get("parameters", {})
            
            # 构建调用示例
            example = ""
            if params and "properties" in params:
                param_example = {}
                for param_name, param_info in params["properties"].items():
                    # 从 description 中提取示例值
                    param_desc = param_info.get("description", "")
                    if "e.g." in param_desc:
                        example_part = param_desc.split("e.g.")[1].strip().split(",")[0].strip()
                        param_example[param_name] = example_part
                    else:
                        param_example[param_name] = "..."
                
                import json
                example = f"\n  调用示例: `{name}[{json.dumps(param_example, ensure_ascii=False)}]`"
            
            descriptions.append(f"- **{name}**: {desc}{example}")
        
        return "\n".join(descriptions)
    
    async def _stream_react_response(
        self,
        websocket: WebSocket,
        session_id: str,
        prompt: str,
        message_id: str,
        step: int
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        流式调用 LLM 并解析 Thought 和 Action。
        
        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
            prompt: React 提示词
            message_id: 消息 ID
            step: 当前步数
            
        Returns:
            (thought, action) 元组
        """
        # 构建请求
        messages = [{"role": "user", "content": prompt}]
        response = await self.llm_client.client.chat.completions.create(
            model=self.llm_client.model,
            messages=messages,
            stream=True
        )
        
        # 收集响应内容
        content_buffer = ""
        
        async for chunk in response:
            # 检查取消标记
            if self.session_manager.get_cancel_flag(session_id):
                return None, None
            
            delta = chunk.choices[0].delta
            
            if delta.content:
                content_buffer += delta.content
                
                # 流式发送内容
                await websocket.send_json({
                    "type": "react_chunk",
                    "messageId": message_id,
                    "step": step,
                    "content": delta.content
                })
        
        # 解析 Thought 和 Action
        thought, action = self._parse_react_output(content_buffer)
        
        # 添加调试：输出完整的 LLM 响应
        print(f"\n[DEBUG] Step {step} LLM 完整响应:")
        print(f"{'='*50}")
        print(content_buffer)
        print(f"{'='*50}")
        print(f"[DEBUG] 解析结果 - Thought: {thought}")
        print(f"[DEBUG] 解析结果 - Action: {action}")
        print()
        
        # 发送解析结果
        if thought:
            await websocket.send_json({
                "type": "react_thought",
                "thought": thought,
                "messageId": message_id,
                "step": step
            })
        
        if action:
            await websocket.send_json({
                "type": "react_action",
                "action": action,
                "messageId": message_id,
                "step": step
            })
        
        return thought, action
    
    def _parse_react_output(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析 LLM 输出，提取 Thought 和 Action。
        
        Args:
            text: LLM 输出文本
            
        Returns:
            (thought, action) 元组
        """
        # 匹配 Thought
        thought_match = re.search(r"\*\*Thought:\*\*\s*(.*?)(?=\*\*Action:\*\*|$)", text, re.DOTALL)
        if not thought_match:
            thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|$)", text, re.DOTALL)
        
        # 匹配 Action
        action_match = re.search(r"\*\*Action:\*\*\s*(.*?)$", text, re.DOTALL)
        if not action_match:
            action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        
        return thought, action
    
    def _parse_action(self, action_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析 Action 文本，提取工具名称和输入。
        
        Args:
            action_text: Action 文本
            
        Returns:
            (tool_name, tool_input) 元组
        """
        # 清理 action 文本
        cleaned_action = action_text.strip()
        
        # 只在开头有“调用工具：”等前缀时才移除，避免误删 JSON 中的冒号
        if cleaned_action.startswith("调用工具：") or cleaned_action.startswith("调用工具:"):
            # 取第一个冒号后的内容
            if "：" in cleaned_action:
                cleaned_action = cleaned_action.split("：", 1)[1].strip()
            elif ":" in cleaned_action:
                cleaned_action = cleaned_action.split(":", 1)[1].strip()
        
        # 移除反引号（只移除首尾的反引号，不影响内部的引号）
        if cleaned_action.startswith('`'):
            cleaned_action = cleaned_action[1:]
        if cleaned_action.endswith('`'):
            cleaned_action = cleaned_action[:-1]
        cleaned_action = cleaned_action.strip()
        
        print(f"[DEBUG] _parse_action - 原文: {action_text}")
        print(f"[DEBUG] _parse_action - 清理后: {cleaned_action}")
        
        # 匹配格式：工具名[参数]（支持多行）
        match = re.match(r"(\w+)\[(.*)\]$", cleaned_action, re.DOTALL)
        if match:
            tool_name = match.group(1)
            tool_input = match.group(2).strip()
            print(f"[DEBUG] _parse_action - 匹配成功: tool_name={tool_name}, tool_input={tool_input}")
            return tool_name, tool_input
        
        print(f"[DEBUG] _parse_action - 匹配失败")
        return None, None
    
    def _parse_action_input(self, action_text: str) -> str:
        """
        解析 Action 输入内容。
        
        Args:
            action_text: Action 文本
            
        Returns:
            输入内容
        """
        # 支持多行匹配
        match = re.match(r"\w+\[(.*)\]", action_text.strip(), re.DOTALL)
        if match:
            return match.group(1).strip()
        
        match = re.match(r"`\w+\[(.*)\]`", action_text.strip(), re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return action_text.strip()
    
    async def _execute_tool(
        self,
        websocket: WebSocket,
        session_id: str,
        tool_name: str,
        tool_input: str,
        message_id: str
    ) -> str:
        """
        执行工具调用并返回结果。
        
        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
            tool_name: 工具名称
            tool_input: 工具输入
            message_id: 消息 ID
            
        Returns:
            工具执行结果
        """
        try:
            # 发送工具调用开始
            await websocket.send_json({
                "type": "tool_call_start",
                "toolName": tool_name,
                "toolInput": tool_input,
                "messageId": message_id
            })
            
            # 执行工具（tool_input 可能是 JSON 字符串或普通字符串）
            result = await self.tool_registry.execute_tool(tool_name, tool_input)
            
            # 发送工具调用结果
            await websocket.send_json({
                "type": "tool_call_end",
                "toolName": tool_name,
                "toolResult": result,
                "messageId": message_id
            })
            
            return result
        
        except Exception as e:
            error_msg = f"工具执行错误: {str(e)}"
            await websocket.send_json({
                "type": "tool_call_error",
                "toolName": tool_name,
                "error": error_msg,
                "messageId": message_id
            })
            return error_msg
