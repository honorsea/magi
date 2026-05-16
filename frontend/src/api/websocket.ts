type MessageHandler = (event: any) => void;

export class SimWebSocket {
  private ws: WebSocket | null = null;
  private simId: string;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectTimer: any = null;

  constructor(simId: string) {
    this.simId = simId;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    this.ws = new WebSocket(`${protocol}//${host}/ws/simulation/${this.simId}`);

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handlers.forEach(h => h(data));
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    this.ws.onclose = () => {
      // Auto-reconnect if not intentionally closed
      this.reconnectTimer = setTimeout(() => this.connect(), 2000);
    };

    this.ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.onclose = null; // Prevent reconnect
      this.ws.close();
      this.ws = null;
    }
  }

  onMessage(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }
}
