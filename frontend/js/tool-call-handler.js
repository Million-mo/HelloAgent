// 工具调用相关处理
export class ToolCallHandler {
    constructor(chatApp) {
        this.app = chatApp;
    }

    showToolCallsStart(tools) {
        const messagesArea = document.getElementById('messagesArea');
        
        const toolDiv = document.createElement('div');
        toolDiv.className = 'tool-call';
        const timestamp = Date.now();
        toolDiv.id = `tool-call-container-${timestamp}`;
        
        const toolsHtml = tools.map((tool, idx) => {
            const toolName = typeof tool === 'string' ? tool : (tool.name || 'unknown');
            const toolArgs = typeof tool === 'object' && tool.arguments ? tool.arguments : '{}';
            const toolId = `tool-${timestamp}-${idx}`;
            const argsDisplay = this.formatToolArguments(toolArgs);
            return `
                <div class="tool-call-item" id="${toolId}" data-tool-name="${this.escapeHtml(toolName)}" data-tool-index="${idx}">
                    <div class="tool-call-header" onclick="window.chatApp.toggleToolCall('${toolId}')">
                        <div class="tool-call-title">
                            <i class="fas fa-tools fa-spin"></i>
                            <span class="tool-name">${this.escapeHtml(toolName)}</span>
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
        this.app.scrollToBottom();
    }

    showToolCall(toolName, toolResult) {
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
        
        if (targetTool) {
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
        this.app.scrollToBottom();
    }

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

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
