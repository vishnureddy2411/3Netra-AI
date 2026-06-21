'use client'

interface Props {
  filename: string
  content: string
  mimeType: string
  label: string
}

export default function DownloadCard({
  filename,
  content,
  mimeType,
  label,
}: Props) {
  const handleDownload = () => {
    const blob = new Blob([content], { type: mimeType })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getIcon = () => {
    if (filename.endsWith('.pdf'))  return '📄'
    if (filename.endsWith('.md'))   return '📝'
    if (filename.endsWith('.txt'))  return '📄'
    if (filename.endsWith('.svg'))  return '🖼️'
    if (filename.endsWith('.json')) return '📋'
    return '📎'
  }

  const getSize = () => {
    const bytes = new Blob([content]).size
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden max-w-sm">
      <div className="px-4 py-3 border-b border-[#21262d]">
        <div className="text-xs font-mono text-[#f0b429] uppercase tracking-widest mb-0.5">
          Ready to Download
        </div>
        <p className="text-xs text-[#484f58]">{label}</p>
      </div>

      <div className="px-4 py-4">
        <div className="flex items-center gap-3 bg-[#0d1117] border border-[#21262d] rounded-lg px-3 py-3 mb-4">
          <div className="text-2xl flex-shrink-0">{getIcon()}</div>
          <div className="min-w-0">
            <div className="text-sm font-medium text-[#e6edf3] truncate">
              {filename}
            </div>
            <div className="text-xs text-[#484f58]">
              {getSize()} · {mimeType.split('/')[1]?.toUpperCase() || 'FILE'}
            </div>
          </div>
        </div>

        <button
          onClick={handleDownload}
          className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors text-sm"
        >
          <span>↓</span>
          Download {filename}
        </button>
      </div>
    </div>
  )
}