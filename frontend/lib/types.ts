/** Shared TypeScript types for the Codex-style AI Dev Team frontend. */

/** Workspace specification for session creation. */
export interface WorkspaceSpec {
  mode: 'existing' | 'create'
  path?: string
  name?: string
}

/** Create session request. */
export interface SessionCreate {
  name?: string
  workspace?: WorkspaceSpec
}

/** Session summary (list view). */
export interface SessionSummary {
  id: string
  name: string
  workspace_path?: string
  has_files: boolean
  created_at: number
}

/** Full session response. */
export interface Session {
  id: string
  name: string
  workspace_path?: string
  idea: string
  messages: ChatMessage[]
  requirements: string[]
  architecture: Record<string, any>
  files: Record<string, string>
  test_results: Record<string, any>
  review_feedback: string[]
  documentation: Record<string, string>
  created_at: number
}

/** Chat message in session messages array. */
export interface ChatMessage {
  type: 'HumanMessage' | 'AIMessage'
  content: string
}

/** Agent activity event. */
export interface AgentEvent {
  node: string
  label: string
  status: 'running' | 'complete' | 'error'
  message?: string
  files_count?: number
  timestamp: number
}

/** Workspace file node. */
export interface WorkspaceNode {
  path: string
  type: 'file' | 'dir'
  size?: number
}

/** Preview panel runtime status. */
export interface PreviewStatus {
  status: 'stopped' | 'installing' | 'starting' | 'running' | 'error'
  backend_url: string
  frontend_url: string
  message: string
}

/** Preview log entry (one stdout/stderr line). */
export interface PreviewLog {
  service: 'backend' | 'frontend'
  line: string
}

/** Aggregated preview state for the store. */
export interface PreviewState {
  status: PreviewStatus['status']
  backendUrl: string
  frontendUrl: string
  message: string
  logs: PreviewLog[]
  open: boolean
}

/** WebSocket message types. */
export type WSInboundMessage =
  | { type: 'chat'; message: string; client_message_id?: string }
  | { type: 'chat.stop' }
  | { type: 'workspace.read'; path: string }

export type WSOutboundMessage =
  | { type: 'chat.ack'; message_id: string; session_id: string }
  | { type: 'chat.token'; session_id: string; message_id: string; delta: string }
  | { type: 'chat.done'; session_id: string; message_id: string; content: string }
  | { type: 'chat.message'; session_id: string; role: string; content: string; ts: number }
  | { type: 'agent_update'; session_id: string; node: string; label: string; status: string; message?: string; files_count?: number; timestamp: number }
  | { type: 'workspace.updated'; written: string[]; skipped: string[]; timestamp: number }
  | { type: 'file.content'; path: string; content: string }
  | { type: 'error'; session_id: string; message: string }
  | { type: 'session.snapshot'; session_id: string; session: Session }
  | { type: 'chat.stopped'; session_id: string }
  | { type: 'preview.status'; status: string; backend_url: string; frontend_url: string; message: string }
  | { type: 'preview.log'; service: 'backend' | 'frontend'; line: string }
  | { type: 'preview.ready'; frontend_url: string; backend_url: string }
  | { type: 'preview.auto'; session_id: string; workspace_path: string }
