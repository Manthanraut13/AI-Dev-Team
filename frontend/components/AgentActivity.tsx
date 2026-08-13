'use client'

import { AgentEvent } from '../lib/types'

const AGENT_ICONS: Record<string, string> = {
  product_manager: '📋',
  architect: '🏗️',
  research: '🔍',
  backend_dev: '⚙️',
  frontend_dev: '🎨',
  qa_engineer: '🧪',
  code_reviewer: '🔎',
  error_handler: '🛠️',
  documentation: '📄',
  github: '🚀',
}

const AGENT_COLORS: Record<string, string> = {
  product_manager: 'text-blue-400',
  architect: 'text-purple-400',
  research: 'text-cyan-400',
  backend_dev: 'text-green-400',
  frontend_dev: 'text-pink-400',
  qa_engineer: 'text-yellow-400',
  code_reviewer: 'text-orange-400',
  error_handler: 'text-red-400',
  documentation: 'text-teal-400',
  github: 'text-gray-300',
}

interface Props {
  events: AgentEvent[]
  activeAgent: string | null
}

export default function AgentActivity({ events, activeAgent }: Props) {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-gray-800 p-4">
        <h1 className="text-lg font-bold text-white flex items-center gap-2">
          <span className="text-blue-500">AI</span> Dev Team
        </h1>
        <p className="text-xs text-gray-500 mt-1">Multi-Agent Chat</p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        {events.length === 0 && (
          <p className="text-xs text-gray-600 px-2 py-4 text-center">
            Agent activity will appear here
          </p>
        )}
        {events.map((evt, i) => (
          <div
            key={i}
            className={`flex items-center gap-2 px-2 py-1.5 rounded text-xs ${
              evt.status === 'running'
                ? 'bg-blue-900/30 text-blue-300'
                : evt.status === 'error'
                ? 'bg-red-900/30 text-red-300'
                : 'text-gray-400'
            }`}
          >
            <span>{AGENT_ICONS[evt.node] || '🔧'}</span>
            <span className={`flex-1 ${AGENT_COLORS[evt.node] || ''}`}>{evt.label}</span>
            {evt.status === 'running' && (
              <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" />
            )}
            {evt.status === 'complete' && <span className="text-green-500">✓</span>}
            {evt.files_count ? (
              <span className="text-gray-600">{evt.files_count}f</span>
            ) : null}
          </div>
        ))}
      </div>

      {activeAgent && (
        <div className="p-3 border-t border-gray-800">
          <div className="flex items-center gap-2 text-xs text-blue-400">
            <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" />
            {activeAgent} working...
          </div>
        </div>
      )}
    </div>
  )
}
