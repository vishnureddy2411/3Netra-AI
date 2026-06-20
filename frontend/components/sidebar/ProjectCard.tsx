// ─────────────────────────────────────────────
// Project Card — shown in sidebar
// Displays project status, progress, and actions
// ─────────────────────────────────────────────

'use client'

import type { UserProject } from '../../lib/supabase'
import { STATUS_COLORS, STATUS_LABELS, STAGE_LABELS, timeAgo } from '../../lib/projects'

interface Props {
  project: UserProject
  isActive: boolean
  onClick: () => void
}

export default function ProjectCard({ project, isActive, onClick }: Props) {
  const statusColor = STATUS_COLORS[project.overall_status] || STATUS_COLORS.pending
  const statusLabel = STATUS_LABELS[project.overall_status] || 'Pending'
  const stageLabel  = STAGE_LABELS[project.current_stage]  || project.current_stage

  const progress = project.progress_percentage || 0

  const progressColor =
    progress === 100 ? 'bg-[#3fb950]' :
    progress >= 50   ? 'bg-[#58a6ff]' :
    progress >= 20   ? 'bg-amber-400' :
    'bg-[#30363d]'

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-3 rounded-xl border transition-all group ${
        isActive
          ? 'bg-[#1c2333] border-[#58a6ff]/30'
          : 'bg-transparent border-transparent hover:bg-[#161b22] hover:border-[#30363d]'
      }`}
    >
      {/* Title + status */}
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className={`text-xs font-medium leading-relaxed line-clamp-2 flex-1 ${
          isActive ? 'text-[#e6edf3]' : 'text-[#8b949e] group-hover:text-[#e6edf3]'
        } transition-colors`}>
          {project.title}
        </div>
        <span className={`text-xs px-1.5 py-0.5 rounded-full border flex-shrink-0 font-mono ${statusColor}`}>
          {project.overall_status === 'in_progress' ? 'Active' : statusLabel}
        </span>
      </div>

      {/* Role */}
      {project.target_role && (
        <div className="text-xs text-[#484f58] mb-2 truncate">
          {project.target_role}
        </div>
      )}

      {/* Progress bar */}
      <div className="mb-1.5">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-[#30363d] font-mono">{stageLabel}</span>
          <span className="text-xs text-[#30363d] font-mono">{progress}%</span>
        </div>
        <div className="w-full bg-[#21262d] rounded-full h-1">
          <div
            className={`h-1 rounded-full transition-all ${progressColor}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Time ago */}
      <div className="text-xs text-[#30363d]">
        {timeAgo(project.updated_at)}
      </div>
    </button>
  )
}