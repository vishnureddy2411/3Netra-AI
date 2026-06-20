'use client'

import { useState } from 'react'
import { PURPOSE_OPTIONS } from '../../lib/constants'
import type { GateData } from '../../lib/types'

interface Props {
  gateData: GateData
  onUpdate: (updated: GateData) => void
}

export default function GateSummary({ gateData, onUpdate }: Props) {
  const [editingField, setEditingField] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')

  const purposeLabel =
    PURPOSE_OPTIONS.find(p => p.id === gateData.purpose)?.label || gateData.purpose

  const startEdit = (field: string, current: string) => {
    setEditingField(field)
    setEditValue(current)
  }

  const submitEdit = () => {
    if (!editingField) return
    onUpdate({ ...gateData, [editingField]: editValue })
    setEditingField(null)
    setEditValue('')
  }

  const cancelEdit = () => {
    setEditingField(null)
    setEditValue('')
  }

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl px-4 py-3 max-w-2xl">
      <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-3">
        Your setup — click any value to edit
      </div>

      <div className="flex flex-wrap gap-3">

        {/* Role */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#484f58] font-mono">Role</span>
          {editingField === 'role' ? (
            <div className="flex items-center gap-1">
              <input
                value={editValue}
                onChange={e => setEditValue(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') submitEdit()
                  if (e.key === 'Escape') cancelEdit()
                }}
                autoFocus
                className="bg-[#0d1117] border border-[#f0b429]/30 rounded-lg px-2 py-1 text-xs text-[#e6edf3] outline-none w-36"
              />
              <button
                onClick={submitEdit}
                className="text-xs text-[#f0b429] hover:text-white transition-colors px-1.5 py-1 rounded bg-[#f0b429]/10 border border-[#f0b429]/20"
              >
                ✓
              </button>
              <button
                onClick={cancelEdit}
                className="text-xs text-[#484f58] hover:text-[#e6edf3] transition-colors px-1.5 py-1 rounded bg-[#0d1117] border border-[#30363d]"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              onClick={() => startEdit('role', gateData.role)}
              className="flex items-center gap-1.5 text-xs px-2.5 py-1 bg-[#0d1117] border border-[#30363d] rounded-lg text-[#8b949e] hover:text-[#e6edf3] hover:border-[#8b949e] transition-colors"
            >
              {gateData.role || 'Not set'}
              <span className="text-[#30363d]">✏</span>
            </button>
          )}
        </div>

        {/* Purpose */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#484f58] font-mono">Purpose</span>
          {editingField === 'purpose' ? (
            <div className="flex items-center gap-1">
              <select
                value={editValue}
                onChange={e => setEditValue(e.target.value)}
                autoFocus
                className="bg-[#0d1117] border border-[#f0b429]/30 rounded-lg px-2 py-1 text-xs text-[#e6edf3] outline-none"
              >
                {PURPOSE_OPTIONS.map(p => (
                  <option key={p.id} value={p.id}>{p.label}</option>
                ))}
              </select>
              <button
                onClick={submitEdit}
                className="text-xs text-[#f0b429] hover:text-white transition-colors px-1.5 py-1 rounded bg-[#f0b429]/10 border border-[#f0b429]/20"
              >
                ✓
              </button>
              <button
                onClick={cancelEdit}
                className="text-xs text-[#484f58] hover:text-[#e6edf3] transition-colors px-1.5 py-1 rounded bg-[#0d1117] border border-[#30363d]"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              onClick={() => startEdit('purpose', gateData.purpose)}
              className="flex items-center gap-1.5 text-xs px-2.5 py-1 bg-[#0d1117] border border-[#30363d] rounded-lg text-[#8b949e] hover:text-[#e6edf3] hover:border-[#8b949e] transition-colors"
            >
              {purposeLabel || 'Not set'}
              <span className="text-[#30363d]">✏</span>
            </button>
          )}
        </div>

        {/* Idea */}
        {gateData.idea && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#484f58] font-mono">Idea</span>
            {editingField === 'idea' ? (
              <div className="flex items-center gap-1">
                <input
                  value={editValue}
                  onChange={e => setEditValue(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') submitEdit()
                    if (e.key === 'Escape') cancelEdit()
                  }}
                  autoFocus
                  className="bg-[#0d1117] border border-[#f0b429]/30 rounded-lg px-2 py-1 text-xs text-[#e6edf3] outline-none w-48"
                />
                <button
                  onClick={submitEdit}
                  className="text-xs text-[#f0b429] hover:text-white transition-colors px-1.5 py-1 rounded bg-[#f0b429]/10 border border-[#f0b429]/20"
                >
                  ✓
                </button>
                <button
                  onClick={cancelEdit}
                  className="text-xs text-[#484f58] hover:text-[#e6edf3] transition-colors px-1.5 py-1 rounded bg-[#0d1117] border border-[#30363d]"
                >
                  ✕
                </button>
              </div>
            ) : (
              <button
                onClick={() => startEdit('idea', gateData.idea)}
                className="flex items-center gap-1.5 text-xs px-2.5 py-1 bg-[#0d1117] border border-[#30363d] rounded-lg text-[#8b949e] hover:text-[#e6edf3] hover:border-[#8b949e] transition-colors max-w-xs"
              >
                <span className="truncate">
                  {gateData.idea.slice(0, 40)}{gateData.idea.length > 40 ? '...' : ''}
                </span>
                <span className="text-[#30363d] flex-shrink-0">✏</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}