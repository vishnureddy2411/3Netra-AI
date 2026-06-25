// ─────────────────────────────────────────────
// All constants for 3Netra-AI frontend
// ─────────────────────────────────────────────

export const API = 'http://localhost:8000/api'

export const PURPOSE_OPTIONS = [
  {
    id: 'job_hunt',
    label: 'Get Hired',
    icon: '🎯',
    desc: 'Build a portfolio project that lands you a job',
    output_preview: 'Resume bullets · Hiring manager analysis · Interview talking points',
    research_focus: 'what impresses hiring managers, ATS keywords, role-specific projects, GitHub portfolio best practices, recruiter screening signals',
    council_lens: 'hiring signal strength, interview talking points, resume impact, differentiation from tutorial projects, recruiter first impression',
  },
  {
    id: 'learning',
    label: 'Learn & Grow',
    icon: '📚',
    desc: 'Master a technology or skill through a hands-on project',
    output_preview: 'Skill progression · Complexity curve · Learning roadmap',
    research_focus: 'technology learning curve, common pitfalls, best learning resources, prerequisite skills, hands-on exercises',
    council_lens: 'complexity curve, skill building path, prerequisites, time investment, learning milestones, common beginner mistakes',
  },
  {
    id: 'professional',
    label: 'Work Project',
    icon: '🏢',
    desc: 'Solve a real business problem at work',
    output_preview: 'Business case · ROI analysis · Stakeholder justification · Delivery risk',
    research_focus: 'enterprise solutions, build vs buy tradeoffs, integration patterns, team adoption costs, ROI metrics, existing tool landscape, vendor comparison, maintenance burden',
    council_lens: 'business ROI, delivery timeline, team skill requirements, maintenance burden, stakeholder justification, integration complexity, build vs buy decision, long-term ownership cost',
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
  Beginner:     'text-emerald-400 border-emerald-400/25 bg-emerald-400/5',
  Intermediate: 'text-amber-400 border-amber-400/25 bg-amber-400/5',
  Expert:       'text-purple-400 border-purple-400/25 bg-purple-400/5',
}