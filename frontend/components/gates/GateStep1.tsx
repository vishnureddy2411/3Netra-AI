'use client'

interface Props {
  onAnswer: (val: string) => void
}

export default function GateStep1({ onAnswer }: Props) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 w-full max-w-md">
      <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-1">
        Getting Started
      </div>
      <p className="text-sm text-[#e6edf3] font-medium mb-1">
        Who are you building for?
      </p>
      <p className="text-xs text-[#484f58] mb-5 leading-relaxed">
        This determines how agents research, evaluate, and advise on your project.
      </p>

      <div className="space-y-2">
        <button
          onClick={() => onAnswer('student')}
          className="w-full text-left px-4 py-4 bg-[#0d1117] border border-[#30363d] rounded-xl hover:border-[#f0b429]/30 hover:bg-[#161b22] transition-all group"
        >
          <div className="flex items-start gap-3">
            <span className="text-xl flex-shrink-0 mt-0.5">🎓</span>
            <div>
              <div className="text-sm font-semibold text-[#e6edf3] group-hover:text-[#f0b429] transition-colors mb-0.5">
                Student / Job Seeker
              </div>
              <p className="text-xs text-[#484f58] leading-relaxed">
                Building a portfolio project, learning a technology, or preparing for interviews
              </p>
              <div className="text-xs font-mono text-[#30363d] mt-1.5">
                Get Hired · Learn & Grow
              </div>
            </div>
          </div>
        </button>

        <button
          onClick={() => onAnswer('professional')}
          className="w-full text-left px-4 py-4 bg-[#0d1117] border border-[#30363d] rounded-xl hover:border-[#f0b429]/30 hover:bg-[#161b22] transition-all group"
        >
          <div className="flex items-start gap-3">
            <span className="text-xl flex-shrink-0 mt-0.5">🏢</span>
            <div>
              <div className="text-sm font-semibold text-[#e6edf3] group-hover:text-[#f0b429] transition-colors mb-0.5">
                Professional / Employee
              </div>
              <p className="text-xs text-[#484f58] leading-relaxed">
                Solving a real business problem at work — delivery, ROI, and team adoption matter
              </p>
              <div className="text-xs font-mono text-[#30363d] mt-1.5">
                Work Project · Business Execution
              </div>
            </div>
          </div>
        </button>
      </div>
    </div>
  )
}