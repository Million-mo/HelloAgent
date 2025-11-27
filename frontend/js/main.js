// 主应用入口
import { WebSocketHandler } from './websocket-handler.js';
import { MessageHandler } from './message-handler.js';
import { ToolCallHandler } from './tool-call-handler.js';
import { ReactAgentHandler } from './react-agent-handler.js';
import { TodoHandler } from './todo-handler.js';
import { MarkdownRenderer } from './markdown-renderer.js';

class ChatApp {
    constructor() {
        this.currentMessageId = null;
        this.isStreaming = false;
        this.mode = 'agent';
        
        // 初始化各个处理器
        this.wsHandler = new WebSocketHandler(this);
        this.messageHandler = new MessageHandler(this);
        this.toolCallHandler = new ToolCallHandler(this);
        this.reactAgentHandler = new ReactAgentHandler(this);
        this.todoHandler = new TodoHandler(this);
        this.mdRenderer = new MarkdownRenderer();
        
        // Markdown实例
        this.md = this.mdRenderer.md;
        
        this.init();
    }

    init() {
        this.wsHandler.connect();
        this.setupEventListeners();
    }

    setupEventListeners() {
        const input = document.getElementById('messageInput');
        const messagesArea = document.getElementById('messagesArea');
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        input.addEventListener('input', () => {
            this.autoResizeInput(input);
        });
        
        messagesArea.addEventListener('click', (e) => {
            this.handleCopyButtonClick(e);
        });
    }

    handleMessage(data) {
        switch (data.type) {
            case 'user_message_received':
                this.messageHandler.addUserMessage(data.content);
                break;
            case 'assistant_start':
                this.messageHandler.removeTypingIndicator();
                this.currentMessageId = data.messageId;
                this.isStreaming = true;
                this.switchToStopButton();
                break;
            case 'assistant_chunk':
                const existingMsg = document.getElementById(data.messageId);
                if (!existingMsg) {
                    this.messageHandler.addAssistantMessage('', data.messageId);
                }
                this.messageHandler.updateMessage(data.messageId, data.content);
                break;
            case 'tool_calls_start':
                this.toolCallHandler.showToolCallsStart(data.tools);
                break;
            case 'tool_call':
                this.toolCallHandler.showToolCall(data.toolName, data.toolResult);
                break;
            case 'assistant_end':
                this.messageHandler.finalizeMessage(data.messageId);
                this.currentMessageId = null;
                this.isStreaming = false;
                this.switchToSendButton();
                this.enableInput(true);
                break;
            case 'planning_start':
                this.todoHandler.showPlanningMessage(data.messageId);
                break;
            case 'planning_status_update':
                this.todoHandler.updatePlanningStatus(data.messageId, data.status);
                break;
            case 'todo_list':
                this.todoHandler.removePlanningMessage(data.messageId);
                this.todoHandler.createTodoList(data.messageId, data.tasks);
                break;
            case 'todo_update':
                this.todoHandler.updateTodoItem(data.task_id, data.status, data.result, data.error);
                break;
            case 'react_start':
                this.messageHandler.removeTypingIndicator();
                this.currentMessageId = data.messageId;
                this.reactAgentHandler.currentStep = 0;
                this.reactAgentHandler.reactSteps = {};
                this.reactAgentHandler.addReactContainer(data.messageId, data.maxSteps);
                this.isStreaming = true;
                this.switchToStopButton();
                break;
            case 'react_step_start':
                this.reactAgentHandler.currentStep = data.step;
                this.reactAgentHandler.addReactStep(data.step, data.messageId);
                break;
            case 'react_chunk':
                this.reactAgentHandler.updateReactStepContent(data.step, data.content, this.currentMessageId);
                break;
            case 'react_thought':
                this.reactAgentHandler.showReactThought(data.step, data.thought, this.currentMessageId);
                break;
            case 'react_action':
                this.reactAgentHandler.showReactAction(data.step, data.action, this.currentMessageId);
                break;
            case 'tool_call_start':
                this.reactAgentHandler.showToolCallStart(data.toolName, data.toolInput, this.currentMessageId, this.reactAgentHandler.currentStep);
                break;
            case 'tool_call_end':
                this.reactAgentHandler.showToolCallEnd(data.toolName, data.toolResult, this.currentMessageId, this.reactAgentHandler.currentStep);
                break;
            case 'tool_call_error':
                this.reactAgentHandler.showToolCallError(data.toolName, data.error, this.currentMessageId, this.reactAgentHandler.currentStep);
                break;
            case 'react_observation':
                this.reactAgentHandler.showReactObservation(this.reactAgentHandler.currentStep, data.observation, this.currentMessageId);
                break;
            case 'react_step_end':
                this.reactAgentHandler.finalizeReactStep(data.step, this.currentMessageId);
                break;
            case 'react_finish':
                this.reactAgentHandler.showReactFinish(data.answer, data.totalSteps, this.currentMessageId);
                this.currentMessageId = null;
                this.isStreaming = false;
                this.switchToSendButton();
                this.enableInput(true);
                break;
            case 'react_max_steps':
                this.reactAgentHandler.showReactMaxSteps(data.answer, this.currentMessageId);
                this.currentMessageId = null;
                this.isStreaming = false;
                this.switchToSendButton();
                this.enableInput(true);
                break;
            case 'react_error':
                this.showError(data.message);
                this.isStreaming = false;
                this.switchToSendButton();
                this.enableInput(true);
                break;
        }
    }

    sendMessage() {
        if (this.isStreaming) {
            this.stopStreaming();
            return;
        }

        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message || !this.wsHandler.isConnected) {
            return;
        }

        const agentSelect = document.getElementById('agentSelect');
        const selectedAgent = agentSelect ? agentSelect.value : null;

        this.wsHandler.send({
            type: 'message',
            content: message,
            mode: this.mode,
            agent_name: selectedAgent
        });

        input.value = '';
        this.autoResizeInput(input);
        
        if (selectedAgent !== '任务规划师') {
            this.messageHandler.addTypingIndicator();
        }
        
        this.enableInput(false);
    }

    stopStreaming() {
        if (!this.currentMessageId) return;
        
        this.wsHandler.send({
            type: 'stop',
            messageId: this.currentMessageId
        });
        
        this.isStreaming = false;
        this.switchToSendButton();
    }

    toggleToolCall(toolId) {
        this.toolCallHandler.toggleToolCall(toolId);
    }

    autoResizeInput(input) {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    }

    handleCopyButtonClick(e) {
        const btn = e.target.closest('.copy-btn');
        if (!btn) return;
        
        const wrapper = btn.closest('.code-wrapper');
        const codeEl = wrapper ? wrapper.querySelector('.code-body pre code') : null;
        if (!codeEl) return;
        
        const lineContents = codeEl.querySelectorAll('.line-content');
        const text = Array.from(lineContents).map(n => n.innerText).join('\n');
        
        navigator.clipboard.writeText(text).then(() => {
            const originalHtml = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i> 已复制';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.innerHTML = originalHtml;
                btn.classList.remove('copied');
            }, 1500);
        }).catch(() => {
            btn.textContent = '复制失败';
            setTimeout(() => {
                btn.innerHTML = '<i class="fas fa-copy"></i> <i>复制</i>';
            }, 1500);
        });
    }

    switchToStopButton() {
        const sendBtn = document.getElementById('sendButton');
        if (sendBtn) {
            sendBtn.innerHTML = '<i class="fas fa-stop"></i><span>停止输出</span>';
            sendBtn.className = 'btn btn-danger send-btn';
        }
    }

    switchToSendButton() {
        const sendBtn = document.getElementById('sendButton');
        if (sendBtn) {
            sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i><span>发送</span>';
            sendBtn.className = 'btn btn-primary send-btn';
            sendBtn.disabled = false;
        }
    }

    enableInput(enable) {
        const input = document.getElementById('messageInput');
        input.disabled = !enable;
        
        if (enable) {
            input.focus();
        }
    }

    updateStatus(text, connected) {
        const status = document.getElementById('status');
        const statusDot = status.querySelector('.status-dot');
        const statusText = status.querySelector('.status-text');
        
        statusText.textContent = text;
        
        if (connected) {
            statusDot.classList.add('connected');
            statusDot.classList.remove('disconnected');
        } else {
            statusDot.classList.add('disconnected');
            statusDot.classList.remove('connected');
        }
    }

    showError(message) {
        const messagesArea = document.getElementById('messagesArea');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message assistant';
        errorDiv.innerHTML = `
            <div class="message-content" style="background: #fee2e2; border-color: #fecaca; color: #991b1b;">
                <div class="message-header">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>错误</span>
                </div>
                <div class="message-text">${message}</div>
            </div>
        `;
        messagesArea.appendChild(errorDiv);
        this.scrollToBottom();
    }

    scrollToBottom() {
        const messagesArea = document.getElementById('messagesArea');
        const isNearBottom = messagesArea.scrollHeight - messagesArea.scrollTop - messagesArea.clientHeight < 150;
        if (isNearBottom) {
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }
    }

    clearChat() {
        if (confirm('确定要清空所有对话记录吗？')) {
            localStorage.removeItem('chat_session_id');
            location.reload();
        }
    }
}

// 全局函数
function sendMessage() {
    window.chatApp.sendMessage();
}

function handleKeyPress(event) {
    window.chatApp.handleKeyPress(event);
}

function clearChat() {
    window.chatApp.clearChat();
}

function stopStreaming() {
    window.chatApp.stopStreaming();
}

// 导出全局函数
window.sendMessage = sendMessage;
window.clearChat = clearChat;
window.stopStreaming = stopStreaming;

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
});
