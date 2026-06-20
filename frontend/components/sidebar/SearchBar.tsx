'use client'

interface Props {
  value: string
  onChange: (val: string) => void
}

export default function SearchBar({ value, onChange }: Props) {
  return (
    <div className="relative">
      <div className="absolute left-3 top-1/2 -translate-y-1/2 text-[#484f58] text-xs">
        🔍
      </div>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder="Search projects..."
        className="w-full bg-[#0d1117] border border-[#21262d] rounded-lg pl-8 pr-3 py-2 text-xs text-[#e6edf3] placeholder-[#30363d] outline-none focus:border-[#30363d] transition-colors"
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-[#484f58] hover:text-[#e6edf3] transition-colors text-xs"
        >
          ✕
        </button>
      )}
    </div>
  )
}