'use client'

import { useState } from 'react'
import { useSessionStore } from '../stores/sessionStore'

interface Props {
  requirements: string[]
  architecture: Record<string, any>
}

export default function PlanCard({ requirements, architecture }: Props) {
  const sendChat = useSessionStore((s) => s.sendChat)
  const streaming = useSessionStore((s) => s.streaming)
  const [feedback, setFeedback] = useState('')

  const endpoints = (architecture?.api_endpoints || []).slice(0, 6) as Array<Record<string, any>>
  const tables = (architecture?.db_schema || []).slice(0, 6) as Array<Record<string, any>>
  const tech = (architecture?.tech_decisions || []).slice(0, 4) as string[]

  const approve = () => {
    const fb = feedback.trim()
    sendChat(fb ? `Approved the plan. ${fb}` : 'Approved the plan, please proceed with the build.')
  }

  const reject = () => {
    const fb = feedback.trim()
    sendChat(fb ? `Rejected the plan. ${fb}` : 'Rejected the plan. Please revise it.')
  }

  return (
    <div className="rounded-xl border border-gray-700 bg-[#0d1117] overflow-hidden">
      <div className="px-4 py-2 bg-[#161b22] border-b border-gray-700 flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
          📋 Proposed Plan
        </span>
        <span className="text-xs text-gray-500">{requirements.length} requirements</span>
      </div>

      <div className="p-4 space-y-4">
        {requirements.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Requirements</h4>
            <ul className="space-y-1">
              {requirements.map((r, i) => (
                <li key={i} className="text-sm text-gray-300 flex gap-2">
                  <span className="text-blue-500">•</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {tech.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Tech Stack</h4>
            <div className="flex flex-wrap gap-1.5">
              {tech.map((t, i) => (
                <span key={i} className="px-2 py-0.5 rounded bg-gray-800 text-xs text-gray-300">
                  {t}
                </span>
              ))}
            </div>
          </div>
        )}

        {endpoints.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">API Endpoints</h4>
            <div className="space-y-1">
              {endpoints.map((e, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span
                    className={`px-1.5 py-0.5 rounded font-mono ${
                      (e.method || 'GET').toUpperCase() === 'POST'
                        ? 'bg-green-900/50 text-green-400'
                        : (e.method || 'GET').toUpperCase() === 'DELETE'
                        ? 'bg-red-900/50 text-red-400'
                        : 'bg-blue-900/50 text-blue-400'
                    }`}
                  >
                    {e.method || 'GET'}
                  </span>
                  <code className="text-gray-400">{e.path || '/'}</code>
                </div>
              ))}
            </div>
          </div>
        )}

        {tables.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Database</h4>
            <div className="flex flex-wrap gap-1.5">
              {tables.map((t, i) => (
                <span key={i} className="px-2 py-0.5 rounded bg-purple-900/40 text-xs text-purple-300">
                  {t.table}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="pt-2 border-t border-gray-700">
          <div className="flex items-center gap-2">
            <input
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Optional feedback... (e.g. use Postgres instead of SQLite)"
              disabled={streaming}
              className="flex-1 rounded border border-gray-700 bg-[#111111] px-3 py-2 text-xs text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div className="flex gap-2 mt-2">
            <button
              onClick={approve}
              disabled={streaming}
              className="flex-1 rounded bg-green-600 px-3 py-2 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-40"
            >
              ✓ Approve Plan
            </button>
            <button
              onClick={reject}
              disabled={streaming}
              className="flex-1 rounded bg-red-600 px-3 py-2 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-40"
            >
              ✗ Reject Plan
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
