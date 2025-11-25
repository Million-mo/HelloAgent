// WebSocket 连接管理
export class WebSocketHandler {
    constructor(chatApp) {
        this.app = chatApp;
        this.ws = null;
        this.sessionId = this.getSessionId();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.isConnected = false;
    }

    getSessionId() {
        let sessionId = localStorage.getItem('chat_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('chat_session_id', sessionId);
        }
        return sessionId;
    }

    connect() {
        const backendHost = 'localhost:8000';
        const wsUrl = `ws://${backendHost}/ws/${this.sessionId}`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            this.setupEvents();
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.app.updateStatus('连接失败', false);
            this.scheduleReconnect();
        }
    }

    setupEvents() {
        this.ws.onopen = () => {
            console.log('WebSocket连接已建立');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.app.updateStatus('已连接', true);
            this.app.enableInput(true);
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.app.handleMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket连接已关闭');
            this.isConnected = false;
            this.app.updateStatus('已断开', false);
            this.app.enableInput(false);
            this.scheduleReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
            this.app.updateStatus('连接错误', false);
        };
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            this.app.updateStatus(`重连中... (${this.reconnectAttempts})`, false);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay);
        } else {
            this.app.updateStatus('连接失败', false);
            this.app.showError('无法连接到服务器，请刷新页面重试');
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
            return true;
        }
        return false;
    }
}
