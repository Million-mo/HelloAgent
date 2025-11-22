class ChatApp {
    constructor() {
        this.ws = null;
        this.sessionId = this.getSessionId();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.isConnected = false;
        this.currentMessageId = null;
        this.messageBuffers = {}; // 存储流式消息缓冲
        this.renderLocks = {}; // 渲染锁，避免高频重渲染
        this.isStreaming = false; // 是否正在流式输出
        this.mode = 'react'; // 默认使用 React Agent 模式
        this.currentStep = 0; // 当前 React 步骤
        this.reactSteps = {}; // 存储 React 步骤信息
        this.init();
        this.initMarked();
    }

    initMarked() {
        // 配置 markdown-it（完全按照最佳实践结构）
        const self = this;
        if (typeof markdownit !== 'undefined') {
            this.md = markdownit({
                html: true,
                linkify: true,
                typographer: true,
                breaks: true,
                highlight: function(code, lang) {
                    let highlighted = '';
                    if (window.hljs && lang && hljs.getLanguage(lang)) {
                        highlighted = hljs.highlight(code, { language: lang, ignoreIllegals: true }).value;
                        // 移除 highlight.js 自动添加的行尾换行符，这可能导致额外的空行
                        if (highlighted.endsWith('\n')) {
                            highlighted = highlighted.slice(0, -1);
                        }
                    } else if (window.hljs) {
                        highlighted = hljs.highlightAuto(code).value;
                    } else {
                        highlighted = self.escapeHtml(code);
                    }
                    
                    // 按行拆分，生成带行号的 HTML
                    const rawLines = highlighted.split('\n');
                    // 确保即使是空行也包含零宽字符，但不需要移除末尾空行，因为 split('\n') 已经处理了
                    // 移除最后可能的空行 (如果 highlight.js 留下了)
                    // if (rawLines.length && rawLines[rawLines.length - 1].trim() === '') {
                    //     rawLines.pop();
                    // }
                    
                    const linesHtml = rawLines.map((lineHtml, idx) => {
                        const lineContent = lineHtml || '&#8203;'; // 空行用零宽字符
                        // 移除行尾多余的空格，避免行号和内容之间出现巨大间距
                        const trimmedLineContent = lineContent.replace(/\s+$/, '');
                        return `<div class="line"><span class="line-number">${idx + 1}</span><span class="line-content">${trimmedLineContent}</span></div>`;
                    }).join('');
                    
                    const langLabel = (lang || 'plaintext').toUpperCase();
                    
                    // 正确结构：header 和 code-body 分离
                    return `<div class="code-wrapper">
                                <div class="code-header">
                                    <span class="code-lang">${langLabel}</span>
                                    <button class="copy-btn" data-lang="${langLabel}">
                                        <i class="fas fa-copy"></i> <i>复制</i>
                                    </button>
                                </div>
                                <div class="code-body">
                                    <pre><code class="hljs language-${lang || ''}">${linesHtml}</code></pre>
                                </div>
                            </div>`;
                }
            });
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getSessionId() {
        let sessionId = localStorage.getItem('chat_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('chat_session_id', sessionId);
        }
        return sessionId;
    }

    autoResizeInput(input) {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    }

    handleCopyButtonClick(e) {
        const btn = e.target.closest('.copy-btn');
        if (!btn) return;
        
        // 找到同一个 code-wrapper 下的代码文本
        const wrapper = btn.closest('.code-wrapper');
        const codeEl = wrapper ? wrapper.querySelector('.code-body pre code') : null;
        if (!codeEl) return;
        
        // 获取纯文本（从所有 .line-content 中提取）
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

    init() {
        this.connectWebSocket();
        this.setupEventListeners();
    }

    setupEventListeners() {
        const input = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendButton');
        const messagesArea = document.getElementById('messagesArea');
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 自动调整输入框高度
        input.addEventListener('input', () => {
            this.autoResizeInput(input);
        });
        
        // 复制按钮事件委托（委托到 messagesArea 容器，流式渲染也有效）
        messagesArea.addEventListener('click', (e) => {
            this.handleCopyButtonClick(e);
        });
    }

    connectWebSocket() {
        // 前后端分离：指定后端服务地址
        const backendHost = 'localhost:8000'; // 暴露的公共 URL
        const wsUrl = `ws://${backendHost}/ws/${this.sessionId}`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            this.setupWebSocketEvents();
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.updateStatus('连接失败', false);
            this.scheduleReconnect();
        }
    }

    setupWebSocketEvents() {
        this.ws.onopen = () => {
            console.log('WebSocket连接已建立');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.updateStatus('已连接', true);
            this.enableInput(true);
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket连接已关闭');
            this.isConnected = false;
            this.updateStatus('已断开', false);
            this.enableInput(false);
            this.scheduleReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
            this.updateStatus('连接错误', false);
        };
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            this.updateStatus(`重连中... (${this.reconnectAttempts})`, false);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, this.reconnectDelay);
        } else {
            this.updateStatus('连接失败', false);
            this.showError('无法连接到服务器，请刷新页面重试');
        }
    }

    handleMessage(data) {
        switch (data.type) {
            case 'user_message_received':
                this.addUserMessage(data.content);
                break;
            case 'assistant_start':
                this.removeTypingIndicator();
                this.currentMessageId = data.messageId;
                this.addAssistantMessage('', data.messageId);
                this.isStreaming = true;
                this.switchToStopButton();
                break;
            case 'assistant_chunk':
                this.updateMessage(data.messageId, data.content);
                break;
            case 'tool_calls_start':
                this.showToolCallsStart(data.tools);
                break;
            case 'tool_call':
                this.showToolCall(data.toolName, data.toolResult);
                break;
            case 'assistant_end':
                this.finalizeMessage(data.messageId);
                this.currentMessageId = null;
                this.isStreaming = false;
                this.switchToSendButton();
                this.enableInput(true);
                break;
            // React Agent 相关消息类型
            case 'react_start':
                this.removeTypingIndicator();
                this.currentMessageId = data.messageId;
                this.currentStep = 0;
                this.reactSteps = {};
                this.addReactContainer(data.messageId, data.maxSteps);
                this.isStreaming = true;
                this.switchToStopButton();
                break;
            case 'react_step_start':
                this.currentStep = data.step;
                this.addReactStep(data.step, data.messageId);
                break;
            case 'react_chunk':
                this.updateReactStepContent(data.step, data.content);
                break;
            case 'react_thought':
                this.showReactThought(data.step, data.thought);
                break;
            case 'react_action':
                this.showReactAction(data.step, data.action);
                break;
            case 'tool_call_start':
                this.showToolCallStart(data.toolName, data.toolInput);
                break;
            case 'tool_call_end':
                this.showToolCallEnd(data.toolName, data.toolResult);
                break;
            case 'tool_call_error':
                this.showToolCallError(data.toolName, data.error);
                break;
            case 'react_observation':
                this.showReactObservation(this.currentStep, data.observation);
                break;
            case 'react_step_end':
                this.finalizeReactStep(data.step);
                break;
            case 'react_finish':
                this.showReactFinish(data.answer, data.totalSteps);
                this.currentMessageId = null;
                this.isStreaming = false;
                this.switchToSendButton();
                this.enableInput(true);
                break;
            case 'react_max_steps':
                this.showReactMaxSteps(data.answer);
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

    addUserMessage(content) {
        const messagesArea = document.getElementById('messagesArea');
        const messageDiv = this.createMessageElement('user', content);
        messagesArea.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addAssistantMessage(content, messageId) {
        const messagesArea = document.getElementById('messagesArea');
        const messageDiv = this.createMessageElement('assistant', content, messageId);
        messagesArea.appendChild(messageDiv);
        this.scrollToBottom();
    }

    updateMessage(messageId, content) {
        const messageDiv = document.getElementById(messageId);
        if (messageDiv) {
            const textDiv = messageDiv.querySelector('.message-text');
            if (textDiv) {
                // 累积内容到缓冲区
                if (!this.messageBuffers[messageId]) {
                    this.messageBuffers[messageId] = '';
                }
                this.messageBuffers[messageId] += content;
                
                // 使用 requestAnimationFrame 节流渲染，避免高频重渲染
                if (!this.renderLocks[messageId]) {
                    this.renderLocks[messageId] = true;
                    
                    requestAnimationFrame(() => {
                        this.renderStreamingMarkdown(messageId, textDiv);
                        this.renderLocks[messageId] = false;
                        this.scrollToBottom();
                    });
                }
            }
        }
    }
    
    renderStreamingMarkdown(messageId, textDiv) {
        const content = this.messageBuffers[messageId];
        if (!content) return;
        
        if (this.md) {
            try {
                // 实时渲染 Markdown（完全按照你的方案）
                textDiv.innerHTML = this.md.render(content);
                
                // 自动滚动到底部（smooth 效果）
                const messagesArea = document.getElementById('messagesArea');
                messagesArea.scrollTo({
                    top: messagesArea.scrollHeight,
                    behavior: 'smooth'
                });
            } catch (err) {
                // 如果渲染失败，显示原始文本
                textDiv.textContent = content;
            }
        } else {
            textDiv.textContent = content;
        }
    }

    finalizeMessage(messageId) {
        const messageDiv = document.getElementById(messageId);
        if (messageDiv) {
            messageDiv.classList.add('message-complete');
            
            // 清除渲染锁
            delete this.renderLocks[messageId];
            
            // 最终完整渲染 Markdown（确保所有元素都正确）
            const textDiv = messageDiv.querySelector('.message-text');
            const content = this.messageBuffers[messageId] || textDiv.textContent;
            
            if (content && this.md) {
                try {
                    textDiv.innerHTML = this.md.render(content);
                } catch (err) {
                    console.error('Markdown 渲染失败:', err);
                    textDiv.textContent = content;
                }
            }
            
            // 清理缓冲区
            delete this.messageBuffers[messageId];
        }
    }

    createMessageElement(role, content, messageId = null) {
        const messageDiv = document.createElement('div');
        messageId = messageId || 'msg_' + Date.now();
        messageDiv.className = `message ${role}`;
        messageDiv.id = messageId;

        const icon = role === 'user' ? 'fa-user' : 'fa-robot';
        const name = role === 'user' ? '你' : 'AI助手';

        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <i class="fas ${icon}"></i>
                    <span>${name}</span>
                </div>
                <div class="message-text">${content}</div>
            </div>
        `;

        return messageDiv;
    }

    showToolCallsStart(tools) {
        const messagesArea = document.getElementById('messagesArea');
        const toolDiv = document.createElement('div');
        toolDiv.className = 'tool-call';
        toolDiv.innerHTML = `
            <div class="tool-call-content">
                <div class="tool-call-header">
                    <i class="fas fa-tools"></i>
                    <span>正在调用工具: ${tools.map(t => t.name).join(', ')}</span>
                </div>
            </div>
        `;
        messagesArea.appendChild(toolDiv);
        this.scrollToBottom();
    }

    showToolCall(toolName, toolResult) {
        const messagesArea = document.getElementById('messagesArea');
        const toolDiv = document.createElement('div');
        toolDiv.className = 'tool-call';
        toolDiv.innerHTML = `
            <div class="tool-call-content">
                <div class="tool-call-header">
                    <i class="fas fa-check-circle"></i>
                    <span>工具调用完成: ${toolName}</span>
                </div>
                <div class="tool-call-result">${toolResult}</div>
            </div>
        `;
        messagesArea.appendChild(toolDiv);
        this.scrollToBottom();
    }

    addTypingIndicator() {
        const messagesArea = document.getElementById('messagesArea');
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typingIndicator';
        typingDiv.className = 'message assistant';
        typingDiv.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        messagesArea.appendChild(typingDiv);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const typingDiv = document.getElementById('typingIndicator');
        if (typingDiv) {
            typingDiv.remove();
        }
    }

    sendMessage() {
        // 如果正在流式输出，则执行停止操作
        if (this.isStreaming) {
            this.stopStreaming();
            return;
        }

        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message || !this.isConnected) {
            return;
        }

        // 发送消息（包含模式信息）
        this.ws.send(JSON.stringify({
            type: 'message',
            content: message,
            mode: this.mode  // 发送当前选择的模式
        }));

        // 清空输入框并重置高度
        input.value = '';
        this.autoResizeInput(input);
        
        // 显示输入中指示器
        this.addTypingIndicator();
        
        // 禁用输入框
        this.enableInput(false);
    }

    enableInput(enable) {
        const input = document.getElementById('messageInput');
        input.disabled = !enable;
        
        if (enable) {
            input.focus();
        }
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

    stopStreaming() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        if (!this.currentMessageId) return;
        
        // 发送停止指令
        this.ws.send(JSON.stringify({
            type: 'stop',
            messageId: this.currentMessageId
        }));
        
        // 立即更新状态
        this.isStreaming = false;
        this.switchToSendButton();
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
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    clearChat() {
        if (confirm('确定要清空所有对话记录吗？')) {
            localStorage.removeItem('chat_session_id');
            location.reload();
        }
    }

    // === React Agent 相关方法 ===

    addReactContainer(messageId, maxSteps) {
        const messagesArea = document.getElementById('messagesArea');
        const containerDiv = document.createElement('div');
        containerDiv.className = 'message assistant react-container';
        containerDiv.id = messageId;
        containerDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <i class="fas fa-robot"></i>
                    <span>React Agent （最大步数: ${maxSteps}）</span>
                </div>
                <div class="react-steps" id="react-steps-${messageId}"></div>
                <div class="react-final-answer" id="react-final-${messageId}" style="display:none;"></div>
            </div>
        `;
        messagesArea.appendChild(containerDiv);
        this.scrollToBottom();
    }

    addReactStep(step, messageId) {
        const stepsContainer = document.getElementById(`react-steps-${messageId}`);
        if (!stepsContainer) return;

        const stepDiv = document.createElement('div');
        stepDiv.className = 'react-step';
        stepDiv.id = `react-step-${messageId}-${step}`;
        stepDiv.innerHTML = `
            <div class="react-step-header">
                <i class="fas fa-cog fa-spin"></i>
                <strong>步骤 ${step}</strong>
            </div>
            <div class="react-step-content" id="react-step-content-${messageId}-${step}"></div>
        `;
        stepsContainer.appendChild(stepDiv);
        this.scrollToBottom();
    }

    updateReactStepContent(step, content) {
        const contentDiv = document.getElementById(`react-step-content-${this.currentMessageId}-${step}`);
        if (contentDiv) {
            if (!this.reactSteps[step]) {
                this.reactSteps[step] = '';
            }
            this.reactSteps[step] += content;
            contentDiv.textContent = this.reactSteps[step];
            this.scrollToBottom();
        }
    }

    showReactThought(step, thought) {
        const stepDiv = document.getElementById(`react-step-${this.currentMessageId}-${step}`);
        if (!stepDiv) return;

        const thoughtDiv = document.createElement('div');
        thoughtDiv.className = 'react-thought';
        thoughtDiv.innerHTML = `
            <div class="react-label">
                <i class="fas fa-lightbulb"></i>
                <strong>Thought:</strong>
            </div>
            <div class="react-text">${this.escapeHtml(thought)}</div>
        `;
        stepDiv.appendChild(thoughtDiv);
        this.scrollToBottom();
    }

    showReactAction(step, action) {
        const stepDiv = document.getElementById(`react-step-${this.currentMessageId}-${step}`);
        if (!stepDiv) return;

        const actionDiv = document.createElement('div');
        actionDiv.className = 'react-action';
        actionDiv.innerHTML = `
            <div class="react-label">
                <i class="fas fa-play-circle"></i>
                <strong>Action:</strong>
            </div>
            <div class="react-text">${this.escapeHtml(action)}</div>
        `;
        stepDiv.appendChild(actionDiv);
        this.scrollToBottom();
    }

    showToolCallStart(toolName, toolInput) {
        const stepDiv = document.getElementById(`react-step-${this.currentMessageId}-${this.currentStep}`);
        if (!stepDiv) return;

        const toolDiv = document.createElement('div');
        toolDiv.className = 'react-tool-call';
        toolDiv.id = `tool-call-${this.currentMessageId}-${this.currentStep}`;
        toolDiv.innerHTML = `
            <div class="react-label">
                <i class="fas fa-tools fa-spin"></i>
                <strong>正在调用工具: ${this.escapeHtml(toolName)}</strong>
            </div>
            <div class="tool-input">输入: ${this.escapeHtml(toolInput)}</div>
        `;
        stepDiv.appendChild(toolDiv);
        this.scrollToBottom();
    }

    showToolCallEnd(toolName, toolResult) {
        const toolDiv = document.getElementById(`tool-call-${this.currentMessageId}-${this.currentStep}`);
        if (toolDiv) {
            toolDiv.className = 'react-tool-call success';
            toolDiv.innerHTML = `
                <div class="react-label">
                    <i class="fas fa-check-circle"></i>
                    <strong>工具调用成功: ${this.escapeHtml(toolName)}</strong>
                </div>
                <div class="tool-result">结果: ${this.escapeHtml(toolResult)}</div>
            `;
        }
        this.scrollToBottom();
    }

    showToolCallError(toolName, error) {
        const toolDiv = document.getElementById(`tool-call-${this.currentMessageId}-${this.currentStep}`);
        if (toolDiv) {
            toolDiv.className = 'react-tool-call error';
            toolDiv.innerHTML = `
                <div class="react-label">
                    <i class="fas fa-exclamation-circle"></i>
                    <strong>工具调用失败: ${this.escapeHtml(toolName)}</strong>
                </div>
                <div class="tool-error">错误: ${this.escapeHtml(error)}</div>
            `;
        }
        this.scrollToBottom();
    }

    showReactObservation(step, observation) {
        const stepDiv = document.getElementById(`react-step-${this.currentMessageId}-${step}`);
        if (!stepDiv) return;

        const obsDiv = document.createElement('div');
        obsDiv.className = 'react-observation';
        obsDiv.innerHTML = `
            <div class="react-label">
                <i class="fas fa-eye"></i>
                <strong>Observation:</strong>
            </div>
            <div class="react-text">${this.escapeHtml(observation)}</div>
        `;
        stepDiv.appendChild(obsDiv);
        this.scrollToBottom();
    }

    finalizeReactStep(step) {
        const stepDiv = document.getElementById(`react-step-${this.currentMessageId}-${step}`);
        if (!stepDiv) return;

        const header = stepDiv.querySelector('.react-step-header i');
        if (header) {
            header.className = 'fas fa-check-circle';
        }
        stepDiv.classList.add('completed');
        delete this.reactSteps[step];
    }

    showReactFinish(answer, totalSteps) {
        const finalDiv = document.getElementById(`react-final-${this.currentMessageId}`);
        if (!finalDiv) return;

        finalDiv.style.display = 'block';
        finalDiv.innerHTML = `
            <div class="react-finish-header">
                <i class="fas fa-flag-checkered"></i>
                <strong>最终答案 （总计 ${totalSteps} 步）</strong>
            </div>
            <div class="react-finish-content">${this.md ? this.md.render(answer) : this.escapeHtml(answer)}</div>
        `;
        this.scrollToBottom();
    }

    showReactMaxSteps(answer) {
        const finalDiv = document.getElementById(`react-final-${this.currentMessageId}`);
        if (!finalDiv) return;

        finalDiv.style.display = 'block';
        finalDiv.innerHTML = `
            <div class="react-finish-header" style="color: #f59e0b;">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>达到最大步数</strong>
            </div>
            <div class="react-finish-content">${this.escapeHtml(answer)}</div>
        `;
        this.scrollToBottom();
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

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
});
