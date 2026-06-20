// ─────────────────────────────────────────────
// Auth helpers for 3Netra-AI
// Handles login, signup, logout, session
// ─────────────────────────────────────────────

import { supabase } from './supabase'

// ── Sign up ───────────────────────────────────

export async function signUp(email: string, password: string, fullName: string) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: { full_name: fullName },
    },
  })
  if (error) throw error
  return data
}

// ── Sign in ───────────────────────────────────

export async function signIn(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })
  if (error) throw error
  return data
}

// ── Sign out ──────────────────────────────────

export async function signOut() {
  const { error } = await supabase.auth.signOut()
  if (error) throw error
}

// ── Get current session ───────────────────────

export async function getSession() {
  const { data: { session }, error } = await supabase.auth.getSession()
  if (error) throw error
  return session
}

// ── Get current user ──────────────────────────

export async function getCurrentUser() {
  const { data: { user }, error } = await supabase.auth.getUser()
  if (error) throw error
  return user
}

// ── Get access token ──────────────────────────
// Used to attach JWT to backend API calls

export async function getAccessToken(): Promise<string | null> {
  const session = await getSession()
  return session?.access_token || null
}

// ── Auth state change listener ────────────────

export function onAuthStateChange(
  callback: (event: string, session: any) => void
) {
  return supabase.auth.onAuthStateChange(callback)
}

// ── Reset password ────────────────────────────

export async function resetPassword(email: string) {
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/auth/reset`,
  })
  if (error) throw error
}

// ── Authenticated API call helper ─────────────
// Attaches JWT token to every backend request

export async function authFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  let token: string | null = null

  try {
    const { data: { session } } = await supabase.auth.getSession()
    token = session?.access_token || null

    if (!token) {
      const { data: refreshed } = await supabase.auth.refreshSession()
      token = refreshed.session?.access_token || null
    }
  } catch (_err) {
    token = null
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  return fetch(url, { ...options, headers })
}

// ── Authenticated POST ────────────────────────

export async function authPost(url: string, body: object) {
  const res = await authFetch(url, {
    method: 'POST',
    body: JSON.stringify(body),
    headers: {
      'Content-Type': 'application/json',
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }))
    throw new Error(err.error || `${url} failed`)
  }
  return res.json()
}

// ── Authenticated GET ─────────────────────────

export async function authGet(url: string) {
  const res = await authFetch(url, { method: 'GET' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }))
    throw new Error(err.error || `${url} failed`)
  }
  return res.json()
}