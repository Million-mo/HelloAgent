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
        // this.mode = 'function_call'; // 默认使用 Function Call Agent 模式
        // this.mode = 'react'; // 默认使用 Function Call Agent 模式
        this.mode = 'agent'; // 默认使用 Function Call Agent 模式
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
                // 不立即创建消息气泡，等到收到第一个chunk时再创建
                // 这样可以避免显示空白气泡
                this.isStreaming = true;
                this.switchToStopButton();
                break;
            case 'assistant_chunk':
                // 收到第一个chunk时才创建消息气泡
                const existingMsg = document.getElementById(data.messageId);
                if (!existingMsg) {
                    this.addAssistantMessage('', data.messageId);
                }
                this.updateMessage(data.messageId, data.content);
                break;
            case 'tool_calls_start':
                this.showToolCallsStart(data.tools);
                break;
            case 'tool_progress':
                this.updateToolProgress(data.toolName, data.status, data.data);
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
            // Planning Agent TodoList
            case 'planning_start':
                // 不显示typing indicator，而是显示一个规划中的消息气泡
                this.showPlanningMessage(data.messageId);
                break;
            case 'todo_list':
                this.createTodoList(data.messageId, data.tasks);
                break;
            case 'todo_update':
                this.updateTodoItem(data.task_id, data.status, data.result, data.error);
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
        } else {
            // 如果消息气泡不存在（说明没有内容），也要清理缓冲区
            delete this.messageBuffers[messageId];
            delete this.renderLocks[messageId];
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
        // 创建独立的工具调用容器（不使用message气泡包装）
        const toolDiv = document.createElement('div');
        toolDiv.className = 'tool-call';
        const timestamp = Date.now();
        toolDiv.id = `tool-call-container-${timestamp}`;
        
        // 为每个工具创建独立的折叠容器
        const toolsHtml = tools.map((tool, idx) => {
            const toolId = `tool-${timestamp}-${idx}`;
            const argsDisplay = tool.arguments ? this.formatToolArguments(tool.arguments) : '{}';
            return `
                <div class="tool-call-item" id="${toolId}" data-tool-name="${this.escapeHtml(tool.name)}" data-tool-index="${idx}">
                    <div class="tool-call-header" onclick="window.chatApp.toggleToolCall('${toolId}')">
                        <div class="tool-call-title">
                            <i class="fas fa-tools fa-spin"></i>
                            <span class="tool-name">${this.escapeHtml(tool.name)}</span>
                            <span class="tool-status">调用中...</span>
                        </div>
                        <i class="fas fa-chevron-right toggle-icon"></i>
                    </div>
                    <div class="tool-call-body" style="display: none;">
                        <div class="tool-call-section">
                            <div class="tool-section-label">
                                <i class="fas fa-cog"></i>
                                <strong>参数</strong>
                            </div>
                            <pre class="tool-arguments">${argsDisplay}</pre>
                        </div>
                        <div class="tool-call-section tool-result-section" style="display: none;">
                            <div class="tool-section-label">
                                <i class="fas fa-check-circle"></i>
                                <strong>结果</strong>
                            </div>
                            <pre class="tool-result-content"></pre>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        toolDiv.innerHTML = `<div class="tool-call-content">${toolsHtml}</div>`;
        toolDiv.setAttribute('data-pending-count', tools.length);
        messagesArea.appendChild(toolDiv);
        this.scrollToBottom();
    }

    showToolCall(toolName, toolResult) {
        // 查找对应的工具调用项（找到第一个未完成的）
        const messagesArea = document.getElementById('messagesArea');
        const toolItems = messagesArea.querySelectorAll('.tool-call-item');
        let targetTool = null;
        
        // 优先查找未完成的工具调用（没有success类的）
        for (let item of toolItems) {
            const nameEl = item.querySelector('.tool-name');
            const hasSuccess = item.classList.contains('success');
            if (nameEl && nameEl.textContent === toolName && !hasSuccess) {
                targetTool = item;
                break;
            }
        }
        
        if (targetTool) {
            // 移除进度显示（如果有）
            const progressSection = targetTool.querySelector('.tool-progress-section');
            if (progressSection) {
                progressSection.remove();
            }
            
            // 更新现有工具的状态和结果
            const statusEl = targetTool.querySelector('.tool-status');
            const iconEl = targetTool.querySelector('.tool-call-title i');
            const resultSection = targetTool.querySelector('.tool-result-section');
            const resultContent = targetTool.querySelector('.tool-result-content');
            
            if (statusEl) statusEl.textContent = '完成';
            if (iconEl) {
                iconEl.className = 'fas fa-check-circle';
            }
            if (resultSection) resultSection.style.display = 'block';
            if (resultContent) resultContent.textContent = this.formatToolResult(toolResult);
            
            targetTool.classList.add('success');
        } else {
            // 如果找不到对应的工具项，创建新的独立工具调用
            const toolDiv = document.createElement('div');
            toolDiv.className = 'tool-call';
            const toolId = `tool-${Date.now()}`;
            toolDiv.innerHTML = `
                <div class="tool-call-content">
                    <div class="tool-call-item success" id="${toolId}">
                        <div class="tool-call-header" onclick="window.chatApp.toggleToolCall('${toolId}')">
                            <div class="tool-call-title">
                                <i class="fas fa-check-circle"></i>
                                <span class="tool-name">${this.escapeHtml(toolName)}</span>
                                <span class="tool-status">完成</span>
                            </div>
                            <i class="fas fa-chevron-right toggle-icon"></i>
                        </div>
                        <div class="tool-call-body" style="display: none;">
                            <div class="tool-call-section">
                                <div class="tool-section-label">
                                    <i class="fas fa-check-circle"></i>
                                    <strong>结果</strong>
                                </div>
                                <pre class="tool-result-content">${this.formatToolResult(toolResult)}</pre>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            messagesArea.appendChild(toolDiv);
        }
        this.scrollToBottom();
    }
    
    updateToolProgress(toolName, status, data) {
        // 查找对应的工具调用项
        const messagesArea = document.getElementById('messagesArea');
        const toolItems = messagesArea.querySelectorAll('.tool-call-item');
        let targetTool = null;
        
        for (let item of toolItems) {
            const nameEl = item.querySelector('.tool-name');
            const hasSuccess = item.classList.contains('success');
            if (nameEl && nameEl.textContent === toolName && !hasSuccess) {
                targetTool = item;
                break;
            }
        }
        
        if (!targetTool) return;
        
        const statusEl = targetTool.querySelector('.tool-status');
        const iconEl = targetTool.querySelector('.tool-call-title i');
        
        if (status === 'executing') {
            // 工具开始执行
            if (statusEl) {
                if (toolName === 'write_file') {
                    // 显示文件名
                    const fileName = data && data.file_path ? this.getFileName(data.file_path) : '';
                    statusEl.textContent = fileName ? `正在写入: ${fileName}` : '正在写入文件...';
                    
                    // 在工具调用体中添加文件信息
                    const toolBody = targetTool.querySelector('.tool-call-body');
                    if (toolBody && data && data.file_path) {
                        let fileInfoSection = targetTool.querySelector('.tool-file-info-section');
                        if (!fileInfoSection) {
                            fileInfoSection = document.createElement('div');
                            fileInfoSection.className = 'tool-call-section tool-file-info-section';
                            fileInfoSection.innerHTML = `
                                <div class="tool-section-label">
                                    <i class="fas fa-file"></i>
                                    <strong>文件信息</strong>
                                </div>
                                <div class="file-info-content">
                                    <div class="file-info-item">
                                        <span class="file-info-label">文件路径:</span>
                                        <span class="file-info-value">${this.escapeHtml(data.file_path)}</span>
                                    </div>
                                </div>
                            `;
                            toolBody.insertBefore(fileInfoSection, toolBody.firstChild);
                            fileInfoSection.style.display = 'block';
                            
                            // 展开工具调用详情
                            toolBody.style.display = 'block';
                            const toggleIcon = targetTool.querySelector('.toggle-icon');
                            if (toggleIcon) {
                                toggleIcon.className = 'fas fa-chevron-down toggle-icon';
                            }
                        }
                    }
                } else if (toolName === 'read_file') {
                    statusEl.textContent = '正在读取文件...';
                } else if (toolName === 'execute_command') {
                    statusEl.textContent = '正在执行命令...';
                } else {
                    statusEl.textContent = '执行中...';
                }
            }
        } else if (status === 'writing' && data) {
            // 文件写入进度
            let progressSection = targetTool.querySelector('.tool-progress-section');
            
            if (!progressSection) {
                // 创建进度显示区域
                const toolBody = targetTool.querySelector('.tool-call-body');
                progressSection = document.createElement('div');
                progressSection.className = 'tool-call-section tool-progress-section';
                const fileName = data.file_path ? this.getFileName(data.file_path) : '文件';
                progressSection.innerHTML = `
                    <div class="tool-section-label">
                        <i class="fas fa-spinner fa-spin"></i>
                        <strong>正在写入: ${this.escapeHtml(fileName)}</strong>
                    </div>
                    <div class="tool-progress-content">
                        <div class="progress-info">
                            <span class="progress-label">写入进度:</span>
                            <span class="progress-percentage">0%</span>
                        </div>
                        <div class="progress-bar-container">
                            <div class="progress-bar" style="width: 0%"></div>
                        </div>
                        <div class="progress-details">
                            <span class="progress-text">0 B / 0 B</span>
                        </div>
                    </div>
                `;
                toolBody.insertBefore(progressSection, toolBody.firstChild);
                progressSection.style.display = 'block';
                
                // 展开工具调用详情
                toolBody.style.display = 'block';
                const toggleIcon = targetTool.querySelector('.toggle-icon');
                if (toggleIcon) {
                    toggleIcon.className = 'fas fa-chevron-down toggle-icon';
                }
            }
            
            // 更新进度条
            if (data.progress !== undefined) {
                const progressBar = progressSection.querySelector('.progress-bar');
                const progressPercentage = progressSection.querySelector('.progress-percentage');
                const progressText = progressSection.querySelector('.progress-text');
                
                if (progressBar) {
                    progressBar.style.width = `${data.progress}%`;
                }
                if (progressPercentage) {
                    progressPercentage.textContent = `${data.progress}%`;
                }
                if (progressText) {
                    const written = this.formatSize(data.written || 0);
                    const total = this.formatSize(data.total_size || 0);
                    progressText.textContent = `${written} / ${total}`;
                }
            }
            
            if (statusEl) {
                const fileName = data.file_path ? this.getFileName(data.file_path) : '文件';
                statusEl.textContent = `写入中: ${fileName} (${data.progress || 0}%)`;
            }
        } else if (status === 'completed') {
            // 工具执行完成
            if (statusEl) {
                if (toolName === 'write_file') {
                    statusEl.textContent = '✓ 写入完成';
                } else {
                    statusEl.textContent = '完成';
                }
            }
            if (iconEl) iconEl.className = 'fas fa-check-circle';
            
            // 移除进度区域的动画图标
            const progressSection = targetTool.querySelector('.tool-progress-section');
            if (progressSection) {
                const spinIcon = progressSection.querySelector('.fa-spinner');
                if (spinIcon) {
                    spinIcon.className = 'fas fa-check-circle';
                }
            }
        } else if (status === 'error') {
            // 工具执行错误
            if (statusEl) statusEl.textContent = '✗ 失败';
            if (iconEl) iconEl.className = 'fas fa-exclamation-circle';
            targetTool.classList.add('error');
        }
        
        this.scrollToBottom();
    }
    
    getFileName(filePath) {
        // 从文件路径中提取文件名
        if (!filePath) return '';
        const parts = filePath.replace(/\\/g, '/').split('/');
        return parts[parts.length - 1];
    }
    
    formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
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

        // 获取当前选择的Agent
        const agentSelect = document.getElementById('agentSelect');
        const selectedAgent = agentSelect ? agentSelect.value : null;

        // 发送消息（包含模式和Agent信息）
        this.ws.send(JSON.stringify({
            type: 'message',
            content: message,
            mode: this.mode,  // 发送当前选择的模式
            agent_name: selectedAgent  // 发送选择的Agent名称
        }));

        // 清空输入框并重置高度
        input.value = '';
        this.autoResizeInput(input);
        
        // 只有非PlanningAgent才显示通用的typing indicator
        // PlanningAgent有专门的planning气泡
        if (selectedAgent !== '任务规划师') {
            this.addTypingIndicator();
        }
        
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
        // 只在用户已经在底部附近时才自动滚动（避免打断用户向上查看历史消息）
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

    // === 工具调用辅助方法 ===
    
    toggleToolCall(toolId) {
        const toolItem = document.getElementById(toolId);
        if (!toolItem) return;
        
        const body = toolItem.querySelector('.tool-call-body');
        const toggleIcon = toolItem.querySelector('.toggle-icon');
        
        if (body && toggleIcon) {
            const isVisible = body.style.display !== 'none';
            body.style.display = isVisible ? 'none' : 'block';
            toggleIcon.className = isVisible ? 'fas fa-chevron-right toggle-icon' : 'fas fa-chevron-down toggle-icon';
        }
    }
    
    formatToolArguments(args) {
        if (typeof args === 'string') {
            try {
                const parsed = JSON.parse(args);
                return JSON.stringify(parsed, null, 2);
            } catch (e) {
                return args;
            }
        } else if (typeof args === 'object') {
            return JSON.stringify(args, null, 2);
        }
        return String(args);
    }
    
    formatToolResult(result) {
        if (typeof result === 'string') {
            try {
                const parsed = JSON.parse(result);
                return JSON.stringify(parsed, null, 2);
            } catch (e) {
                return result;
            }
        } else if (typeof result === 'object') {
            return JSON.stringify(result, null, 2);
        }
        return String(result);
    }
    
    formatArgsForTooltip(args) {
        if (!args) return '无参数';
        
        if (typeof args === 'string') {
            try {
                const parsed = JSON.parse(args);
                // 转换为紧凑的单行格式，但保持可读性
                const compact = JSON.stringify(parsed);
                // 如果太长，截断并添加省略号
                if (compact.length > 150) {
                    return compact.substring(0, 150) + '...';
                }
                return compact;
            } catch (e) {
                // 如果不是JSON，直接返回字符串
                if (args.length > 150) {
                    return args.substring(0, 150) + '...';
                }
                return args;
            }
        } else if (typeof args === 'object') {
            const compact = JSON.stringify(args);
            if (compact.length > 150) {
                return compact.substring(0, 150) + '...';
            }
            return compact;
        }
        return String(args);
    }
    
    // TodoList 相关方法
    createTodoList(messageId, tasks) {
        // 先移除planning消息气泡
        const planningMsg = document.getElementById(`planning_${messageId}`);
        if (planningMsg) {
            planningMsg.remove();
        }
        
        const messagesArea = document.getElementById('messagesArea');
        const todoContainer = document.createElement('div');
        todoContainer.className = 'message assistant';
        todoContainer.id = `todo_${messageId}`;
        
        let html = `
            <div class="message-content">
                <div class="message-header">
                    <i class="fas fa-tasks"></i>
                    <span class="role-name">AI助手 - 任务规划</span>
                </div>
                <div class="message-text">
                    <div class="todo-list">
                        <div class="todo-header">
                            <h4>📋 任务清单</h4>
                            <span class="todo-progress">0/${tasks.length} 已完成</span>
                        </div>
        `;
        
        tasks.forEach(task => {
            const priorityClass = task.priority || 'medium';
            const dependsText = task.dependencies && task.dependencies.length > 0 
                ? `<span class="task-depends">依赖: ${task.dependencies.join(', ')}</span>` 
                : '';
            const agentText = task.assigned_agent 
                ? `<span class="task-agent">🤖 ${task.assigned_agent}</span>` 
                : '';
            
            html += `
                <div class="todo-item" data-task-id="${task.id}" data-status="pending">
                    <div class="todo-checkbox">
                        <i class="far fa-circle"></i>
                    </div>
                    <div class="todo-content">
                        <div class="todo-title priority-${priorityClass}">
                            <span class="task-title">${task.title}</span>
                            ${agentText}
                        </div>
                        <div class="todo-description">${task.description}</div>
                        ${dependsText}
                    </div>
                </div>
            `;
        });
        
        html += `
                    </div>
                </div>
            </div>
        `;
        
        todoContainer.innerHTML = html;
        messagesArea.appendChild(todoContainer);
        this.scrollToBottom();
    }
    
    showPlanningMessage(messageId) {
        const messagesArea = document.getElementById('messagesArea');
        const planningDiv = document.createElement('div');
        planningDiv.className = 'message assistant';
        planningDiv.id = `planning_${messageId}`;
        
        planningDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <i class="fas fa-brain"></i>
                    <span class="role-name">AI助手 - 任务规划</span>
                </div>
                <div class="message-text">
                    <div class="planning-indicator">
                        <i class="fas fa-spinner fa-spin"></i>
                        <span>正在分析任务并生成计划...</span>
                    </div>
                </div>
            </div>
        `;
        
        messagesArea.appendChild(planningDiv);
        this.scrollToBottom();
    }
    
    updateTodoItem(taskId, status, result, error) {
        const todoItem = document.querySelector(`[data-task-id="${taskId}"]`);
        if (!todoItem) return;
        
        const checkbox = todoItem.querySelector('.todo-checkbox i');
        const title = todoItem.querySelector('.task-title');
        
        todoItem.dataset.status = status;
        
        if (status === 'in_progress') {
            checkbox.className = 'fas fa-spinner fa-spin';
            todoItem.classList.add('todo-in-progress');
        } else if (status === 'completed') {
            checkbox.className = 'fas fa-check-circle';
            todoItem.classList.remove('todo-in-progress');
            todoItem.classList.add('todo-completed');
            title.style.textDecoration = 'line-through';
            
            // 更新进度
            this.updateTodoProgress();
            
            // 如果有结果，可以显示（可选）
            if (result) {
                const content = todoItem.querySelector('.todo-content');
                const resultDiv = document.createElement('div');
                resultDiv.className = 'task-result';
                resultDiv.textContent = result.length > 100 ? result.substring(0, 100) + '...' : result;
                content.appendChild(resultDiv);
            }
        } else if (status === 'failed') {
            checkbox.className = 'fas fa-times-circle';
            todoItem.classList.remove('todo-in-progress');
            todoItem.classList.add('todo-failed');
            
            if (error) {
                const content = todoItem.querySelector('.todo-content');
                const errorDiv = document.createElement('div');
                errorDiv.className = 'task-error';
                errorDiv.textContent = '❗ ' + error;
                content.appendChild(errorDiv);
            }
        }
        
        this.scrollToBottom();
    }
    
    updateTodoProgress() {
        const todoLists = document.querySelectorAll('.todo-list');
        todoLists.forEach(list => {
            const items = list.querySelectorAll('.todo-item');
            const completed = list.querySelectorAll('.todo-item[data-status="completed"]').length;
            const total = items.length;
            
            const progressSpan = list.querySelector('.todo-progress');
            if (progressSpan) {
                progressSpan.textContent = `${completed}/${total} 已完成`;
            }
        });
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
