'use client'

import { useState } from 'react'
import { PURPOSE_OPTIONS } from '../../lib/constants'

interface Props {
  onAnswer: (val: string) => void
  onBack:   () => void
}

export default function GateStep4({ onAnswer, onBack }: Props) {
  const [selected, setSelected] = useState<string | null>(null)

  const handleSelect = (id: string) => {
    setSelected(id)
    setTimeout(() => onAnswer(id), 150)
  }

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 w-full max-w-md">

      {/* Header */}
      <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-1">
        Step 3 of 3
      </div>
      <p className="text-sm text-[#e6edf3] font-medium mb-1">
        What is the main purpose of this project?
      </p>
      <p className="text-xs text-[#484f58] mb-5 leading-relaxed">
        This shapes how every agent researches, evaluates, and advises on your project.
        Choose what matches your real goal.
      </p>

      {/* Options */}
      <div className="space-y-2 mb-5">
        {PURPOSE_OPTIONS.filter(opt => opt.id !== 'professional').map(opt => {
          const isSelected = selected === opt.id
          return (
            <button
              key={opt.id}
              onClick={() => handleSelect(opt.id)}
              className={`w-full text-left px-4 py-3.5 rounded-xl border transition-all ${
                isSelected
                  ? 'bg-[#f0b429]/10 border-[#f0b429]/40'
                  : 'bg-[#0d1117] border-[#30363d] hover:border-[#f0b429]/20 hover:bg-[#161b22]'
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Icon */}
                <span className="text-xl flex-shrink-0 mt-0.5">{opt.icon}</span>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-0.5">
                    <span className={`text-sm font-semibold transition-colors ${
                      isSelected ? 'text-[#f0b429]' : 'text-[#e6edf3]'
                    }`}>
                      {opt.label}
                    </span>
                    {isSelected && (
                      <span className="text-xs font-mono text-[#f0b429] flex-shrink-0">
                        ✓ Selected
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[#484f58] leading-relaxed mb-2">
                    {opt.desc}
                  </p>
                  {/* Output preview */}
                  <div className={`text-xs font-mono px-2 py-1 rounded-lg border transition-colors ${
                    isSelected
                      ? 'text-[#f0b429]/70 border-[#f0b429]/20 bg-[#f0b429]/5'
                      : 'text-[#30363d] border-[#21262d] bg-transparent'
                  }`}>
                    {opt.output_preview}
                  </div>
                </div>
              </div>
            </button>
          )
        })}
      </div>

      {/* Back */}
      <button
        onClick={onBack}
        className="w-full py-2.5 bg-[#0d1117] border border-[#30363d] rounded-lg text-xs text-[#484f58] hover:text-[#e6edf3] hover:border-[#8b949e] transition-colors font-mono"
      >
        ← Back
      </button>
    </div>
  )
}