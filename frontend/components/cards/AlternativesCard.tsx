'use client'

import { PURPOSE_OPTIONS, LEVEL_COLORS } from '../../lib/constants'
import type { ProjectIdea } from '../../lib/types'

interface Props {
  ideas: ProjectIdea[]
  purpose: string
  role: string
  originalIdea: string
  onSelect: (idea: ProjectIdea) => void
  onMoreAlternatives?: () => void
}

export default function AlternativesCard({
  ideas,
  purpose,
  role,
  originalIdea,
  onSelect,
  onMoreAlternatives,
}: Props) {
  const purposeLabel = PURPOSE_OPTIONS.find(p => p.id === purpose)?.label || purpose

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden max-w-2xl">
      <div className="px-5 py-3 border-b border-[#21262d]">
        <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-0.5">
          Alternative Projects
        </div>
        <p className="text-xs text-[#484f58]">
          Each option addresses specific weaknesses of your original idea ·
          {purposeLabel}{role ? ` · ${role}` : ''}
        </p>
      </div>

      {/* Original idea reminder */}
      <div className="px-5 py-3 border-b border-[#21262d] bg-[#0d1117]">
        <div className="text-xs font-mono text-[#30363d] mb-1">
          Your original idea
        </div>
        <p className="text-xs text-[#484f58] leading-relaxed">
          {originalIdea.slice(0, 100)}
          {originalIdea.length > 100 ? '...' : ''}
        </p>
      </div>

      <div className="p-4 space-y-3">
        {ideas.map((idea, i) => (
          <button
            key={i}
            onClick={() => onSelect(idea)}
            className="w-full text-left bg-[#0d1117] border border-[#30363d] rounded-xl p-4 hover:border-[#f0b429]/30 hover:bg-[#161b22] transition-colors group"
          >
            {/* Title + level */}
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="font-medium text-[#e6edf3] group-hover:text-[#f0b429] transition-colors text-sm">
                {idea.title}
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full border flex-shrink-0 ${
                LEVEL_COLORS[idea.level] || LEVEL_COLORS['Intermediate']
              }`}>
                {idea.level}
              </span>
            </div>

            {/* One liner */}
            <p className="text-xs text-[#484f58] mb-3 leading-relaxed">
              {idea.one_liner}
            </p>

            {/* Why better than original */}
            {idea.why_better_than_original && (
              <div className="bg-[#1a2e1a] border border-[#2ea04320] rounded-lg px-3 py-2 mb-3">
                <div className="text-xs font-mono text-[#3fb950]/50 mb-1">
                  Why this beats your original
                </div>
                <p className="text-xs text-[#8b949e] leading-relaxed">
                  {idea.why_better_than_original}
                </p>
              </div>
            )}

            {/* Tech stack */}
            {idea.tech_stack && idea.tech_stack.length > 0 && (
              <div className="mb-3">
                <div className="text-xs font-mono text-[#30363d] mb-1.5">
                  Tech stack
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {idea.tech_stack.map((tech, j) => (
                    <span key={j}
                      className="text-xs px-2 py-0.5 bg-[#1c2333] border border-[#58a6ff]/15 rounded text-[#58a6ff]/70">
                      {tech}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Skills */}
            {idea.skills_demonstrated && idea.skills_demonstrated.length > 0 && (
              <div className="mb-3">
                <div className="text-xs font-mono text-[#30363d] mb-1.5">
                  Skills demonstrated
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {idea.skills_demonstrated.map((skill, j) => (
                    <span key={j}
                      className="text-xs px-2 py-0.5 bg-[#161b22] border border-[#30363d] rounded text-[#484f58]">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Footer */}
            <div className="flex items-center justify-between text-xs text-[#30363d] pt-2 border-t border-[#21262d]">
              <span>⏱ {idea.build_time}</span>
              <span className="text-[#f0b429]/30 group-hover:text-[#f0b429] transition-colors">
                Select →
              </span>
            </div>
          </button>
        ))}
      </div>

      {onMoreAlternatives && (
        <div className="px-4 pb-4">
          <button
            onClick={onMoreAlternatives}
            className="w-full py-2.5 bg-[#0d1117] border border-[#30363d] rounded-lg text-xs font-mono text-[#484f58] hover:text-[#e6edf3] hover:border-[#8b949e] transition-colors"
          >
            Show more alternatives →
          </button>
        </div>
      )}
    </div>
  )
}