// ─────────────────────────────────────────────
// All constants for 3Netra-AI frontend
// ─────────────────────────────────────────────

export const API = 'http://localhost:8000/api'

export const PURPOSE_OPTIONS = [
  {
    id: 'portfolio',
    label: 'Portfolio',
    icon: '🗂️',
    desc: 'Land a job — project goes on resume and GitHub',
    research_focus: 'what impresses hiring managers, ATS keywords, role-specific projects',
    council_lens: 'hiring signals, interview talking points, resume impact, differentiation from tutorials',
  },
  {
    id: 'startup',
    label: 'Startup',
    icon: '🚀',
    desc: 'Build a real product with users and revenue',
    research_focus: 'market size, competitors, monetization models, user acquisition',
    council_lens: 'TAM, revenue model, competitive moat, solo build feasibility',
  },
  {
    id: 'learning',
    label: 'Learning',
    icon: '📚',
    desc: 'Develop a specific skill or understand a technology',
    research_focus: 'technology learning curve, common pitfalls, best resources',
    council_lens: 'complexity curve, skill building path, prerequisites, time investment',
  },
]

export const STAGES = [
  {
    num: '01',
    name: 'Research',
    desc: 'Market data · competitors · technology trends',
    color: 'text-blue-400',
    border: 'border-blue-400/20',
    bg: 'bg-blue-400/5',
  },
  {
    num: '02',
    name: 'Expert Analysis',
    desc: '5 specialists review · peer check · final verdict',
    color: 'text-amber-400',
    border: 'border-amber-400/20',
    bg: 'bg-amber-400/5',
  },
  {
    num: '03',
    name: 'Architecture',
    desc: 'System design · database · API contracts',
    color: 'text-purple-400',
    border: 'border-purple-400/20',
    bg: 'bg-purple-400/5',
  },
  {
    num: '04',
    name: 'Build',
    desc: 'Code per module · live preview · approval gates',
    color: 'text-emerald-400',
    border: 'border-emerald-400/20',
    bg: 'bg-emerald-400/5',
  },
]

export const LEVEL_COLORS: Record<string, string> = {
  Beginner: 'text-emerald-400 border-emerald-400/25 bg-emerald-400/5',
  Intermediate: 'text-amber-400 border-amber-400/25 bg-amber-400/5',
  Expert: 'text-purple-400 border-purple-400/25 bg-purple-400/5',
}