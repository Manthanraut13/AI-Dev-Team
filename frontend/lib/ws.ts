import { API_BASE } from './api'
import { WSInboundMessage, WSOutboundMessage } from './types'

/** Typed WebSocket client with reconnect and event subscription. */
export class WsClient {
  private ws: WebSocket | null = null
  private sessionId: string
  private handlers: Map<string, Set<(data: any) => void>> = new Map()
  private reconnectDelay = 1000
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private closed = false

  constructor(sessionId: string) {
    this.sessionId = sessionId
  }

  /** Connect to the session WS endpoint. */
  connect(): void {
    this.closed = false
    const wsUrl = `${API_BASE.replace('http', 'ws')}/ws/session/${this.sessionId}`
    this.ws = new WebSocket(wsUrl)

    this.ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as WSOutboundMessage
        this.emit(data.type, data)
      } catch {}
    }

    this.ws.onclose = () => {
      if (!this.closed) {
        this.reconnectTimer = setTimeout(() => this.connect(), this.reconnectDelay)
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 10000)
      }
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }

    this.ws.onopen = () => {
      this.reconnectDelay = 1000
      this.emit('open', {})
    }
  }

  /** Send a message to the server. */
  send(msg: WSInboundMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg))
    }
  }

  /** Subscribe to a message type. Returns unsubscribe function. */
  on(type: string, cb: (data: any) => void): () => void {
    if (!this.handlers.has(type)) this.handlers.set(type, new Set())
    this.handlers.get(type)!.add(cb)
    return () => this.handlers.get(type)?.delete(cb)
  }

  /** Emit an event to all subscribers. */
  private emit(type: string, data: any): void {
    const subs = this.handlers.get(type)
    if (subs) {
      subs.forEach((cb) => cb(data))
    }
  }

  /** Close the connection permanently (no reconnect). */
  close(): void {
    this.closed = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }
}
