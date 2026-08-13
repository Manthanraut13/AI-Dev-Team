'use client'

import { useState } from 'react'
import { useSessionStore } from '../stores/sessionStore'
import WorkspacePicker from '../components/WorkspacePicker'
import TopBar from '../components/TopBar'
import AgentActivity from '../components/AgentActivity'
import ChatPanel from '../components/ChatPanel'
import FilePanel from '../components/FilePanel'
import PreviewPanel from '../components/PreviewPanel'

const PREVIEW_BAR_HEIGHT = 40 // collapsed bar height in pixels

export default function Home() {
  const phase = useSessionStore((s) => s.phase)
  const events = useSessionStore((s) => s.events)
  const activeAgent = useSessionStore((s) => s.activeAgent)
  const error = useSessionStore((s) => s.error)
  const previewOpen = useSessionStore((s) => s.preview.open)
  const previewStatus = useSessionStore((s) => s.preview.status)
  const togglePreview = useSessionStore((s) => s.togglePreview)

  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  if (phase === 'pick') {
    return <WorkspacePicker />
  }

  // Compute preview pane height (collapsed vs expanded).
  const previewHeight = previewOpen ? '45%' : `${PREVIEW_BAR_HEIGHT}px`

  return (
    <div className="flex h-screen bg-[#000000] text-gray-200">
      <aside className="w-64 flex-shrink-0 border-r border-gray-800 bg-[#0a0a0a] flex flex-col">
        <AgentActivity events={events} activeAgent={activeAgent} />
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden min-w-0">
        <TopBar />
        <div className="flex-1 overflow-hidden min-h-0">
          <ChatPanel />
        </div>

        {/* Preview pane — collapses to a thin toggle bar when closed. */}
        <div
          className="flex-shrink-0 border-t border-gray-800 bg-[#0a0a0a]"
          style={{ height: previewHeight }}
        >
          {previewOpen ? (
            <PreviewPanel />
          ) : (
            <button
              onClick={togglePreview}
              className="h-full w-full flex items-center justify-between px-4 text-xs text-gray-400 hover:bg-[#111] transition"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`h-2 w-2 rounded-full ${
                    previewStatus === 'running'
                      ? 'bg-green-500'
                      : previewStatus === 'error'
                      ? 'bg-red-500'
                      : 'bg-gray-600'
                  }`}
                />
                <span>Preview</span>
                {previewStatus !== 'stopped' && (
                  <span className="text-gray-600">({previewStatus})</span>
                )}
              </div>
              <span className="text-gray-600">Click to open ▴</span>
            </button>
          )}
        </div>
      </main>

      <aside className="w-72 lg:w-96 flex-shrink-0">
        <FilePanel selectedPath={selectedFile} onSelect={setSelectedFile} />
      </aside>

      {error && (
        <div className="fixed bottom-4 right-4 max-w-sm rounded-lg bg-red-900/90 border border-red-700 px-4 py-3 text-sm text-red-100 shadow-xl">
          {error}
        </div>
      )}
    </div>
  )
}
