'use client'

import { useEffect, useState } from 'react'
import { useSessionStore } from '../stores/sessionStore'
import { WorkspaceNode } from '../lib/types'

interface Props {
  selectedPath: string | null
  onSelect: (path: string | null) => void
}

export default function FilePanel({ selectedPath, onSelect }: Props) {
  const tree = useSessionStore((s) => s.workspaceTree)
  const workspacePath = useSessionStore((s) => s.workspacePath)
  const workspaceLoading = useSessionStore((s) => s.workspaceLoading)
  const openFile = useSessionStore((s) => s.openFile)

  const [fileContent, setFileContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!selectedPath) {
      setFileContent(null)
      return
    }
    setLoading(true)
    openFile(selectedPath).then((content) => {
      setFileContent(content)
      setLoading(false)
    })
  }, [selectedPath, openFile])

  const files = tree?.filter((n) => n.type === 'file') || []

  return (
    <div className="flex h-full flex-col border-l border-gray-800 bg-[#0a0a0a]">
      <div className="px-4 py-2 border-b border-gray-800">
        <h3 className="text-xs font-semibold text-gray-500 uppercase">Files</h3>
        <p className="text-[10px] text-gray-600 truncate mt-0.5" title={workspacePath || ''}>
          {workspacePath || 'No workspace'}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {workspaceLoading && <p className="text-xs text-gray-600 px-2 py-2">Loading tree...</p>}

        {!workspaceLoading && files.length === 0 && (
          <p className="text-xs text-gray-600 px-2 py-4 text-center">
            No files yet.<br />Run a build to generate code.
          </p>
        )}

        {files.map((node) => (
          <TreeNode
            key={node.path}
            node={node}
            selected={selectedPath === node.path}
            onSelect={onSelect}
          />
        ))}
      </div>

      {selectedPath && (
        <div className="h-1/2 border-t border-gray-800 flex flex-col">
          <div className="px-4 py-1.5 border-b border-gray-800 flex items-center justify-between">
            <span className="text-xs text-gray-400 truncate">{selectedPath}</span>
            <button
              onClick={() => onSelect(null)}
              className="text-xs text-gray-500 hover:text-white"
            >
              ✕
            </button>
          </div>
          <div className="flex-1 overflow-auto p-3">
            {loading ? (
              <p className="text-xs text-gray-600">Loading...</p>
            ) : (
              <pre className="whitespace-pre-wrap text-xs text-gray-300 leading-relaxed">
                {fileContent}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function TreeNode({
  node,
  selected,
  onSelect,
}: {
  node: WorkspaceNode
  selected: boolean
  onSelect: (path: string) => void
}) {
  return (
    <button
      onClick={() => node.type === 'file' && onSelect(node.path)}
      className={`flex items-center gap-2 w-full text-left px-2 py-1 rounded text-xs ${
        selected ? 'bg-blue-900/40 text-blue-300' : 'text-gray-400 hover:bg-gray-800'
      }`}
    >
      <span>{node.type === 'dir' ? '📁' : '📄'}</span>
      <span className="truncate flex-1">{node.path.split('/').pop()}</span>
      {node.size != null && node.type === 'file' && (
        <span className="text-[10px] text-gray-600">{formatSize(node.size)}</span>
      )}
    </button>
  )
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}
