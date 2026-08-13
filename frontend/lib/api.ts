import { PreviewStatus, Session, SessionCreate, SessionSummary, WorkspaceNode } from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => null)
    const msg = detail?.detail || `Request failed (${res.status})`
    throw new Error(msg)
  }
  return res.json()
}

/** Create a session, optionally resolving a workspace. */
export async function createSession(body: SessionCreate): Promise<Session> {
  return request<Session>('/api/sessions', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/** Load a session by ID. */
export async function loadSession(sessionId: string): Promise<Session> {
  return request<Session>(`/api/sessions/${sessionId}`)
}

/** List all sessions. */
export async function listSessions(): Promise<SessionSummary[]> {
  return request<SessionSummary[]>('/api/sessions')
}

/** Set the workspace path for a session. */
export async function setWorkspace(sessionId: string, path: string): Promise<Session> {
  return request<Session>(`/api/sessions/${sessionId}/workspace`, {
    method: 'POST',
    body: JSON.stringify({ path }),
  })
}

/** Write generated files to disk. Returns written/skipped lists. */
export async function writeFiles(sessionId: string, overwrite = false): Promise<{ written: string[]; skipped: string[] }> {
  return request<{ written: string[]; skipped: string[] }>(`/api/sessions/${sessionId}/write`, {
    method: 'POST',
    body: JSON.stringify({ overwrite }),
  })
}

/** Get workspace file tree. */
export async function getTree(sessionId: string): Promise<{ workspace_path: string; tree: WorkspaceNode[] }> {
  return request<{ workspace_path: string; tree: WorkspaceNode[] }>(`/api/sessions/${sessionId}/workspace/tree`)
}

/** Read a file from the workspace. */
export async function readFile(sessionId: string, path: string): Promise<{ path: string; content: string }> {
  return request<{ path: string; content: string }>(
    `/api/sessions/${sessionId}/workspace/file?path=${encodeURIComponent(path)}`
  )
}

/** Start a chat turn via REST (fallback; real streaming uses WS). */
export async function sendChat(sessionId: string, message: string): Promise<{ message_id: string }> {
  return request<{ message_id: string }>(`/api/sessions/${sessionId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

/** Start the generated app (install deps + run backend/frontend). */
export async function runProject(sessionId: string): Promise<PreviewStatus> {
  return request<PreviewStatus>(`/api/sessions/${sessionId}/run`, {
    method: 'POST',
  })
}

/** Stop the running app (kills uvicorn + next dev process trees). */
export async function stopProject(sessionId: string): Promise<PreviewStatus> {
  return request<PreviewStatus>(`/api/sessions/${sessionId}/stop`, {
    method: 'POST',
  })
}

/** Read the current preview status. */
export async function getRunStatus(sessionId: string): Promise<PreviewStatus> {
  return request<PreviewStatus>(`/api/sessions/${sessionId}/run/status`)
}

export { API_BASE }
