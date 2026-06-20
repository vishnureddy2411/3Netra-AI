'use client'

import { useState } from 'react'
import { signIn, signUp } from '../../lib/auth'

interface Props {
  onSuccess: () => void
}

// ── Validators ────────────────────────────────

const validateFullName = (name: string): string => {
  if (!name.trim()) return 'Full name is required'
  if (name.trim().length < 2) return 'Name must be at least 2 characters'
  if (name.trim().length > 50) return 'Name must be under 50 characters'
  if (!/^[a-zA-Z\s'-]+$/.test(name.trim()))
    return 'Name can only contain letters, spaces, hyphens, and apostrophes'
  return ''
}

const validateEmail = (email: string): string => {
  if (!email.trim()) return 'Email is required'
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
  if (!emailRegex.test(email.trim())) return 'Enter a valid email address'
  return ''
}

const validatePassword = (password: string): string => {
  if (!password) return 'Password is required'
  if (password.length < 8) return 'Password must be at least 8 characters'
  if (!/[A-Z]/.test(password)) return 'Password must contain at least one uppercase letter'
  if (!/[0-9]/.test(password)) return 'Password must contain at least one number'
  if (!/[^a-zA-Z0-9]/.test(password)) return 'Password must contain at least one special character'
  return ''
}

const validateConfirmPassword = (password: string, confirm: string): string => {
  if (!confirm) return 'Please confirm your password'
  if (password !== confirm) return 'Passwords do not match'
  return ''
}

// ── Password strength indicator ───────────────

function PasswordStrength({ password }: { password: string }) {
  if (!password) return null

  const checks = [
    { label: '8+ characters', pass: password.length >= 8 },
    { label: 'Uppercase letter', pass: /[A-Z]/.test(password) },
    { label: 'Number', pass: /[0-9]/.test(password) },
    { label: 'Special character', pass: /[^a-zA-Z0-9]/.test(password) },
  ]

  const passed = checks.filter(c => c.pass).length
  const strength = passed <= 1 ? 'Weak' : passed <= 2 ? 'Fair' : passed <= 3 ? 'Good' : 'Strong'
  const strengthColor =
    passed <= 1 ? 'bg-[#f85149]' :
    passed <= 2 ? 'bg-amber-400' :
    passed <= 3 ? 'bg-[#58a6ff]' :
    'bg-[#3fb950]'

  return (
    <div className="mt-2 space-y-2">
      {/* Strength bar */}
      <div className="flex items-center gap-2">
        <div className="flex-1 bg-[#21262d] rounded-full h-1.5">
          <div
            className={`h-1.5 rounded-full transition-all ${strengthColor}`}
            style={{ width: `${(passed / 4) * 100}%` }}
          />
        </div>
        <span className={`text-xs font-mono ${
          passed <= 1 ? 'text-[#f85149]' :
          passed <= 2 ? 'text-amber-400' :
          passed <= 3 ? 'text-[#58a6ff]' :
          'text-[#3fb950]'
        }`}>
          {strength}
        </span>
      </div>

      {/* Checklist */}
      <div className="grid grid-cols-2 gap-1">
        {checks.map((c, i) => (
          <div key={i} className="flex items-center gap-1">
            <span className={`text-xs ${c.pass ? 'text-[#3fb950]' : 'text-[#30363d]'}`}>
              {c.pass ? '✓' : '○'}
            </span>
            <span className={`text-xs ${c.pass ? 'text-[#484f58]' : 'text-[#30363d]'}`}>
              {c.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main form ─────────────────────────────────

export default function AuthForm({ onSuccess }: Props) {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')

  const [fullName,        setFullName]        = useState('')
  const [email,           setEmail]           = useState('')
  const [password,        setPassword]        = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm,  setShowConfirm]  = useState(false)

  const clearForm = () => {
    setFullName('')
    setEmail('')
    setPassword('')
    setConfirmPassword('')
    setErrors({})
    setError('')
    setMessage('')
  }

  const validateAll = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (mode === 'signup') {
      const nameErr = validateFullName(fullName)
      if (nameErr) newErrors.fullName = nameErr
    }

    const emailErr = validateEmail(email)
    if (emailErr) newErrors.email = emailErr

    const passErr = validatePassword(password)
    if (passErr) newErrors.password = passErr

    if (mode === 'signup') {
      const confirmErr = validateConfirmPassword(password, confirmPassword)
      if (confirmErr) newErrors.confirmPassword = confirmErr
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // Inline field validation on blur
  const handleBlur = (field: string, value: string) => {
    let err = ''
    if (field === 'fullName') err = validateFullName(value)
    if (field === 'email')    err = validateEmail(value)
    if (field === 'password') err = validatePassword(value)
    if (field === 'confirmPassword') err = validateConfirmPassword(password, value)
    setErrors(prev => ({ ...prev, [field]: err }))
  }

  const handleSubmit = async () => {
    if (!validateAll()) return

    setIsLoading(true)
    setError('')
    setMessage('')

    try {
      if (mode === 'signin') {
        await signIn(email.trim(), password)
        onSuccess()
      } else {
        const data = await signUp(email.trim(), password, fullName.trim())
        if (data.user && !data.session) {
          setMessage('Account created! Check your email to confirm before signing in.')
        } else if (data.session) {
          onSuccess()
        }
      }
    } catch (err: any) {
      const msg = err.message || 'Something went wrong'

      // Handle known Supabase errors
      if (msg.includes('already registered') || msg.includes('already exists')) {
        setErrors(prev => ({ ...prev, email: 'This email is already registered. Try signing in.' }))
      } else if (msg.includes('Invalid login credentials')) {
        setError('Incorrect email or password. Please try again.')
      } else if (msg.includes('Email not confirmed')) {
        setError('Please confirm your email before signing in.')
      } else {
        setError(msg)
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="w-full max-w-sm">

      {/* Logo */}
      <div className="flex flex-col items-center mb-8">
        <div className="w-12 h-12 rounded-2xl bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center mb-4">
          <span className="text-[#f0b429] text-xl font-bold">3</span>
        </div>
        <h1 className="text-2xl font-semibold text-[#e6edf3] mb-1">
          3Netra<span className="text-[#f0b429]">-AI</span>
        </h1>
        <p className="text-sm text-[#484f58]">Your AI engineering team</p>
      </div>

      {/* Tab switcher */}
      <div className="flex bg-[#161b22] border border-[#30363d] rounded-xl p-1 mb-6">
        <button
          onClick={() => { setMode('signin'); clearForm() }}
          className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
            mode === 'signin'
              ? 'bg-[#0d1117] text-[#e6edf3]'
              : 'text-[#484f58] hover:text-[#8b949e]'
          }`}
        >
          Sign In
        </button>
        <button
          onClick={() => { setMode('signup'); clearForm() }}
          className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
            mode === 'signup'
              ? 'bg-[#0d1117] text-[#e6edf3]'
              : 'text-[#484f58] hover:text-[#8b949e]'
          }`}
        >
          Sign Up
        </button>
      </div>

      <div className="space-y-4">

        {/* Full name */}
        {mode === 'signup' && (
          <div>
            <label className="text-xs font-mono text-[#484f58] mb-1.5 block uppercase tracking-widest">
              Full Name
            </label>
            <input
              type="text"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              onBlur={() => handleBlur('fullName', fullName)}
              placeholder="Enter FullName"
              autoFocus
              className={`w-full bg-[#161b22] border rounded-lg px-3 py-2.5 text-sm text-[#e6edf3] placeholder-[#484f58] outline-none transition-colors ${
                errors.fullName
                  ? 'border-[#f85149]/50 focus:border-[#f85149]'
                  : 'border-[#30363d] focus:border-[#f0b429]/30'
              }`}
            />
            {errors.fullName && (
              <p className="text-xs text-[#f85149] mt-1">{errors.fullName}</p>
            )}
          </div>
        )}

        {/* Email */}
        <div>
          <label className="text-xs font-mono text-[#484f58] mb-1.5 block uppercase tracking-widest">
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            onBlur={() => handleBlur('email', email)}
            onKeyDown={e => { if (e.key === 'Enter') handleSubmit() }}
            placeholder="you@example.com"
            autoFocus={mode === 'signin'}
            className={`w-full bg-[#161b22] border rounded-lg px-3 py-2.5 text-sm text-[#e6edf3] placeholder-[#484f58] outline-none transition-colors ${
              errors.email
                ? 'border-[#f85149]/50 focus:border-[#f85149]'
                : 'border-[#30363d] focus:border-[#f0b429]/30'
            }`}
          />
          {errors.email && (
            <p className="text-xs text-[#f85149] mt-1">{errors.email}</p>
          )}
        </div>

        {/* Password */}
        <div>
          <label className="text-xs font-mono text-[#484f58] mb-1.5 block uppercase tracking-widest">
            Password
          </label>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={e => setPassword(e.target.value)}
              onBlur={() => handleBlur('password', password)}
              onKeyDown={e => { if (e.key === 'Enter' && mode === 'signin') handleSubmit() }}
              placeholder="••••••••"
              className={`w-full bg-[#161b22] border rounded-lg px-3 py-2.5 pr-10 text-sm text-[#e6edf3] placeholder-[#484f58] outline-none transition-colors ${
                errors.password
                  ? 'border-[#f85149]/50 focus:border-[#f85149]'
                  : 'border-[#30363d] focus:border-[#f0b429]/30'
              }`}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#484f58] hover:text-[#8b949e] text-xs"
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>
          {errors.password && (
            <p className="text-xs text-[#f85149] mt-1">{errors.password}</p>
          )}
          {mode === 'signup' && <PasswordStrength password={password} />}
        </div>

        {/* Confirm password */}
        {mode === 'signup' && (
          <div>
            <label className="text-xs font-mono text-[#484f58] mb-1.5 block uppercase tracking-widest">
              Confirm Password
            </label>
            <div className="relative">
              <input
                type={showConfirm ? 'text' : 'password'}
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                onBlur={() => handleBlur('confirmPassword', confirmPassword)}
                onKeyDown={e => { if (e.key === 'Enter') handleSubmit() }}
                placeholder="••••••••"
                className={`w-full bg-[#161b22] border rounded-lg px-3 py-2.5 pr-10 text-sm text-[#e6edf3] placeholder-[#484f58] outline-none transition-colors ${
                  errors.confirmPassword
                    ? 'border-[#f85149]/50 focus:border-[#f85149]'
                    : confirmPassword && password === confirmPassword
                    ? 'border-[#3fb950]/30 focus:border-[#3fb950]/50'
                    : 'border-[#30363d] focus:border-[#f0b429]/30'
                }`}
              />
              <button
                type="button"
                onClick={() => setShowConfirm(!showConfirm)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#484f58] hover:text-[#8b949e] text-xs"
              >
                {showConfirm ? 'Hide' : 'Show'}
              </button>
            </div>
            {errors.confirmPassword && (
              <p className="text-xs text-[#f85149] mt-1">{errors.confirmPassword}</p>
            )}
            {confirmPassword && password === confirmPassword && !errors.confirmPassword && (
              <p className="text-xs text-[#3fb950] mt-1">✓ Passwords match</p>
            )}
          </div>
        )}

        {/* Global error */}
        {error && (
          <div className="bg-[#2d1b1b] border border-[#f85149]/20 rounded-lg px-3 py-2.5">
            <p className="text-xs text-[#f85149] leading-relaxed">{error}</p>
          </div>
        )}

        {/* Success message */}
        {message && (
          <div className="bg-[#1a2e1a] border border-[#3fb950]/20 rounded-lg px-3 py-2.5">
            <p className="text-xs text-[#3fb950] leading-relaxed">{message}</p>
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={isLoading}
          className="w-full py-3 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-sm"
        >
          {isLoading
            ? mode === 'signin' ? 'Signing in...' : 'Creating account...'
            : mode === 'signin' ? 'Sign In →' : 'Create Account →'
          }
        </button>

        {/* Forgot password */}
        {mode === 'signin' && (
          <p className="text-xs text-[#484f58] text-center">
            Forgot password?{' '}
            <button
              onClick={async () => {
                if (!email.trim()) {
                  setErrors({ email: 'Enter your email first' })
                  return
                }
                const emailErr = validateEmail(email)
                if (emailErr) { setErrors({ email: emailErr }); return }
                try {
                  const { resetPassword } = await import('../../lib/auth')
                  await resetPassword(email.trim())
                  setMessage('Password reset email sent. Check your inbox.')
                } catch (e: any) {
                  setError(e.message || 'Reset failed')
                }
              }}
              className="text-[#f0b429] hover:text-[#e0a419] transition-colors"
            >
              Reset it
            </button>
          </p>
        )}
      </div>

      <p className="text-xs text-[#30363d] text-center mt-6">
        Your projects are private and secure
      </p>
    </div>
  )
}