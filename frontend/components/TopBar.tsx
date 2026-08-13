'use client'

import { useState } from 'react'
import { useSessionStore } from '../stores/sessionStore'

export default function TopBar() {
  const session = useSessionStore((s) => s.session)
  const workspacePath = useSessionStore((s) => s.workspacePath)
  const streaming = useSessionStore((s) => s.streaming)
  const writeFilesToDisk = useSessionStore((s) => s.writeFilesToDisk)
  const files = useSessionStore((s) => s.files)
  const previewOpen = useSessionStore((s) => s.preview.open)
  const previewStatus = useSessionStore((s) => s.preview.status)
  const togglePreview = useSessionStore((s) => s.togglePreview)
  const [writtenMsg, setWrittenMsg] = useState<string | null>(null)

  const handleWrite = async () => {
    try {
      const { written, skipped } = await writeFilesToDisk()
      setWrittenMsg(`Wrote ${written.length} files${skipped.length ? `, skipped ${skipped.length}` : ''}`)
      setTimeout(() => setWrittenMsg(null), 4000)
    } catch (e) {
      setWrittenMsg((e as Error).message)
      setTimeout(() => setWrittenMsg(null), 4000)
    }
  }

  const fileCount = Object.keys(files || {}).length

  return (
    <div className="flex items-center justify-between px-6 py-2.5 border-b border-gray-800 bg-[#0a0a0a]">
      <div className="flex items-center gap-3 min-w-0">
        <h2 className="font-semibold text-white truncate">{session?.name || 'Session'}</h2>
        {workspacePath && (
          <span
            className="text-xs text-gray-500 truncate hidden md:block"
            title={workspacePath}
          >
            {workspacePath}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {writtenMsg && <span className="text-xs text-green-400">{writtenMsg}</span>}

        <button
          onClick={togglePreview}
          className={`flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs font-medium transition ${
            previewOpen
              ? 'bg-blue-700 text-white hover:bg-blue-600'
              : 'bg-gray-800 text-gray-200 hover:bg-gray-700'
          }`}
          title="Toggle preview"
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              previewStatus === 'running'
                ? 'bg-green-400'
                : previewStatus === 'error'
                ? 'bg-red-400'
                : previewStatus === 'installing' || previewStatus === 'starting'
                ? 'bg-yellow-400 animate-pulse'
                : 'bg-gray-500'
            }`}
          />
          Preview
        </button>

        {fileCount > 0 && (
          <button
            onClick={handleWrite}
            className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 transition"
          >
            Write to Disk ({fileCount})
          </button>
        )}

        <div className="flex items-center gap-1.5">
          <span
            className={`h-2 w-2 rounded-full ${
              streaming ? 'bg-blue-400 animate-pulse' : 'bg-green-500'
            }`}
          />
          <span className="text-xs text-gray-500">{streaming ? 'Working' : 'Online'}</span>
        </div>
      </div>
    </div>
  )
}
