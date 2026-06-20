// ─────────────────────────────────────────────
// Confirmation Gate Card
// Appears after user selects any project
// in both Flow 1 and Flow 2.
// User must explicitly choose to proceed
// or discuss doubts before diagrams run.
// ─────────────────────────────────────────────

'use client'

import type { SelectedProject } from '../../lib/types'

interface Props {
  selectedProject: SelectedProject
  onProceed: () => void
  onDiscuss: () => void
  disabled: boolean
}

export default function ConfirmationGateCard({
  selectedProject,
  onProceed,
  onDiscuss,
  disabled,
}: Props) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden max-w-2xl">

      {/* Header */}
      <div className="px-4 py-3 border-b border-[#21262d] bg-[#0d1117]">
        <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-0.5">
          Project Selected
        </div>
        <p className="text-xs text-[#484f58]">
          Before generating diagrams — confirm you are ready or discuss any doubts
        </p>
      </div>

      {/* Project summary */}
      <div className="px-4 py-4 space-y-4">

        {/* Title */}
        <div className="bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-3">
          <div className="text-xs font-mono text-[#484f58] mb-1">You selected</div>
          <div className="text-base font-semibold text-[#e6edf3] mb-1">
            {selectedProject.title}
          </div>
          {selectedProject.description && (
            <p className="text-xs text-[#484f58] leading-relaxed">
              {selectedProject.description.slice(0, 120)}
              {selectedProject.description.length > 120 ? '...' : ''}
            </p>
          )}
        </div>

        {/* Key details grid */}
        <div className="grid grid-cols-2 gap-2">
          {selectedProject.level && (
            <div className="bg-[#0d1117] border border-[#21262d] rounded-lg px-3 py-2">
              <div className="text-xs font-mono text-[#30363d] mb-1">Difficulty</div>
              <div className="text-xs text-[#8b949e]">{selectedProject.level}</div>
            </div>
          )}
          {selectedProject.buildTime && (
            <div className="bg-[#0d1117] border border-[#21262d] rounded-lg px-3 py-2">
              <div className="text-xs font-mono text-[#30363d] mb-1">Build time</div>
              <div className="text-xs text-[#8b949e]">{selectedProject.buildTime}</div>
            </div>
          )}
        </div>

        {/* Tech stack */}
        {selectedProject.techStack && selectedProject.techStack.length > 0 && (
          <div>
            <div className="text-xs font-mono text-[#30363d] mb-2">Tech stack</div>
            <div className="flex flex-wrap gap-1.5">
              {selectedProject.techStack.map((tech, i) => (
                <span key={i}
                  className="text-xs px-2 py-0.5 bg-[#1c2333] border border-[#58a6ff]/15 rounded text-[#58a6ff]/70">
                  {tech}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Skills demonstrated */}
        {selectedProject.skillsDemonstrated && selectedProject.skillsDemonstrated.length > 0 && (
          <div>
            <div className="text-xs font-mono text-[#30363d] mb-2">Skills demonstrated</div>
            <div className="flex flex-wrap gap-1.5">
              {selectedProject.skillsDemonstrated.slice(0, 5).map((skill, i) => (
                <span key={i}
                  className="text-xs px-2 py-0.5 bg-[#161b22] border border-[#30363d] rounded text-[#484f58]">
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Known risks */}
        {selectedProject.risks && selectedProject.risks.length > 0 && (
          <div>
            <div className="text-xs font-mono text-[#f85149]/40 mb-2">Known risks</div>
            <ul className="space-y-1.5">
              {selectedProject.risks.slice(0, 3).map((risk, i) => (
                <li key={i} className="flex items-start gap-1.5 text-xs text-[#484f58] leading-relaxed">
                  <span className="text-[#f85149]/40 mt-0.5 flex-shrink-0">⚠</span>
                  {risk.slice(0, 100)}{risk.length > 100 ? '...' : ''}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Confirmation question */}
        <div className="bg-[#1c2333] border border-[#58a6ff]/15 rounded-lg px-4 py-3">
          <p className="text-sm text-[#8b949e] leading-relaxed">
            Do you want to proceed to architecture diagrams, or would you like to
            discuss any doubts about this project first?
          </p>
        </div>

        {/* Action buttons */}
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={onProceed}
            disabled={disabled}
            className="flex flex-col items-center justify-center px-4 py-4 bg-[#1a2e1a] border border-[#3fb950]/25 rounded-xl hover:border-[#3fb950]/50 hover:bg-[#1a2e1a] transition-colors disabled:opacity-30 group"
          >
            <div className="text-lg mb-1.5">→</div>
            <div className="text-sm font-semibold text-[#3fb950] mb-0.5">
              Move to Next Step
            </div>
            <div className="text-xs text-[#484f58] text-center">
              Generate architecture diagrams
            </div>
          </button>

          <button
            onClick={onDiscuss}
            disabled={disabled}
            className="flex flex-col items-center justify-center px-4 py-4 bg-[#0d1117] border border-[#30363d] rounded-xl hover:border-[#f0b429]/30 hover:bg-[#161b22] transition-colors disabled:opacity-30 group"
          >
            <div className="text-lg mb-1.5">💬</div>
            <div className="text-sm font-semibold text-[#e6edf3] group-hover:text-[#f0b429] mb-0.5 transition-colors">
              Discuss Doubts
            </div>
            <div className="text-xs text-[#484f58] text-center">
              Ask questions before committing
            </div>
          </button>
        </div>
      </div>
    </div>
  )
}