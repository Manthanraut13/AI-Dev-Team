'use client'

import { useState } from 'react'
import { useSessionStore } from '../stores/sessionStore'

type Mode = 'create' | 'existing'

export default function WorkspacePicker() {
  const [mode, setMode] = useState<Mode>('create')
  const [name, setName] = useState('')
  const [path, setPath] = useState('')
  const [loading, setLoading] = useState(false)
  const createSession = useSessionStore((s) => s.createSession)
  const error = useSessionStore((s) => s.error)

  const handleSubmit = async () => {
    setLoading(true)
    try {
      await createSession(
        name || path.split(/[\\/]/).pop() || 'Untitled',
        mode === 'create' ? { mode: 'create', name } : { mode: 'existing', path }
      )
    } finally {
      setLoading(false)
    }
  }

  const canSubmit = mode === 'create' ? name.trim().length > 0 : path.trim().length > 0

  return (
    <div className="flex h-screen items-center justify-center bg-[#000000] text-gray-200">
      <div className="w-full max-w-xl space-y-4 p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">
            <span className="text-blue-500">AI</span> Dev Team
          </h1>
          <p className="text-gray-500 text-sm mt-2">
            Pick a folder, then chat with agents to build your app
          </p>
        </div>

        <div className="flex gap-2 bg-[#111111] p-1 rounded-lg border border-gray-700">
          <button
            onClick={() => setMode('create')}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition ${
              mode === 'create' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            Create new
          </button>
          <button
            onClick={() => setMode('existing')}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition ${
              mode === 'existing' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            Existing folder
          </button>
        </div>

        {mode === 'create' ? (
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Project name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && canSubmit && handleSubmit()}
              placeholder="e.g. todo-app"
              className="w-full rounded-lg border border-gray-700 bg-[#111111] px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            />
            <p className="text-xs text-gray-600 mt-1">
              Will be created at <code className="text-gray-500">~/ai-dev-team-projects/{name || '…'}</code>
            </p>
          </div>
        ) : (
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Folder path</label>
            <input
              value={path}
              onChange={(e) => setPath(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && canSubmit && handleSubmit()}
              placeholder="e.g. C:\Projects\my-app or /home/user/projects/app"
              className="w-full rounded-lg border border-gray-700 bg-[#111111] px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            />
            <p className="text-xs text-gray-600 mt-1">Existing directory — code will be written here</p>
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={!canSubmit || loading}
          className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40 transition"
        >
          {loading ? 'Starting...' : mode === 'create' ? 'Create & Start' : 'Open & Start'}
        </button>

        {error && <p className="text-xs text-center text-red-400">{error}</p>}
      </div>
    </div>
  )
}
