'use client'

import { useEffect, useRef, useState } from 'react'
import { useSessionStore } from '../stores/sessionStore'
import { ChatMessage } from '../lib/types'
import PlanCard from './PlanCard'

export default function ChatPanel() {
  const messages = useSessionStore((s) => s.messages)
  const requirements = useSessionStore((s) => s.requirements)
  const architecture = useSessionStore((s) => s.architecture)
  const streaming = useSessionStore((s) => s.streaming)
  const sendChat = useSessionStore((s) => s.sendChat)
  const stopGeneration = useSessionStore((s) => s.stopGeneration)

  const [input, setInput] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const tokenBufferRef = useRef<Record<string, string>>({})
  const [, forceRender] = useState(0)

  // Subscribe to WS chat.token/done events for streaming text.
  const ws = useSessionStore((s) => s.ws)
  useEffect(() => {
    if (!ws) return
    const unsubToken = ws.on('chat.token', (data: { message_id: string; delta: string }) => {
      tokenBufferRef.current[data.message_id] = (tokenBufferRef.current[data.message_id] || '') + data.delta
      forceRender((n) => n + 1)
    })
    const unsubDone = ws.on('chat.done', (data: { message_id: string }) => {
      delete tokenBufferRef.current[data.message_id]
    })
    return () => {
      unsubToken()
      unsubDone()
    }
  }, [ws])

  // Auto-scroll to bottom on new content.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  const handleSend = () => {
    const text = input.trim()
    if (!text) return
    sendChat(text)
    setInput('')
  }

  // Merge streaming tokens into the message list for display.
  const streamingParts = Object.entries(tokenBufferRef.current)

  const showPlanCard = requirements.length > 0 && !streaming

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((m, i) => (
          <MessageBubble key={i} msg={m} />
        ))}

        {/* Streaming placeholder for the in-flight assistant turn */}
        {streaming && streamingParts.length === 0 && (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <span className="h-3 w-3 rounded-full bg-blue-400 animate-pulse" />
            Thinking...
          </div>
        )}

        {streamingParts.map(([id, text]) => (
          <div key={id} className="flex justify-start">
            <div className="max-w-[80%] rounded-xl rounded-tl-sm bg-[#1a1a1a] border border-gray-800 px-4 py-3 text-sm text-gray-200 whitespace-pre-wrap">
              {text}
              <span className="inline-block h-4 w-0.5 bg-blue-400 animate-pulse ml-0.5" />
            </div>
          </div>
        ))}

        {showPlanCard && <PlanCard requirements={requirements} architecture={architecture} />}

        <div ref={endRef} />
      </div>

      <div className="border-t border-gray-800 p-4">
        <div className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder={streaming ? 'Agent is working...' : 'Describe your project or give feedback...'}
            disabled={streaming}
            className="flex-1 rounded-lg border border-gray-700 bg-[#111111] px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none disabled:opacity-50"
          />
          {streaming ? (
            <button
              onClick={stopGeneration}
              className="rounded-lg bg-red-600 px-4 py-3 text-sm font-medium text-white hover:bg-red-700 transition"
            >
              Stop
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40 transition"
            >
              Send
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.type === 'HumanMessage'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${
          isUser
            ? 'bg-blue-600 text-white rounded-tr-sm'
            : 'bg-[#1a1a1a] border border-gray-800 text-gray-200 rounded-tl-sm'
        }`}
      >
        {msg.content === '__streaming__' ? '' : msg.content}
      </div>
    </div>
  )
}
