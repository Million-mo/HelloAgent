// React Agent 相关处理
export class ReactAgentHandler {
    constructor(chatApp) {
        this.app = chatApp;
        this.currentStep = 0;
        this.reactSteps = {};
    }

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
        this.app.scrollToBottom();
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
        this.app.scrollToBottom();
    }

    updateReactStepContent(step, content, currentMessageId) {
        const contentDiv = document.getElementById(`react-step-content-${currentMessageId}-${step}`);
        if (contentDiv) {
            if (!this.reactSteps[step]) {
                this.reactSteps[step] = '';
            }
            this.reactSteps[step] += content;
            contentDiv.textContent = this.reactSteps[step];
            this.app.scrollToBottom();
        }
    }

    showReactThought(step, thought, currentMessageId) {
        const stepDiv = document.getElementById(`react-step-${currentMessageId}-${step}`);
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
        this.app.scrollToBottom();
    }

    showReactAction(step, action, currentMessageId) {
        const stepDiv = document.getElementById(`react-step-${currentMessageId}-${step}`);
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
        this.app.scrollToBottom();
    }

    showToolCallStart(toolName, toolInput, currentMessageId, currentStep) {
        const stepDiv = document.getElementById(`react-step-${currentMessageId}-${currentStep}`);
        if (!stepDiv) return;

        const toolDiv = document.createElement('div');
        toolDiv.className = 'react-tool-call';
        toolDiv.id = `tool-call-${currentMessageId}-${currentStep}`;
        toolDiv.innerHTML = `
            <div class="react-label">
                <i class="fas fa-tools fa-spin"></i>
                <strong>正在调用工具: ${this.escapeHtml(toolName)}</strong>
            </div>
            <div class="tool-input">输入: ${this.escapeHtml(toolInput)}</div>
        `;
        stepDiv.appendChild(toolDiv);
        this.app.scrollToBottom();
    }

    showToolCallEnd(toolName, toolResult, currentMessageId, currentStep) {
        const toolDiv = document.getElementById(`tool-call-${currentMessageId}-${currentStep}`);
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
        this.app.scrollToBottom();
    }

    showToolCallError(toolName, error, currentMessageId, currentStep) {
        const toolDiv = document.getElementById(`tool-call-${currentMessageId}-${currentStep}`);
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
        this.app.scrollToBottom();
    }

    showReactObservation(step, observation, currentMessageId) {
        const stepDiv = document.getElementById(`react-step-${currentMessageId}-${step}`);
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
        this.app.scrollToBottom();
    }

    finalizeReactStep(step, currentMessageId) {
        const stepDiv = document.getElementById(`react-step-${currentMessageId}-${step}`);
        if (!stepDiv) return;

        const header = stepDiv.querySelector('.react-step-header i');
        if (header) {
            header.className = 'fas fa-check-circle';
        }
        stepDiv.classList.add('completed');
        delete this.reactSteps[step];
    }

    showReactFinish(answer, totalSteps, currentMessageId) {
        const finalDiv = document.getElementById(`react-final-${currentMessageId}`);
        if (!finalDiv) return;

        finalDiv.style.display = 'block';
        finalDiv.innerHTML = `
            <div class="react-finish-header">
                <i class="fas fa-flag-checkered"></i>
                <strong>最终答案 （总计 ${totalSteps} 步）</strong>
            </div>
            <div class="react-finish-content">${this.app.md ? this.app.md.render(answer) : this.escapeHtml(answer)}</div>
        `;
        this.app.scrollToBottom();
    }

    showReactMaxSteps(answer, currentMessageId) {
        const finalDiv = document.getElementById(`react-final-${currentMessageId}`);
        if (!finalDiv) return;

        finalDiv.style.display = 'block';
        finalDiv.innerHTML = `
            <div class="react-finish-header" style="color: #f59e0b;">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>达到最大步数</strong>
            </div>
            <div class="react-finish-content">${this.escapeHtml(answer)}</div>
        `;
        this.app.scrollToBottom();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
