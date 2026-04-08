// src/services/websocketService.js
import { API_BASE_URL } from '../config/env';

class WebSocketService {
    constructor() {
        this.ws = null;
        this.callbacks = {
            onEnergyUpdate: null,
            onError: null,
            onConnectionChange: null
        };
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 2000;
        this.isConnected = false;
        this.heartbeatInterval = null;
    }

    connect() {
        const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws/realtime';
        
        try {
            console.log('Connecting to WebSocket:', wsUrl);
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.startHeartbeat();
                
                if (this.callbacks.onConnectionChange) {
                    this.callbacks.onConnectionChange(true);
                }
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'energy_update' && this.callbacks.onEnergyUpdate) {
                        this.callbacks.onEnergyUpdate(data.data);
                    }
                    
                    this.resetHeartbeat();
                    
                } catch (error) {
                    console.error('WebSocket parse error:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.isConnected = false;
                if (this.callbacks.onError) {
                    this.callbacks.onError(error);
                }
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.stopHeartbeat();
                
                if (this.callbacks.onConnectionChange) {
                    this.callbacks.onConnectionChange(false);
                }
                
                this.reconnect();
            };

        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.reconnect();
        }
    }

    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN) {
                try {
                    this.ws.send(JSON.stringify({ type: 'ping' }));
                } catch (e) {
                    console.warn('Heartbeat failed:', e);
                }
            }
        }, 30000);
    }

    resetHeartbeat() {
        this.stopHeartbeat();
        this.startHeartbeat();
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    reconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(30000, this.reconnectDelay * this.reconnectAttempts);
            
            console.log('Reconnecting (attempt ' + this.reconnectAttempts + '/' + this.maxReconnectAttempts + ') in ' + (delay/1000) + 's...');
            
            setTimeout(() => this.connect(), delay);
        } else {
            console.log('Max reconnection attempts reached');
        }
    }

    onEnergyUpdate(callback) {
        this.callbacks.onEnergyUpdate = callback;
    }

    onError(callback) {
        this.callbacks.onError = callback;
    }

    onConnectionChange(callback) {
        this.callbacks.onConnectionChange = callback;
    }

    disconnect() {
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    isConnected() {
        return this.isConnected;
    }
}

const websocketService = new WebSocketService();
export default websocketService;
