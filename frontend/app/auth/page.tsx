// ─────────────────────────────────────────────
// Auth page — Login / Signup
// Redirects to main page after successful auth
// ─────────────────────────────────────────────

'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import AuthForm from '../../components/auth/AuthForm'
import { getSession } from '../../lib/auth'

export default function AuthPage() {
  const router = useRouter()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    // If already logged in redirect to main page
    getSession()
      .then(session => {
        if (session) router.replace('/')
        else setChecking(false)
      })
      .catch(() => setChecking(false))
  }, [router])

  const handleSuccess = () => {
    router.replace('/')
  }

  if (checking) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0d1117]">
        <div className="flex gap-1">
          {[0, 1, 2].map(i => (
            <div
              key={i}
              style={{ animationDelay: `${i * 0.2}s` }}
              className="w-2 h-2 rounded-full bg-[#f0b429] animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#0d1117] px-4">
      {/* Background pattern */}
      <div className="absolute inset-0 bg-[#0d1117]">
        <div className="absolute inset-0"
          style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, #21262d 1px, transparent 0)`,
            backgroundSize: '32px 32px',
            opacity: 0.4,
          }}
        />
      </div>

      {/* Glow effect */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-[#f0b429]/3 rounded-full blur-3xl pointer-events-none" />

      {/* Form container */}
      <div className="relative z-10 w-full max-w-sm">
        <AuthForm onSuccess={handleSuccess} />
      </div>

      {/* Bottom text */}
      <p className="relative z-10 text-xs text-[#21262d] mt-8 font-mono">
        Research · Analysis · Architecture · Build · Deploy
      </p>
    </div>
  )
}