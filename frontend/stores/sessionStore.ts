'use client'

import { create } from 'zustand'
import {
  createSession as apiCreateSession,
  getRunStatus,
  getTree,
  loadSession,
  readFile,
  runProject,
  stopProject,
  writeFiles,
} from '../lib/api'
import { WsClient } from '../lib/ws'
import {
  AgentEvent,
  ChatMessage,
  PreviewLog,
  PreviewState,
  Session,
  WorkspaceNode,
  WorkspaceSpec,
} from '../lib/types'

/** Application phase — workspace picker → chatting. */
export type Phase = 'pick' | 'chat'

const MAX_LOGS = 500

const initialPreview: PreviewState = {
  status: 'stopped',
  backendUrl: '',
  frontendUrl: '',
  message: '',
  logs: [],
  open: false,
}

interface SessionState {
  phase: Phase
  session: Session | null
  messages: ChatMessage[]
  events: AgentEvent[]
  activeAgent: string | null
  requirements: string[]
  architecture: Record<string, any>
  files: Record<string, string>
  workspacePath: string | null
  workspaceTree: WorkspaceNode[] | null
  workspaceLoading: boolean
  streaming: boolean
  error: string | null
  ws: WsClient | null

  // Preview (auto-run) state
  preview: PreviewState

  // Actions
  createSession: (name: string, workspace: WorkspaceSpec) => Promise<void>
  sendChat: (message: string) => void
  stopGeneration: () => void
  setWorkspace: (path: string) => Promise<void>
  refreshTree: () => Promise<void>
  openFile: (path: string) => Promise<string | null>
  writeFilesToDisk: (overwrite?: boolean) => Promise<{ written: string[]; skipped: string[] }>
  applyWsEvent: (msg: any) => void

  // Preview actions
  runProject: () => Promise<void>
  stopProject: () => Promise<void>
  openPreview: () => void
  closePreview: () => void
  togglePreview: () => void

  reset: () => void
}

export const useSessionStore = create<SessionState>((set, get) => ({
  phase: 'pick',
  session: null,
  messages: [],
  events: [],
  activeAgent: null,
  requirements: [],
  architecture: {},
  files: {},
  workspacePath: null,
  workspaceTree: null,
  workspaceLoading: false,
  streaming: false,
  error: null,
  ws: null,
  preview: initialPreview,

  createSession: async (name, workspace) => {
    set({ error: null, messages: [], events: [], preview: initialPreview })
    try {
      const session = await apiCreateSession({
        name: name || 'Untitled',
        workspace,
      })
      const ws = new WsClient(session.id)

      // Subscribe to WS events before connecting so we don't miss the snapshot.
      ws.on('session.snapshot', (data) => {
        const s = data.session as Session
        set({
          session: s,
          messages: s.messages || [],
          requirements: s.requirements || [],
          architecture: s.architecture || {},
          files: s.files || {},
          workspacePath: s.workspace_path || null,
        })
      })
      ws.on('chat.ack', () => {
        // Assistant bubble created here — we render streaming bubble in ChatPanel.
        set({ streaming: true })
      })
      ws.on('chat.token', () => {
        // Tokens accumulate in a ref in ChatPanel; nothing to do in store.
      })
      ws.on('chat.done', (data) => {
        const done = data as { session_id: string; message_id: string; content: string }
        set((st) => {
          // Replace the streaming placeholder with the final assistant message.
          const messages = st.messages.filter(
            (m) => !(m.type === 'AIMessage' && m.content === '__streaming__')
          )
          return {
            messages: [...messages, { type: 'AIMessage' as const, content: done.content }],
            streaming: false,
          }
        })
        get().refreshTree()
      })
      ws.on('chat.message', (data) => {
        const cm = data as { role: string; content: string; ts: number }
        set((st) => ({
          messages: [
            ...st.messages,
            {
              type: cm.role === 'user' ? 'HumanMessage' as const : 'AIMessage' as const,
              content: cm.content,
            },
          ],
        }))
      })
      ws.on('agent_update', (data) => {
        const evt = data as AgentEvent
        set((st) => ({
          events: [...st.events, evt],
          activeAgent: evt.status === 'running' ? evt.label : null,
        }))
      })
      ws.on('workspace.updated', () => {
        get().refreshTree()
      })
      ws.on('file.content', (data) => {
        // File content handled by FilePanel directly.
        void data
      })
      ws.on('error', (data) => {
        set({ error: (data as { message: string }).message })
      })

      // ---- Preview WS events ----
      ws.on('preview.status', (data) => {
        const p = data as { status: PreviewState['status']; backend_url: string; frontend_url: string; message: string }
        set((st) => ({
          preview: {
            ...st.preview,
            status: p.status,
            backendUrl: p.backend_url || st.preview.backendUrl,
            frontendUrl: p.frontend_url || st.preview.frontendUrl,
            message: p.message || '',
          },
        }))
      })
      ws.on('preview.log', (data) => {
        const entry = data as PreviewLog
        set((st) => {
          const logs = [...st.preview.logs, entry]
          // Cap the in-memory log ring.
          if (logs.length > MAX_LOGS) logs.splice(0, logs.length - MAX_LOGS)
          return { preview: { ...st.preview, logs } }
        })
      })
      ws.on('preview.ready', (data) => {
        const p = data as { frontend_url: string; backend_url: string }
        set((st) => ({
          preview: {
            ...st.preview,
            status: 'running',
            frontendUrl: p.frontend_url,
            backendUrl: p.backend_url,
            open: true,
          },
        }))
      })
      ws.on('preview.auto', () => {
        // Backend just wrote files. Auto-run the preview, then open the panel.
        get().runProject()
        set((st) => ({ preview: { ...st.preview, open: true } }))
      })

      ws.connect()
      set({ ws, session, workspacePath: session.workspace_path || null, phase: 'chat' })
      get().refreshTree()
    } catch (e) {
      set({ error: (e as Error).message })
    }
  },

  sendChat: (message) => {
    const { ws, session } = get()
    if (!ws || !session) return
    // Add user message locally.
    set((st) => ({
      messages: [...st.messages, { type: 'HumanMessage' as const, content: message }],
      streaming: true,
    }))
    // Send over WS.
    ws.send({ type: 'chat', message })
  },

  stopGeneration: () => {
    const { ws } = get()
    ws?.send({ type: 'chat.stop' })
    set({ streaming: false })
  },

  setWorkspace: async (path) => {
    const { session } = get()
    if (!session) return
    try {
      const updated = await setWorkspaceApi(session.id, path)
      set({ session: updated, workspacePath: updated.workspace_path || null })
      get().refreshTree()
    } catch (e) {
      set({ error: (e as Error).message })
    }
  },

  refreshTree: async () => {
    const { session } = get()
    if (!session?.workspace_path) {
      set({ workspaceTree: null })
      return
    }
    set({ workspaceLoading: true })
    try {
      const { tree } = await getTree(session.id)
      set({ workspaceTree: tree })
    } catch {
      set({ workspaceTree: null })
    } finally {
      set({ workspaceLoading: false })
    }
  },

  openFile: async (path) => {
    const { session } = get()
    if (!session?.workspace_path) return null
    try {
      const res = await readFile(session.id, path)
      return res.content
    } catch {
      return null
    }
  },

  writeFilesToDisk: async (overwrite = false) => {
    const { session } = get()
    if (!session) return { written: [], skipped: [] }
    const result = await writeFiles(session.id, overwrite)
    get().refreshTree()
    return result
  },

  applyWsEvent: (msg) => {
    get().applyWsEvent(msg)
  },

  // ---- Preview actions ----

  runProject: async () => {
    const { session } = get()
    if (!session) return
    set((st) => ({ preview: { ...st.preview, status: 'installing', message: 'Starting…', open: true } }))
    try {
      await runProject(session.id)
    } catch (e) {
      set((st) => ({
        preview: { ...st.preview, status: 'error', message: (e as Error).message },
        error: (e as Error).message,
      }))
    }
  },

  stopProject: async () => {
    const { session } = get()
    if (!session) return
    try {
      await stopProject(session.id)
    } catch (e) {
      set({ error: (e as Error).message })
    }
  },

  openPreview: () => {
    set((st) => ({ preview: { ...st.preview, open: true } }))
    // Pull the latest status from the server in case we re-opened after WS disconnect.
    const { session } = get()
    if (session) {
      getRunStatus(session.id)
        .then((s) =>
          set((st) => ({
            preview: {
              ...st.preview,
              status: s.status,
              backendUrl: s.backend_url || st.preview.backendUrl,
              frontendUrl: s.frontend_url || st.preview.frontendUrl,
              message: s.message || '',
            },
          }))
        )
        .catch(() => {/* ignore */})
    }
  },

  closePreview: () => {
    set((st) => ({ preview: { ...st.preview, open: false } }))
  },

  togglePreview: () => {
    const open = get().preview.open
    if (open) get().closePreview()
    else get().openPreview()
  },

  reset: () => {
    const { ws } = get()
    ws?.close()
    set({
      phase: 'pick',
      session: null,
      messages: [],
      events: [],
      activeAgent: null,
      requirements: [],
      architecture: {},
      files: {},
      workspacePath: null,
      workspaceTree: null,
      streaming: false,
      error: null,
      ws: null,
      preview: initialPreview,
    })
  },
}))

// Local import to avoid circular dependency at module scope.
import { setWorkspace as setWorkspaceApi } from '../lib/api'
