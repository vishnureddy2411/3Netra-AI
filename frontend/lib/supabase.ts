// ─────────────────────────────────────────────
// Supabase client singleton
// Used for auth and database operations
// ─────────────────────────────────────────────

import { createClient } from '@supabase/supabase-js'

const supabaseUrl  = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseAnon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

console.log('Supabase URL:', supabaseUrl ? 'found' : 'MISSING')
console.log('Supabase Anon:', supabaseAnon ? 'found' : 'MISSING')

console.log('Supabase URL:', supabaseUrl ? 'found' : 'MISSING')
console.log('Supabase Anon:', supabaseAnon ? 'found' : 'MISSING')

if (!supabaseUrl || !supabaseAnon) {
  console.warn('Supabase environment variables missing')
}

export const supabase = createClient(supabaseUrl, supabaseAnon, {
  auth: {
    autoRefreshToken:  true,
    persistSession:    true,
    detectSessionInUrl: true,
    storageKey:        '3netra-ai-auth',
  },
})

// ── Types ─────────────────────────────────────

export interface AuthUser {
  id: string
  email: string
  created_at: string
}

export interface UserProject {
  id: string
  user_id: string
  title: string
  description: string
  target_role: string
  purpose: string
  difficulty_level: string
  estimated_duration: string
  overall_status: 'pending' | 'in_progress' | 'completed' | 'archived'
  current_stage: string
  progress_percentage: number
  tech_stack: string[]
  risks: string[]
  portfolio_value: string
  full_idea: string
  deep_analysis: any
  verdict: any
  internal_project_id: string
  created_at: string
  updated_at: string
  stages?: ProjectStage[]
}

export interface ProjectStage {
  id: string
  project_id: string
  stage_name: string
  stage_status: 'pending' | 'in_progress' | 'completed' | 'skipped'
  output_data: any
  completed_at: string | null
  created_at: string
}

export interface ChatMessage {
  id: string
  project_id: string
  user_id: string
  role: string
  content_type: string
  content: any
  created_at: string
}