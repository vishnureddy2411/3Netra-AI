'use client'

import { useState, useEffect, useRef } from 'react'

interface Props {
  onSignOut: () => void
  role?: string
  purpose?: string
}

export default function UserMenu({ onSignOut, role, purpose }: Props) {
  const [open, setOpen] = useState(false)
  const [user, setUser] = useState<{ email: string; name: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const menuRef = useRef<HTMLDivElement>(null)

  // Load user session
  useEffect(() => {
    import('../../lib/auth').then(({ getSession }) => {
      getSession().then(session => {
        if (session?.user) {
          setUser({
            email: session.user.email || '',
            name:  session.user.user_metadata?.full_name ||
                   session.user.email?.split('@')[0] || 'User',
          })
        }
      }).catch(() => {}).finally(() => setLoading(false))
    })
  }, [])

  // Close menu when clicking outside
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // All hooks declared above — safe to return conditionally now
  if (loading) {
    return (
      <div className="w-8 h-8 rounded-full bg-[#161b22] border border-[#30363d] animate-pulse" />
    )
  }

  if (!user) return null

  const initials = user.name
    .split(' ')
    .map(w => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  return (
    <div ref={menuRef} className="relative">

      {/* Avatar button */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-2 py-1.5 bg-[#161b22] border border-[#30363d] rounded-lg hover:border-[#484f58] transition-colors"
      >
        <div className="w-6 h-6 rounded-full bg-[#f0b429]/20 border border-[#f0b429]/30 flex items-center justify-center">
          <span className="text-[#f0b429] text-xs font-bold">{initials}</span>
        </div>
        <span className="text-xs text-[#8b949e] hidden sm:block max-w-24 truncate">
          {user.name.split(' ')[0]}
        </span>
        <span className={`text-[#484f58] text-xs transition-transform ${open ? 'rotate-180' : ''}`}>
          ▾
        </span>
      </button>

      {/* Dropdown menu */}
      {open && (
        <div className="absolute right-0 top-10 w-64 bg-[#161b22] border border-[#30363d] rounded-xl shadow-2xl shadow-black/50 z-50 overflow-hidden">

          {/* User info */}
          <div className="px-4 py-3 border-b border-[#21262d]">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-[#f0b429]/20 border border-[#f0b429]/30 flex items-center justify-center flex-shrink-0">
                <span className="text-[#f0b429] text-sm font-bold">{initials}</span>
              </div>
              <div className="min-w-0">
                <div className="text-sm font-medium text-[#e6edf3] truncate">{user.name}</div>
                <div className="text-xs text-[#484f58] truncate">{user.email}</div>
              </div>
            </div>

            {/* Current setup */}
            {(role || purpose) && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {role && (
                  <span className="text-xs px-2 py-0.5 bg-[#0d1117] border border-[#30363d] rounded text-[#8b949e]">
                    {role}
                  </span>
                )}
                {purpose && (
                  <span className="text-xs px-2 py-0.5 bg-[#0d1117] border border-[#30363d] rounded text-[#8b949e] capitalize">
                    {purpose}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Menu items */}
          <div className="py-1">
            <button
              onClick={() => { setOpen(false); window.location.href = '/dashboard' }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d] transition-colors text-left"
            >
              <span>🗂️</span>
              <div>
                <div className="text-sm">My Projects</div>
                <div className="text-xs text-[#484f58]">View all your projects</div>
              </div>
            </button>

            <button
              onClick={() => { setOpen(false); window.location.href = '/settings' }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d] transition-colors text-left"
            >
              <span>⚙️</span>
              <div>
                <div className="text-sm">Settings</div>
                <div className="text-xs text-[#484f58]">Preferences and account</div>
              </div>
            </button>
          </div>

          {/* Coming soon */}
          <div className="px-4 py-2 border-t border-[#21262d] bg-[#0d1117]">
            <div className="text-xs font-mono text-[#30363d] mb-1">Coming soon</div>
            <div className="flex flex-wrap gap-1">
              {['Google Sign-in', 'Email Confirm', 'Export PDF'].map(f => (
                <span key={f}
                  className="text-xs px-1.5 py-0.5 bg-[#161b22] border border-[#21262d] rounded text-[#30363d]">
                  {f}
                </span>
              ))}
            </div>
          </div>

          {/* Sign out */}
          <div className="p-2 border-t border-[#21262d]">
            <button
              onClick={() => { setOpen(false); onSignOut() }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[#f85149] hover:bg-[#2d1b1b] rounded-lg transition-colors"
            >
              <span>→</span>
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}