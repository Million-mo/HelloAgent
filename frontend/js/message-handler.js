// 消息处理和渲染
export class MessageHandler {
    constructor(chatApp) {
        this.app = chatApp;
        this.messageBuffers = {};
        this.renderLocks = {};
    }

    addUserMessage(content) {
        const messagesArea = document.getElementById('messagesArea');
        const messageDiv = this.createMessageElement('user', content);
        messagesArea.appendChild(messageDiv);
        this.app.scrollToBottom();
    }

    addAssistantMessage(content, messageId) {
        const messagesArea = document.getElementById('messagesArea');
        const messageDiv = this.createMessageElement('assistant', content, messageId);
        messagesArea.appendChild(messageDiv);
        this.app.scrollToBottom();
    }

    createMessageElement(role, content, messageId = null) {
        const messageDiv = document.createElement('div');
        messageId = messageId || 'msg_' + Date.now();
        messageDiv.className = `message ${role}`;
        messageDiv.id = messageId;

        const icon = role === 'user' ? 'fa-user' : 'fa-robot';
        const name = role === 'user' ? 'User' : 'AI助手';

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

    updateMessage(messageId, content) {
        const messageDiv = document.getElementById(messageId);
        if (messageDiv) {
            const textDiv = messageDiv.querySelector('.message-text');
            if (textDiv) {
                if (!this.messageBuffers[messageId]) {
                    this.messageBuffers[messageId] = '';
                }
                this.messageBuffers[messageId] += content;
                
                if (!this.renderLocks[messageId]) {
                    this.renderLocks[messageId] = true;
                    
                    requestAnimationFrame(() => {
                        this.renderStreamingMarkdown(messageId, textDiv);
                        this.renderLocks[messageId] = false;
                        this.app.scrollToBottom();
                    });
                }
            }
        }
    }
    
    renderStreamingMarkdown(messageId, textDiv) {
        const content = this.messageBuffers[messageId];
        if (!content) return;
        
        if (this.app.md) {
            try {
                textDiv.innerHTML = this.app.md.render(content);
            } catch (err) {
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
            
            delete this.renderLocks[messageId];
            
            const textDiv = messageDiv.querySelector('.message-text');
            const content = this.messageBuffers[messageId] || textDiv.textContent;
            
            if (content && this.app.md) {
                try {
                    textDiv.innerHTML = this.app.md.render(content);
                } catch (err) {
                    console.error('Markdown 渲染失败:', err);
                    textDiv.textContent = content;
                }
            }
            
            delete this.messageBuffers[messageId];
        } else {
            delete this.messageBuffers[messageId];
            delete this.renderLocks[messageId];
        }
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
        this.app.scrollToBottom();
    }

    removeTypingIndicator() {
        const typingDiv = document.getElementById('typingIndicator');
        if (typingDiv) {
            typingDiv.remove();
        }
    }
}
