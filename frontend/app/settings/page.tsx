// ─────────────────────────────────────────────
// Settings page
// User preferences and account management
// ─────────────────────────────────────────────

'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getSession, signOut } from '../../lib/auth'

export default function SettingsPage() {
  const router = useRouter()
  const [user,        setUser]        = useState<{ email: string; name: string } | null>(null)
  const [fullName,    setFullName]    = useState('')
  const [targetRole,  setTargetRole]  = useState('')
  const [isSaving,    setIsSaving]    = useState(false)
  const [message,     setMessage]     = useState('')
  const [activeTab,   setActiveTab]   = useState<'profile' | 'account' | 'reminders'>('profile')

  useEffect(() => {
    getSession().then(session => {
      if (!session) { router.replace('/auth'); return }
      const u = session.user
      setUser({
        email: u.email || '',
        name:  u.user_metadata?.full_name || u.email?.split('@')[0] || 'User',
      })
      setFullName(u.user_metadata?.full_name || '')
    }).catch(() => router.replace('/auth'))
  }, [])

  const handleSaveProfile = async () => {
    setIsSaving(true)
    setMessage('')
    try {
      // Save to Supabase user metadata
      const { supabase } = await import('../../lib/supabase')
      await supabase.auth.updateUser({
        data: { full_name: fullName, target_role: targetRole }
      })
      setMessage('Profile saved successfully.')
      setUser(prev => prev ? { ...prev, name: fullName } : null)
      setTimeout(() => router.push('/'), 1000)
    } catch (e: any) {
      setMessage(`Error: ${e.message}`)
    } finally {
      setIsSaving(false)
    }
  }

  const handleSignOut = async () => {
    await signOut()
    router.replace('/auth')
  }

  const TABS = [
    { id: 'profile',   label: 'Profile'   },
    { id: 'account',   label: 'Account'   },
    { id: 'reminders', label: 'Reminders' },
  ] as const

  if (!user) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0d1117]">
        <div className="flex gap-1">
          {[0,1,2].map(i => (
            <div key={i} style={{ animationDelay: `${i*0.2}s` }}
              className="w-2 h-2 rounded-full bg-[#f0b429] animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  const initials = user.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">

      {/* Header */}
      <header className="border-b border-[#21262d] px-6 py-4 flex items-center justify-between sticky top-0 bg-[#0d1117]/95 backdrop-blur-sm z-10">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push('/')}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="w-7 h-7 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center">
              <span className="text-[#f0b429] text-sm font-bold">3</span>
            </div>
            <span className="text-sm font-semibold">
              3Netra<span className="text-[#f0b429]">-AI</span>
            </span>
          </button>
          <span className="text-[#30363d]">/</span>
          <span className="text-sm text-[#8b949e]">Settings</span>
        </div>
        <button onClick={() => router.push('/')}
          className="text-xs px-3 py-1.5 bg-[#161b22] border border-[#30363d] text-[#8b949e] hover:text-[#e6edf3] rounded-lg transition-colors font-mono">
          ← Back
        </button>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-8">

        {/* User avatar */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-16 h-16 rounded-2xl bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center">
            <span className="text-[#f0b429] text-xl font-bold">{initials}</span>
          </div>
          <div>
            <h1 className="text-xl font-semibold">{user.name}</h1>
            <p className="text-sm text-[#484f58]">{user.email}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-[#161b22] border border-[#30363d] rounded-xl p-1">
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-[#0d1117] text-[#e6edf3]'
                  : 'text-[#484f58] hover:text-[#8b949e]'
              }`}>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Profile tab */}
        {activeTab === 'profile' && (
          <div className="space-y-4">
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 space-y-4">
              <h2 className="text-sm font-medium text-[#e6edf3]">Profile Information</h2>

              <div>
                <label className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-1.5 block">
                  Full Name
                </label>
                <input type="text" value={fullName} onChange={e => setFullName(e.target.value)}
                  placeholder="Your full name"
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2.5 text-sm text-[#e6edf3] placeholder-[#484f58] outline-none focus:border-[#f0b429]/30 transition-colors" />
              </div>

              <div>
                <label className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-1.5 block">
                  Email
                </label>
                <input type="email" value={user.email} disabled
                  className="w-full bg-[#0d1117] border border-[#21262d] rounded-lg px-3 py-2.5 text-sm text-[#484f58] outline-none cursor-not-allowed" />
                <p className="text-xs text-[#30363d] mt-1">Email cannot be changed</p>
              </div>

              <div>
                <label className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-1.5 block">
                  Default Target Role
                </label>
                <input type="text" value={targetRole} onChange={e => setTargetRole(e.target.value)}
                  placeholder="e.g. ML Engineer, Backend Engineer..."
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2.5 text-sm text-[#e6edf3] placeholder-[#484f58] outline-none focus:border-[#f0b429]/30 transition-colors" />
                <p className="text-xs text-[#30363d] mt-1">Pre-fills the role field when starting new projects</p>
              </div>

              {message && (
                <div className={`rounded-lg px-3 py-2 text-xs ${
                  message.startsWith('Error')
                    ? 'bg-[#2d1b1b] border border-[#f85149]/20 text-[#f85149]'
                    : 'bg-[#1a2e1a] border border-[#3fb950]/20 text-[#3fb950]'
                }`}>
                  {message}
                </div>
              )}

              <button onClick={handleSaveProfile} disabled={isSaving}
                className="w-full py-2.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] disabled:opacity-40 transition-colors text-sm">
                {isSaving ? 'Saving...' : 'Save Profile'}
              </button>
            </div>
          </div>
        )}

        {/* Account tab */}
        {activeTab === 'account' && (
          <div className="space-y-4">
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 space-y-4">
              <h2 className="text-sm font-medium text-[#e6edf3]">Account Settings</h2>

              <div className="flex items-center justify-between py-3 border-b border-[#21262d]">
                <div>
                  <div className="text-sm text-[#e6edf3]">Sign Out</div>
                  <div className="text-xs text-[#484f58]">Sign out of your account on this device</div>
                </div>
                <button onClick={handleSignOut}
                  className="px-4 py-2 bg-[#2d1b1b] border border-[#f85149]/20 text-[#f85149] rounded-lg text-sm hover:border-[#f85149]/40 transition-colors">
                  Sign Out
                </button>
              </div>

              <div className="flex items-center justify-between py-3">
                <div>
                  <div className="text-sm text-[#e6edf3]">Delete Account</div>
                  <div className="text-xs text-[#484f58]">Permanently delete your account and all projects</div>
                </div>
                <button
                  onClick={() => setMessage('To delete your account, please contact support.')}
                  className="px-4 py-2 bg-[#161b22] border border-[#30363d] text-[#484f58] rounded-lg text-sm hover:text-[#f85149] hover:border-[#f85149]/20 transition-colors">
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Reminders tab */}
        {activeTab === 'reminders' && (
          <div className="space-y-4">
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 space-y-4">
              <h2 className="text-sm font-medium text-[#e6edf3]">Production Reminders</h2>
              <p className="text-xs text-[#484f58]">
                Things to enable before deploying to production.
              </p>

              {[
                {
                  title: 'Enable Email Confirmation',
                  desc: 'Currently disabled for development. Turn ON in Supabase → Authentication → Providers → Email → Confirm email.',
                  status: 'pending',
                  priority: 'High',
                },
                {
                  title: 'Add Google Sign-in',
                  desc: 'Set up OAuth in Google Cloud Console and add credentials to Supabase → Authentication → Providers → Google.',
                  status: 'pending',
                  priority: 'Medium',
                },
                {
                  title: 'Set Token Expiry',
                  desc: 'Review JWT token expiry time in Supabase → Settings → API → JWT Settings.',
                  status: 'pending',
                  priority: 'Medium',
                },
                {
                  title: 'Enable RLS Policies',
                  desc: 'Row Level Security is already enabled on all tables. Verify policies in Supabase → Table Editor.',
                  status: 'done',
                  priority: 'High',
                },
              ].map((item, i) => (
                <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border ${
                  item.status === 'done'
                    ? 'bg-[#1a2e1a] border-[#3fb950]/15'
                    : 'bg-[#0d1117] border-[#21262d]'
                }`}>
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-xs ${
                    item.status === 'done'
                      ? 'bg-[#3fb950]/20 text-[#3fb950]'
                      : 'bg-[#21262d] text-[#484f58]'
                  }`}>
                    {item.status === 'done' ? '✓' : '○'}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm text-[#e6edf3]">{item.title}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded font-mono ${
                        item.priority === 'High'
                          ? 'bg-[#2d1b1b] text-[#f85149]'
                          : 'bg-[#1c2333] text-[#58a6ff]'
                      }`}>
                        {item.priority}
                      </span>
                    </div>
                    <p className="text-xs text-[#484f58] leading-relaxed">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}