'use client'

import { useState } from 'react'

interface Props {
  onAnswer:  (val: string) => void
  onBack:    () => void
  userType?: 'student' | 'professional'
}

export default function GateStep3({ onAnswer, onBack, userType = 'student' }: Props) {
  const [val, setVal] = useState('')
  const isProfessional = userType === 'professional'

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 w-full max-w-sm">
      <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-1">
        {isProfessional ? 'Step 2 of 2' : 'Step 2 of 3'}
      </div>
      <p className="text-xs text-[#484f58] mb-4 leading-relaxed">
        {isProfessional
          ? 'Describe your work task clearly — agents will analyze, architect, and help you execute it.'
          : 'Skip if you want agents to research and suggest the best projects for your role and purpose.'}
      </p>
      <p className="text-sm text-[#e6edf3] mb-3">
        {isProfessional
          ? 'What is your work task or business problem?'
          : 'Do you have a project idea in mind?'}
      </p>
      <textarea
        value={val}
        onChange={e => setVal(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' && !e.shiftKey && val.trim()) {
            e.preventDefault()
            onAnswer(val)
          }
        }}
        placeholder={isProfessional
          ? 'e.g. We need a real-time notification system for our e-commerce platform...'
          : 'Describe your project idea... (or skip and we will suggest)'}
        rows={3}
        autoFocus
        className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2.5 text-sm text-[#e6edf3] placeholder-[#484f58] outline-none focus:border-[#f0b429]/30 transition-colors resize-none mb-3"
      />
      <div className="flex gap-2">
        <button
          onClick={onBack}
          className="px-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-lg text-sm text-[#484f58] hover:text-[#e6edf3] hover:border-[#8b949e] transition-colors"
        >
          ← Back
        </button>
        <button
          onClick={() => onAnswer(val)}
          disabled={isProfessional && !val.trim()}
          className="flex-1 py-2.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg text-sm disabled:opacity-30 hover:bg-[#e0a419] transition-colors"
        >
          {isProfessional ? 'Analyze →' : 'Next →'}
        </button>
        {!isProfessional && (
          <button
            onClick={() => onAnswer('')}
            className="px-4 py-2.5 bg-[#0d1117] border border-[#30363d] rounded-lg text-sm text-[#484f58] hover:text-[#e6edf3] transition-colors"
          >
            Suggest
          </button>
        )}
      </div>
    </div>
  )
}