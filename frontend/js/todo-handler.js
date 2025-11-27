// TodoList 处理（Planning Agent）
export class TodoHandler {
    constructor(chatApp) {
        this.app = chatApp;
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
                        <span class="planning-status">正在分析项目...</span>
                    </div>
                </div>
            </div>
        `;
        
        messagesArea.appendChild(planningDiv);
        this.app.scrollToBottom();
    }
    
    updatePlanningStatus(messageId, status) {
        const planningDiv = document.getElementById(`planning_${messageId}`);
        if (planningDiv) {
            const statusSpan = planningDiv.querySelector('.planning-status');
            if (statusSpan) {
                statusSpan.textContent = status;
            }
        }
    }
    
    removePlanningMessage(messageId) {
        const planningDiv = document.getElementById(`planning_${messageId}`);
        if (planningDiv) {
            planningDiv.remove();
        }
    }

    createTodoList(messageId, tasks) {
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
        this.app.scrollToBottom();
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
            
            this.updateTodoProgress();
            
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
        
        this.app.scrollToBottom();
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
