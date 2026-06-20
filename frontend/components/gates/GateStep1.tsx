'use client'

import { useEffect, useState } from 'react'
import { getLastSession } from '../../lib/api'

interface Props {
  onAnswer: (val: string) => void
}

export default function GateStep1({ onAnswer }: Props) {
  const [lastProject, setLastProject] = useState<{
    found: boolean
    resume_message?: string
  } | null>(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    getLastSession()
      .then(d => setLastProject(d))
      .catch(() => setLastProject({ found: false }))
      .finally(() => setChecking(false))
  }, [])

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 w-full max-w-sm">
      <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-1">
        Getting started
      </div>
      <p className="text-xs text-[#484f58] mb-4">
        Helps agents track your progress across sessions
      </p>
      <p className="text-sm text-[#e6edf3] mb-4">
        Is this a new project or are you continuing an existing one?
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => onAnswer('new')}
          className="flex-1 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-lg text-sm text-[#e6edf3] hover:border-[#f0b429]/40 hover:bg-[#161b22] transition-colors font-medium"
        >
          New Project
        </button>
        <button
          onClick={() => { if (lastProject?.found) onAnswer('existing') }}
          disabled={checking || !lastProject?.found}
          className={`flex-1 py-2.5 rounded-lg text-sm transition-colors border ${
            lastProject?.found
              ? 'bg-[#0d1117] border-[#30363d] text-[#8b949e] hover:text-[#e6edf3] hover:border-[#8b949e]'
              : 'bg-[#0d1117] border-[#21262d] text-[#30363d] cursor-not-allowed'
          }`}
        >
          {checking
            ? 'Checking...'
            : lastProject?.found
            ? `Continue: ${lastProject.resume_message?.slice(0, 18)}...`
            : 'No previous project'}
        </button>
      </div>
    </div>
  )
}