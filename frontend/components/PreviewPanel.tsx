'use client'

import { useEffect, useRef, useState } from 'react'
import { useSessionStore } from '../stores/sessionStore'

const STATUS_DOT: Record<string, string> = {
  stopped: 'bg-gray-500',
  installing: 'bg-yellow-400 animate-pulse',
  starting: 'bg-blue-400 animate-pulse',
  running: 'bg-green-500',
  error: 'bg-red-500',
}

const STATUS_LABEL: Record<string, string> = {
  stopped: 'Stopped',
  installing: 'Installing…',
  starting: 'Starting…',
  running: 'Running',
  error: 'Error',
}

export default function PreviewPanel() {
  const preview = useSessionStore((s) => s.preview)
  const runProject = useSessionStore((s) => s.runProject)
  const stopProject = useSessionStore((s) => s.stopProject)
  const closePreview = useSessionStore((s) => s.closePreview)

  const [showLogs, setShowLogs] = useState(false)
  const [iframeKey, setIframeKey] = useState(0)
  const logsEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll logs to the bottom when new entries arrive.
  useEffect(() => {
    if (showLogs) {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [preview.logs.length, showLogs])

  // Force iframe reload when the frontend URL changes (restart scenario).
  useEffect(() => {
    if (preview.frontendUrl) {
      setIframeKey((k) => k + 1)
    }
  }, [preview.frontendUrl])

  const isRunning =
    preview.status === 'running' || preview.status === 'starting' || preview.status === 'installing'

  return (
    <div className="flex h-full flex-col border-t border-gray-800 bg-[#0a0a0a]">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-gray-800 px-3 py-1.5">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`h-2 w-2 rounded-full ${STATUS_DOT[preview.status] || STATUS_DOT.stopped}`} />
          <span className="text-xs font-medium text-gray-300">
            {STATUS_LABEL[preview.status] || preview.status}
          </span>
          {preview.message && (
            <span className="text-[10px] text-gray-500 truncate max-w-xs" title={preview.message}>
              {preview.message}
            </span>
          )}
          {preview.frontendUrl && preview.status === 'running' && (
            <span className="text-[10px] text-gray-500 truncate hidden md:inline">
              {preview.frontendUrl}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          {!isRunning ? (
            <button
              onClick={() => runProject()}
              className="rounded bg-green-700 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-green-600 transition"
            >
              ▶ Run
            </button>
          ) : (
            <button
              onClick={() => stopProject()}
              className="rounded bg-red-700 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-red-600 transition"
            >
              ■ Stop
            </button>
          )}
          {preview.frontendUrl && (
            <button
              onClick={() => runProject()}
              className="rounded bg-gray-800 px-2.5 py-1 text-[11px] font-medium text-gray-200 hover:bg-gray-700 transition"
              title="Restart"
            >
              ↻
            </button>
          )}
          {preview.frontendUrl && (
            <a
              href={preview.frontendUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded bg-gray-800 px-2.5 py-1 text-[11px] font-medium text-gray-200 hover:bg-gray-700 transition"
              title="Open in new tab"
            >
              ↗
            </a>
          )}
          <button
            onClick={() => setShowLogs((v) => !v)}
            className={`rounded px-2.5 py-1 text-[11px] font-medium transition ${
              showLogs ? 'bg-blue-700 text-white' : 'bg-gray-800 text-gray-200 hover:bg-gray-700'
            }`}
          >
            Logs ({preview.logs.length})
          </button>
          <button
            onClick={closePreview}
            className="rounded bg-gray-800 px-2 py-1 text-[11px] font-medium text-gray-200 hover:bg-gray-700 transition"
            title="Close preview"
          >
            ×
          </button>
        </div>
      </div>

      {/* Body — iframe or logs */}
      <div className="flex-1 min-h-0 flex flex-col">
        {showLogs ? (
          <div className="flex-1 overflow-y-auto bg-black p-2 font-mono text-[11px] leading-snug">
            {preview.logs.length === 0 ? (
              <p className="text-gray-600 text-center py-4">No logs yet.</p>
            ) : (
              preview.logs.map((entry, i) => (
                <div key={i} className="flex gap-2">
                  <span
                    className={`flex-shrink-0 ${
                      entry.service === 'frontend' ? 'text-pink-400' : 'text-green-400'
                    }`}
                  >
                    [{entry.service}]
                  </span>
                  <span className="text-gray-300 break-all whitespace-pre-wrap">{entry.line}</span>
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        ) : (
          <div className="flex-1 min-h-0 bg-[#0f0f0f]">
            {preview.frontendUrl && preview.status === 'running' ? (
              <iframe
                key={iframeKey}
                src={preview.frontendUrl}
                className="h-full w-full border-0"
                title="App Preview"
                sandbox="allow-scripts allow-forms allow-same-origin allow-popups"
              />
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-6">
                {preview.status === 'installing' || preview.status === 'starting' ? (
                  <>
                    <div className="h-8 w-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin mb-3" />
                    <p className="text-sm text-gray-400">{preview.message || 'Preparing app…'}</p>
                    <p className="text-xs text-gray-600 mt-1">Streaming logs available</p>
                  </>
                ) : preview.status === 'error' ? (
                  <>
                    <p className="text-sm text-red-400 mb-2">Failed to start</p>
                    <p className="text-xs text-gray-500 max-w-md">{preview.message}</p>
                    <p className="text-xs text-gray-600 mt-2">Open logs for details.</p>
                  </>
                ) : (
                  <>
                    <p className="text-sm text-gray-400 mb-1">No app running</p>
                    <p className="text-xs text-gray-600">
                      Write files to disk, then the app auto-runs here.
                    </p>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
