'use client'

import { useState, useRef, useEffect } from 'react'

import GateStep1 from '../components/gates/GateStep1'
import GateStep2 from '../components/gates/GateStep2'
import GateStep3 from '../components/gates/GateStep3'
import GateStep4 from '../components/gates/GateStep4'
import GateSummary from '../components/gates/GateSummary'
import ThinkingCard from '../components/cards/ThinkingCard'
import IdeasCard from '../components/cards/IdeasCard'
import AlternativesCard from '../components/cards/AlternativesCard'
import ComparisonCard from '../components/cards/ComparisonCard'
import DeepAnalysisCard from '../components/cards/DeepAnalysisCard'
import BuildApprovedCard from '../components/cards/BuildApprovedCard'
import ConfirmationGateCard from '../components/cards/ConfirmationGateCard'
import DiscussionCard from '../components/cards/DiscussionCard'
import DiagramsCard from '../components/cards/DiagramsCard'
import GraphCard from '../components/cards/GraphCard'
import NewSessionCard from '../components/cards/NewSessionCard'
import DownloadCard from '../components/cards/DownloadCard'
import ProCouncilCard from '../components/cards/ProCouncilCard'
import QuizCard from '../components/cards/QuizCard'
import Sidebar from '../components/sidebar/Sidebar'
import UserMenu from '../components/sidebar/UserMenu'
import PreviewPanel from '../components/panels/PreviewPanel'

import {
  buildEnrichedIdea,
  runResearch,
  runCouncil,
  runDeepAnalysis,
  runReframe,
  runIdeas,
  runDiscussion,
  runDiagrams,
  runProjectGraph,
  runProCouncil,
  startWorkflow,
  executeWorkflowStage,
  approveWorkflowStage,
  rejectWorkflowStage,
  sendChatMessage,
  getProjectBriefing,
} from '../lib/api'
import { PURPOSE_OPTIONS } from '../lib/constants'
import {
  createProject,
  createSession,
  saveSessionMessage,
  SKIP_SAVE_TYPES,
  MAX_SESSION_MESSAGES,
} from '../lib/projects'
import type {
  Message,
  MessageContent,
  IntakeData,
  GateData,
  ProjectIdea,
  Verdict,
  DeepAnalysisResult,
  SelectedProject,
  DiscussionTurn,
  Diagram,
  GraphSummary,
} from '../lib/types'

// ─────────────────────────────────────────────
// PIPELINE PROGRESS
// ─────────────────────────────────────────────

const PIPELINE_STAGES = [
  { id: 'research',      label: 'Research'      },
  { id: 'analysis',      label: 'Analysis'      },
  { id: 'deep_analysis', label: 'Deep Analysis' },
  { id: 'architecture',  label: 'Architecture'  },
  { id: 'build',         label: 'Build'         },
]

function PipelineProgress({ activeStage }: { activeStage: string | null }) {
  if (!activeStage) return null
  const activeIdx = PIPELINE_STAGES.findIndex(s => s.id === activeStage)
  return (
    <div className="flex items-center gap-0.5">
      {PIPELINE_STAGES.map((stage, i) => {
        const isDone   = i < activeIdx
        const isActive = i === activeIdx
        return (
          <div key={stage.id} className="flex items-center">
            <span className={`text-xs font-mono px-1.5 py-0.5 rounded transition-colors ${
              isActive ? 'text-amber-400 bg-amber-400/10'
              : isDone  ? 'text-emerald-500/50'
              : 'text-[#2a2a2a]'
            }`}>
              {isDone ? '✓ ' : isActive ? '● ' : ''}{stage.label}
            </span>
            {i < PIPELINE_STAGES.length - 1 && (
              <span className={`text-xs mx-0.5 ${isDone ? 'text-emerald-500/30' : 'text-[#1e1e1e]'}`}>
                →
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ─────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────

export default function Home() {
  const [messages,              setMessages]              = useState<Message[]>([])
  const [input,                 setInput]                 = useState('')
  const [isRunning,             setIsRunning]             = useState(false)
  const [intakeData,            setIntakeData]            = useState<IntakeData | null>(null)
  const [selectionMade,         setSelectionMade]         = useState(false)
  const [editingId,             setEditingId]             = useState<string | null>(null)
  const [editText,              setEditText]              = useState('')
  const [gateStep,              setGateStep]              = useState(1)
  const [gateData,              setGateData]              = useState<GateData>({
    project_type: '', role: '', idea: '', purpose: '',
  })
  const [activeStage,           setActiveStage]           = useState<string | null>(null)
  const [activeProjectId,       setActiveProjectId]       = useState<string | null>(null)
  const [activeResearchSummary, setActiveResearchSummary] = useState('')
  const [activeVerdictSummary,  setActiveVerdictSummary]  = useState('')
  const [pendingProject,        setPendingProject]        = useState<SelectedProject | null>(null)
  const [confirmGateMsgId,      setConfirmGateMsgId]      = useState<string | null>(null)
  const [discussionMsgId,       setDiscussionMsgId]       = useState<string | null>(null)
  const [isDiscussing,          setIsDiscussing]          = useState(false)
  const [sidebarOpen,           setSidebarOpen]           = useState(true)
  const [dbProjectId,           setDbProjectId]           = useState<string | null>(null)
  const [isLoadingProject,      setIsLoadingProject]      = useState(false)
  const [isInitializing,        setIsInitializing]        = useState(true)
  const [activeSessionId,       setActiveSessionId]       = useState<string | null>(null)
  const [showNewSession,        setShowNewSession]        = useState(false)
  const [sidebarRefresh,        setSidebarRefresh]        = useState(0)
  const [viewingSession,        setViewingSession]        = useState<string | null>(null)
  const [sessionHistory,        setSessionHistory]        = useState<Message[]>([])
  const [isLoadingHistory,      setIsLoadingHistory]      = useState(false)
  const [cameFromGate,          setCameFromGate]          = useState(false)
  const [userType, setUserType] = useState<'student' | 'professional'>('student')
  const [previewContent, setPreviewContent] = useState<any>(null)
  const [proCouncilResult,        setProCouncilResult]        = useState<any>(null)
const [workflowStage,           setWorkflowStage]           = useState<string | null>(null)
const [workflowOutput,          setWorkflowOutput]          = useState<any>(null)
const [workflowApprovedDecisions, setWorkflowApprovedDecisions] = useState<Record<string, any>>({})
const [workflowProjectId,       setWorkflowProjectId]       = useState<string | null>(null)
const [quizGraph,               setQuizGraph]               = useState<any>(null)
const [quizDiagrams,            setQuizDiagrams]             = useState<any[]>([])
const [showQuiz,                setShowQuiz]                 = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // ── Auth + project init ───────────────────────

  useEffect(() => {
    let mounted = true

    const init = async () => {
      try {
        const { getSession } = await import('../lib/auth')
        const session = await getSession()

        if (!mounted) return

        if (!session) {
          window.location.href = '/auth'
          return
        }

        const params    = new URLSearchParams(window.location.search)
        const projectId = params.get('project')

        if (projectId) {
          setDbProjectId(projectId)
          setIsLoadingProject(true)
          try {
            const { getProject } = await import('../lib/projects')
            const project = await getProject(projectId)
            if (project && mounted) {
              setGateData({
                project_type: 'existing',
                role:         project.target_role || '',
                idea:         project.full_idea || '',
                purpose:      project.purpose || 'portfolio',
              })
              setIntakeData({
                purpose:         project.purpose || 'portfolio',
                role:            project.target_role || '',
                originalMessage: project.full_idea || '',
              })
              setGateStep(5)
              addMsg({ type: 'chosen', choice: `→ Resumed: ${project.title}` })
            }
          } catch (_e) {
            // ignore
          } finally {
            if (mounted) setIsLoadingProject(false)
          }
        }
      } catch (_e) {
        if (mounted) window.location.href = '/auth'
      } finally {
        if (mounted) setIsInitializing(false)
      }
    }

    init()
    return () => { mounted = false }
  }, [])

  // ── Scroll ────────────────────────────────────

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Helpers ───────────────────────────────────

  const addMsg = (content: MessageContent): string => {
    const id = Math.random().toString(36).slice(2)
    setMessages(prev => [...prev, { id, content }])
    if (dbProjectId && activeSessionId && !SKIP_SAVE_TYPES.includes(content.type)) {
      saveSessionMessage(
        dbProjectId,
        activeSessionId,
        content.type === 'user' ? 'user' : 'agent',
        content.type,
        content,
      )
    }
    return id
  }

  const updateMsg = (id: string, content: MessageContent) => {
    setMessages(prev => prev.map(m => m.id === id ? { ...m, content } : m))
  }

  // ── Phase 2 ───────────────────────────────────

  const runPhase2 = async (mcpId: string, dbId: string, chosenIdea: string) => {
    setIsRunning(true)
    setActiveStage('architecture')
    try {
      const t3 = addMsg({
        type: 'thinking', stage: 'Architecture',
        message: 'Generating system architecture, database schema, API contracts, auth flow, deployment plan...',
      })
      const r3 = await runDiagrams(mcpId, dbId, chosenIdea)
      updateMsg(t3, { type: 'diagrams', diagrams: r3.result.diagrams })

      setActiveStage('build')
      const t4 = addMsg({
        type: 'thinking', stage: 'Project Graph',
        message: 'Pre-wiring all pages, components, and API routes...',
      })
      const r4 = await runProjectGraph(mcpId, dbId, chosenIdea)
      updateMsg(t4, {
        type:    'graph',
        summary: r4.result.summary,
        elapsed: r4.result.elapsed_seconds,
        graph:   r4.result.graph,
      })

      // Store for quiz
      setQuizGraph(r4.result.graph || {})
      setQuizDiagrams(r3.result.diagrams || [])
      setShowQuiz(true)

      addMsg({ type: 'complete', projectId: dbId })
      addMsg({
        type:         'quiz',
        projectId:    dbId,
        idea:         chosenIdea,
        role:         intakeData?.role || gateData.role || 'Engineer',
        projectGraph: r4.result.graph || {},
        diagrams:     r3.result.diagrams || [],
      })
      setShowNewSession(true)
      setSidebarRefresh(prev => prev + 1)
    } catch (err) {
      addMsg({ type: 'error', message: err instanceof Error ? err.message : 'Phase 2 failed' })
    } finally {
      setIsRunning(false)
      setActiveStage(null)
    }
  }

  // ── Flow 1 ────────────────────────────────────

  const runFlow1 = async (context: string, intake: IntakeData) => {
    const thinkId = addMsg({
      type: 'thinking', stage: 'Researching',
      message: 'Searching market data, job postings, and tech trends for your role...',
    })
    setIsRunning(true)
    setActiveStage('research')
    try {
      const r1 = await runResearch(context || intake.role, intake)
      const projectId: string = r1.project_id
      const researchSummary   = JSON.stringify(r1.report?.summary || {})

      setActiveStage('analysis')
      updateMsg(thinkId, {
        type: 'thinking', stage: 'Expert Analysis',
        message: '5 adversarial agents running blind parallel analysis — no agent sees another\'s output...',
      })
      const r2               = await runCouncil(projectId, context || intake.role, intake)
      const verdict: Verdict = r2.result.verdict
      const verdictSummary   = verdict.verdict_reasoning?.slice(0, 300) || ''

      setActiveProjectId(projectId)
      setActiveResearchSummary(researchSummary)
      setActiveVerdictSummary(verdictSummary)

      setActiveStage('deep_analysis')
      updateMsg(thinkId, {
        type: 'thinking', stage: 'Deep Analysis',
        message: 'Running council-level analysis across Beginner, Intermediate, and Expert levels...',
      })

      const r3 = await runIdeas(context || intake.role, intake, researchSummary, verdictSummary)

      updateMsg(thinkId, { type: 'ideas', ideas: r3.ideas, purpose: intake.purpose, role: intake.role })

    } catch (err) {
      updateMsg(thinkId, { type: 'error', message: err instanceof Error ? err.message : 'Could not generate ideas.' })
    } finally {
      setIsRunning(false)
      setActiveStage(null)
    }
  }

  // ── Chat Agent ────────────────────────────────

  const runChatAgent = async (text: string) => {
    const thinkId = addMsg({
      type: 'thinking', stage: 'Agent',
      message: 'Reading project context and preparing response...',
    })
    setIsRunning(true)
    try {
      const history = messages
        .filter(m => m.content.type === 'user' || m.content.type === 'agent_response')
        .slice(-10)
        .map(m => ({
          role:    m.content.type === 'user' ? 'user' : 'agent',
          content: (m.content as any).text || '',
        }))
      const r = await sendChatMessage(
        activeProjectId || '',
        text,
        history,
        intakeData || { purpose: userType === 'professional' ? 'professional' : 'portfolio', role: gateData.role, originalMessage: text },
        userType,
        activeStage || '',
      )
      updateMsg(thinkId, { type: 'agent_response', text: r.response, sources: r.sources || [] })
    } catch (err) {
      updateMsg(thinkId, {
        type: 'error',
        message: err instanceof Error ? err.message : 'Agent failed to respond.',
      })
    } finally {
      setIsRunning(false)
    }
  }

  // ── Pro Flow ──────────────────────────────────

  const runProFlow = async (task: string, context: string = '') => {
    const thinkId = addMsg({
      type: 'thinking', stage: 'Professional Council',
      message: 'Senior Architect, Security Engineer, DevOps Engineer, Backend Engineer, and Tech Lead analyzing your task...',
    })
    setIsRunning(true)
    setActiveStage('analysis')

    try {
      const projectId = `pro-${Date.now()}`
      const role      = gateData.role || 'Software Engineer'

      const r1 = await runProCouncil(projectId, context ? `${task}\n\nBLOCKER RESOLUTIONS:\n${context}` : task, role)
      const verdict = r1.result?.verdict || {}
      const agentOutputs = r1.result?.agent_outputs || []

      setProCouncilResult({ verdict, agentOutputs, task, projectId })

      updateMsg(thinkId, {
        type:         'pro_council',
        verdict,
        agentOutputs,
        task,
        projectId,
        role,
        resolvedContext: context || undefined,
      })

    } catch (err) {
      updateMsg(thinkId, {
        type: 'error',
        message: err instanceof Error ? err.message : 'Professional council failed.',
      })
    } finally {
      setIsRunning(false)
      setActiveStage(null)
    }
  }

  // ── Flow 2 ────────────────────────────────────

  const runFlow2 = async (idea: string, intake: IntakeData) => {
    const enrichedIdea = buildEnrichedIdea(idea, intake)
    const thinkId = addMsg({
      type: 'thinking', stage: 'Research',
      message: 'Scanning GitHub, HackerNews, arXiv, and StackOverflow...',
    })
    setIsRunning(true)
    setActiveStage('research')

    try {
      const r1              = await runResearch(enrichedIdea, intake)
      const projectId       = r1.project_id
      const researchSummary = JSON.stringify(r1.report?.summary || {})

      setActiveProjectId(projectId)
      setActiveResearchSummary(researchSummary)

      setActiveStage('analysis')
      updateMsg(thinkId, {
        type: 'thinking', stage: 'Expert Analysis',
        message: '5 adversarial agents debating independently — Systems Architect, Skeptical Interviewer, Career Strategist, Risk Engineer, Innovation Scout...',
      })

      const r2               = await runCouncil(projectId, enrichedIdea, intake)
      const verdict: Verdict = r2.result.verdict
      const advisorOutputs   = r2.result.advisor_outputs || []
      const verdictSummary   = verdict.verdict_reasoning?.slice(0, 300) || ''
      setActiveVerdictSummary(verdictSummary)

      setActiveStage('deep_analysis')
      updateMsg(thinkId, {
        type: 'thinking', stage: 'Deep Analysis',
        message: 'Running comprehensive role-specific portfolio analysis...',
      })

      let deepAnalysis: DeepAnalysisResult | null = null
      try {
        const r3 = await runDeepAnalysis(enrichedIdea, intake, verdict, advisorOutputs, researchSummary)
        deepAnalysis = r3.result as DeepAnalysisResult
      } catch (daErr) {
        console.warn('Deep analysis failed:', daErr)
      }

      let reframeData: any = null
      if (!deepAnalysis) {
        try { reframeData = await runReframe(enrichedIdea, verdict, intake) }
        catch (rfErr) { console.warn('Reframe failed:', rfErr) }
      }

      const hasPivot = verdict.pivot_suggestion &&
        verdict.pivot_suggestion.trim().length > 14 &&
        !['null', 'none', 'n/a'].includes(verdict.pivot_suggestion.trim().toLowerCase())

      if (!hasPivot) {
        updateMsg(thinkId, {
          type: 'build_approved', projectId, idea: enrichedIdea,
          pros: reframeData?.original_pros || deepAnalysis?.ml_engineering_aspects || [],
          minorCons: (reframeData?.original_cons || []).slice(0, 1),
          verdict, deepAnalysis,
        })
      } else {
        updateMsg(thinkId, {
          type: 'comparison', projectId,
          originalIdea: enrichedIdea,
          pivotIdea: verdict.pivot_suggestion!,
          originalPros: reframeData?.original_pros || [],
          originalCons: reframeData?.original_cons || [],
          suggestedPros: reframeData?.suggested_pros || [],
          suggestedCons: reframeData?.suggested_cons || [],
          skillsDemonstrated: reframeData?.skills_demonstrated || [],
          skillsLacking: reframeData?.skills_lacking || [],
          howSuggestionImproves: reframeData?.how_suggestion_improves || [],
          recommendedStack: verdict.recommended_stack || [],
          summary: reframeData?.summary || '',
          verdict, deepAnalysis,
        })
      }
    } catch (err) {
      updateMsg(thinkId, { type: 'error', message: err instanceof Error ? err.message : 'Analysis failed.' })
    } finally {
      setIsRunning(false)
      setActiveStage(null)
    }
  }

  

  // ── More options ──────────────────────────────

  const handleMoreOptions = async () => {
    if (!intakeData || isRunning) return
    setIsRunning(true)
    try {
      const t = addMsg({
        type: 'thinking', stage: 'Finding Ideas',
        message: 'Generating more validated project ideas using existing research...',
      })
      const r = await runIdeas(intakeData.role || '', intakeData, activeResearchSummary, activeVerdictSummary)
      updateMsg(t, { type: 'ideas', ideas: r.ideas, purpose: intakeData.purpose, role: intakeData.role })
    } catch {
      addMsg({ type: 'error', message: 'Could not generate more ideas.' })
    } finally {
      setIsRunning(false)
    }
  }

  // ── Confirmation gate ─────────────────────────

  const showConfirmationGate = (selectedProject: SelectedProject) => {
    setPendingProject(selectedProject)
    const id = Math.random().toString(36).slice(2)
    setMessages(prev => [...prev, { id, content: { type: 'confirmation_gate', selectedProject } }])
    setConfirmGateMsgId(id)
  }

  const handleConfirmProceed = async () => {
    if (!pendingProject || !intakeData) return
    const project   = pendingProject
    const projectId = (project.projectId && project.projectId !== '')
      ? project.projectId : (activeProjectId || '')

    setPendingProject(null)
    setConfirmGateMsgId(null)
    setSelectionMade(true)
    addMsg({ type: 'chosen', choice: `→ Building: ${project.title}` })

    const savedProject = await createProject(project, intakeData.role, intakeData.purpose)
    if (savedProject) {
      setDbProjectId(savedProject.id)
      setSidebarRefresh(prev => prev + 1)
      const session = await createSession(savedProject.id, 6, 'planning', 'Planning Session 1')
      if (session) {
        setActiveSessionId(session.id)
        for (const msg of messages) {
          if (!SKIP_SAVE_TYPES.includes(msg.content.type)) {
            await saveSessionMessage(
              savedProject.id, session.id,
              msg.content.type === 'user' ? 'user' : 'agent',
              msg.content.type, msg.content,
            )
          }
        }
      }
    }

    runPhase2(activeProjectId || projectId, savedProject?.id || projectId, project.fullIdea)
  }

  const handleStartDiscussion = () => {
    if (!pendingProject || !confirmGateMsgId) return
    updateMsg(confirmGateMsgId, { type: 'discussion', selectedProject: pendingProject, history: [] })
    setDiscussionMsgId(confirmGateMsgId)
    setConfirmGateMsgId(null)
  }

  const handleDiscussionSend = async (userMessage: string, currentHistory: DiscussionTurn[]) => {
    if (!pendingProject || !intakeData || !discussionMsgId || isDiscussing) return
    setIsDiscussing(true)

    const updatedHistory: DiscussionTurn[] = [...currentHistory, { role: 'user', content: userMessage }]
    updateMsg(discussionMsgId, { type: 'discussion', selectedProject: pendingProject, history: updatedHistory })

    try {
      const r = await runDiscussion(pendingProject, userMessage, currentHistory, intakeData)
      const finalHistory: DiscussionTurn[] = [...updatedHistory, { role: 'mentor', content: r.response }]
      updateMsg(discussionMsgId, { type: 'discussion', selectedProject: pendingProject, history: finalHistory })
    } catch {
      const errorHistory: DiscussionTurn[] = [
        ...updatedHistory,
        { role: 'mentor', content: 'I had a technical issue. Are you ready to move to diagrams, or do you have more questions?' },
      ]
      updateMsg(discussionMsgId, { type: 'discussion', selectedProject: pendingProject, history: errorHistory })
    } finally {
      setIsDiscussing(false)
    }
  }

  const handleDiscussionProceed = async () => {
  if (!pendingProject || !intakeData) return
  const project = pendingProject
  const mcpId = (project.projectId && project.projectId !== '')
    ? project.projectId : (activeProjectId || '')

  setPendingProject(null)
  setDiscussionMsgId(null)
  setSelectionMade(true)
  addMsg({ type: 'chosen', choice: `→ Building: ${project.title}` })

  const savedProject = await createProject(project, intakeData.role, intakeData.purpose)
  if (savedProject) {
    setDbProjectId(savedProject.id)
    setSidebarRefresh(prev => prev + 1)
    const session = await createSession(savedProject.id, 6, 'planning', 'Planning Session 1')
    if (session) setActiveSessionId(session.id)
    runPhase2(mcpId, savedProject.id, project.fullIdea)
  } else {
    runPhase2(mcpId, mcpId, project.fullIdea)
  }
}

  // ── New session ───────────────────────────────

  const handleStartNewSession = async () => {
    if (!dbProjectId) return
    setShowNewSession(false)
    const session = await createSession(dbProjectId, 6, 'planning')
    if (session) setActiveSessionId(session.id)
    setMessages([])
    setSelectionMade(false)
    setPendingProject(null)
    setConfirmGateMsgId(null)
    setDiscussionMsgId(null)
    setIsDiscussing(false)
    setSidebarRefresh(prev => prev + 1)
    addMsg({ type: 'chosen', choice: '→ New session started — project memory preserved' })
  }

  // ── Gate ──────────────────────────────────────

  const handleGateAnswer = async (step: number, value: string) => {
    if (step === 1) {
      if (value === 'professional') {
        setUserType('professional')
        setGateData(prev => ({ ...prev, project_type: 'professional' }))
        setGateStep(5)
        setIntakeData({ purpose: 'professional', role: '', originalMessage: '' })
        addMsg({ type: 'chosen', choice: '→ Professional mode — describe your task and agents will respond' })
        return
      }
      setUserType('student')
      setGateData(prev => ({ ...prev, project_type: value }))
      setGateStep(2)
      return
    }
    if (step === 2) { setGateData(prev => ({ ...prev, role: value }));    setGateStep(3); return }
    if (step === 3) {
      setGateData(prev => ({ ...prev, idea: value }))
      setGateStep(4)
      return
    }
    if (step === 4) {
      const finalData = { ...gateData, purpose: value }
      setGateData(finalData)
      setGateStep(5)
      const intake: IntakeData = { purpose: finalData.purpose, role: finalData.role, originalMessage: finalData.idea }
      setIntakeData(intake)
      const purposeLabel = PURPOSE_OPTIONS.find(p => p.id === finalData.purpose)?.label || finalData.purpose
      addMsg({ type: 'chosen', choice: `→ ${finalData.role || 'Engineer'} · ${purposeLabel} · ${finalData.idea ? 'analyzing your idea' : 'finding best projects'}` })
      if (finalData.idea.trim()) await runFlow2(finalData.idea, intake)
      else await runFlow1('', intake)
    }
  }

  const handleGateBack   = (step: number) => setGateStep(step - 1)

  const handleGateUpdate = async (updated: GateData) => {
    setGateData(updated)
    const intake: IntakeData = { purpose: updated.purpose, role: updated.role, originalMessage: updated.idea }
    setIntakeData(intake)
    setMessages([])
    setSelectionMade(false)
    setActiveProjectId(null)
    setActiveResearchSummary('')
    setActiveVerdictSummary('')
    setPendingProject(null)
    setConfirmGateMsgId(null)
    setDiscussionMsgId(null)
    setIsDiscussing(false)
    const purposeLabel = PURPOSE_OPTIONS.find(p => p.id === updated.purpose)?.label || updated.purpose
    addMsg({ type: 'chosen', choice: `→ Updated: ${updated.role || 'Engineer'} · ${purposeLabel}` })
    if (updated.idea.trim()) await runFlow2(updated.idea, intake)
    else await runFlow1('', intake)
  }

  // ── Send ──────────────────────────────────────

  const handleSend = async () => {
    if (!input.trim() || isRunning || gateStep < 5) return
    const text = input.trim()
    setInput('')
    addMsg({ type: 'user', text })

    if (userType === 'professional' && !activeProjectId) {
      await runProFlow(text)
      return
    }

    if (userType === 'professional' && activeProjectId) {
      await runChatAgent(text)
      return
    }

    if (activeProjectId) {
      await runChatAgent(text)
      return
    }

    if (intakeData) {
      setActiveProjectId(null)
      setActiveResearchSummary('')
      setActiveVerdictSummary('')
      setPendingProject(null)
      setConfirmGateMsgId(null)
      setDiscussionMsgId(null)
      setIsDiscussing(false)
      await runFlow2(text, intakeData)
    }
  }

  // ── Sign out ──────────────────────────────────

  const handleSignOut = async () => {
    const { signOut } = await import('../lib/auth')
    await signOut()
    window.location.href = '/auth'
  }

  // ── Idea selection ────────────────────────────

  const handleIdeaSelect = (idea: ProjectIdea) => {
    if (!intakeData || isRunning) return
    const selectedProject: SelectedProject = {
      title: idea.title, description: idea.one_liner,
      techStack: idea.tech_stack || [], level: idea.level,
      buildTime: idea.build_time, skillsDemonstrated: idea.skills_demonstrated || [],
      risks: [], portfolioValue: idea.why_good || '',
      fullIdea: `${idea.title} — ${idea.one_liner}`,
      projectId: activeProjectId || '',
    }
    addMsg({ type: 'user', text: `Selected: ${idea.title}` })
    showConfirmationGate(selectedProject)
  }

  // ── Build handlers ────────────────────────────

  const handleBuildOriginal = (projectId: string, originalIdea: string, verdict?: Verdict) => {
    showConfirmationGate({
      title: originalIdea.slice(0, 60).trim(), description: originalIdea,
      techStack: verdict?.recommended_stack || [], level: 'Intermediate',
      buildTime: verdict?.estimated_build_time || '6 weeks', skillsDemonstrated: [],
      risks: verdict?.top_risks || [], portfolioValue: verdict?.career_value || '',
      fullIdea: originalIdea, projectId,
    })
  }

  const handleBuildSuggested = (projectId: string, pivotIdea: string, verdict?: Verdict) => {
    showConfirmationGate({
      title: pivotIdea.slice(0, 60).trim(), description: pivotIdea,
      techStack: verdict?.recommended_stack || [], level: 'Intermediate',
      buildTime: verdict?.estimated_build_time || '6 weeks', skillsDemonstrated: [],
      risks: [], portfolioValue: verdict?.career_value || '',
      fullIdea: pivotIdea, projectId,
    })
  }

  const handleBuildImproved = (projectId: string, deepAnalysis: DeepAnalysisResult) => {
    const bp = deepAnalysis.improved_blueprint
    showConfirmationGate({
      title: bp?.title || 'Improved Version', description: bp?.description || '',
      techStack: bp?.recommended_stack || [], level: 'Intermediate',
      buildTime: `${bp?.estimated_weeks || 6} weeks`, skillsDemonstrated: [],
      risks: [], portfolioValue: bp?.resume_bullet || '',
      fullIdea: `${bp?.title} — ${bp?.description}`, projectId,
    })
  }

  const handleBuildApproved = (projectId: string, idea: string, verdict?: Verdict) => {
    showConfirmationGate({
      title: idea.slice(0, 60).trim(), description: idea,
      techStack: verdict?.recommended_stack || [], level: 'Intermediate',
      buildTime: verdict?.estimated_build_time || '6 weeks', skillsDemonstrated: [],
      risks: verdict?.top_risks || [], portfolioValue: verdict?.career_value || '',
      fullIdea: idea, projectId,
    })
  }

  // ── Reset ─────────────────────────────────────

  const handleRethink = () => {
    setMessages([])
    setInput('')
    setIsRunning(false)
    setIntakeData(null)
    setSelectionMade(false)
    setEditingId(null)
    setEditText('')
    setGateStep(1)
    setGateData({ project_type: '', role: '', idea: '', purpose: '' })
    setActiveProjectId(null)
    setActiveResearchSummary('')
    setActiveVerdictSummary('')
    setActiveStage(null)
    setPendingProject(null)
    setConfirmGateMsgId(null)
    setDiscussionMsgId(null)
    setIsDiscussing(false)
    setDbProjectId(null)
    setUserType('student')
    setActiveSessionId(null)
    setShowNewSession(false)
    setViewingSession(null)
    setSessionHistory([])
    setPreviewContent(null)
    window.history.pushState({}, '', '/')
  }

  // ── Edit ──────────────────────────────────────

  const handleEditStart = (msgId: string, text: string) => {
    setEditingId(msgId)
    setEditText(text)
  }

  const handleEditSubmit = async (msgId: string) => {
    if (!editText.trim() || isRunning) return
    const newText = editText.trim()
    setEditingId(null)
    setEditText('')
    setSelectionMade(false)
    setActiveProjectId(null)
    setActiveResearchSummary('')
    setActiveVerdictSummary('')
    setPendingProject(null)
    setConfirmGateMsgId(null)
    setDiscussionMsgId(null)
    setIsDiscussing(false)
    const msgIndex = messages.findIndex(m => m.id === msgId)
    if (msgIndex === -1) return
    const newId = Math.random().toString(36).slice(2)
    setMessages(prev => [...prev.slice(0, msgIndex), { id: newId, content: { type: 'user', text: newText } }])
    if (intakeData) await runFlow2(newText, intakeData)
  }

  // ── Sidebar props ─────────────────────────────

  const sidebarProps = {
    activeProjectId:  dbProjectId,
    activeSessionId,
    refreshTrigger:   sidebarRefresh,
    onProjectSelect:  (_project: any) => {},
    onSessionSelect:  async (project: any, sessionId: string) => {
      setCameFromGate(gateStep < 5)
      setGateStep(5)
      setDbProjectId(project.id)
      setGateData({
        project_type: 'existing',
        role:         project.target_role || '',
        idea:         project.full_idea || '',
        purpose:      project.purpose || 'portfolio',
      })
      setMessages([])
      setViewingSession(sessionId)
      setIsLoadingHistory(true)
      try {
        const { getSessionMessages } = await import('../lib/projects')
        const msgs = await getSessionMessages(project.id, sessionId)
        const converted: Message[] = msgs.map((m: any) => ({
          id:      m.id,
          content: m.content as MessageContent,
        }))
        setSessionHistory(converted)
      } catch {
        setSessionHistory([])
      } finally {
        setIsLoadingHistory(false)
      }

      // Auto-generate briefing for returning user
      try {
        const briefing = await getProjectBriefing(
          project.id,
          project.target_role || '',
          project.purpose || 'portfolio',
          userType,
        )
        if (briefing.success) {
          setMessages([{
            id: Math.random().toString(36).slice(2),
            content: {
              type:    'briefing',
              text:    briefing.briefing,
              sources: briefing.sources || [],
            }
          }])
        }
      } catch {
        // briefing failed silently — user still sees empty chat
      }
    },
    onNewProject:     handleRethink,
    onSignOut:        handleSignOut,
    role:             gateData.role,
    purpose:          gateData.purpose,
    isCollapsed:      !sidebarOpen,
    onToggle:         () => setSidebarOpen(!sidebarOpen),
  }

  // ── Render message ────────────────────────────

  const renderMessage = (msg: Message) => {
    const { content } = msg

    if (content.type === 'user') {
      if (editingId === msg.id) {
        return (
          <div className="flex justify-end">
            <div className="bg-[#1c2333] border border-[#f0b429]/20 rounded-2xl rounded-tr-sm p-3 max-w-sm w-full">
              <textarea value={editText} onChange={e => setEditText(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleEditSubmit(msg.id) }
                  if (e.key === 'Escape') { setEditingId(null); setEditText('') }
                }}
                autoFocus rows={3}
                className="w-full bg-transparent text-[#e6edf3] text-sm outline-none resize-none leading-relaxed"
              />
              <div className="flex justify-end gap-3 mt-2 pt-2 border-t border-[#f0b429]/10">
                <button onClick={() => { setEditingId(null); setEditText('') }}
                  className="text-xs text-[#484f58] hover:text-[#e6edf3] transition-colors">cancel</button>
                <button onClick={() => handleEditSubmit(msg.id)}
                  className="text-xs text-[#f0b429] hover:text-white transition-colors font-medium">replay →</button>
              </div>
            </div>
          </div>
        )
      }
      return (
        <div className="flex justify-end group">
          <div className="relative">
            <div className="bg-[#1c2333] border border-[#30363d] rounded-2xl rounded-tr-sm px-4 py-3 max-w-sm">
              <p className="text-sm text-[#e6edf3] leading-relaxed">{content.text}</p>
            </div>
            <button onClick={() => handleEditStart(msg.id, content.text)} title="Edit and replay"
              className="absolute -left-8 top-2 opacity-0 group-hover:opacity-100 transition-all text-[#484f58] hover:text-[#f0b429] text-xs w-6 h-6 flex items-center justify-center rounded-md bg-[#161b22] border border-[#30363d]">
              ✏
            </button>
          </div>
        </div>
      )
    }

    if (content.type === 'thinking') return <ThinkingCard stage={content.stage} message={content.message} />

    if (content.type === 'ideas') return (
      <IdeasCard ideas={content.ideas} purpose={content.purpose} role={content.role}
        onSelect={handleIdeaSelect} onMoreAlternatives={handleMoreOptions} />
    )

    if (content.type === 'alternatives') return (
      <AlternativesCard ideas={content.ideas} purpose={content.purpose} role={content.role}
        originalIdea={content.originalIdea} onSelect={handleIdeaSelect} onMoreAlternatives={handleMoreOptions} />
    )

    if (content.type === 'comparison') {
      const isGateShowing = !!pendingProject
      if (content.deepAnalysis) {
        return (
          <DeepAnalysisCard analysis={content.deepAnalysis} originalIdea={content.originalIdea}
            pivotIdea={content.pivotIdea} projectId={content.projectId}
            onBuildOriginal={() => handleBuildOriginal(content.projectId, content.originalIdea, content.verdict)}
            onBuildImproved={() => handleBuildImproved(content.projectId, content.deepAnalysis!)}
            onMoreAlternatives={handleMoreOptions}
            disabled={selectionMade || isRunning || isGateShowing} />
        )
      }
      return (
        <ComparisonCard projectId={content.projectId} originalIdea={content.originalIdea}
          pivotIdea={content.pivotIdea} originalPros={content.originalPros}
          originalCons={content.originalCons} suggestedPros={content.suggestedPros}
          suggestedCons={content.suggestedCons}
          skillsDemonstrated={content.skillsDemonstrated || []}
          skillsLacking={content.skillsLacking || []}
          howSuggestionImproves={content.howSuggestionImproves || []}
          recommendedStack={content.recommendedStack || []}
          summary={content.summary}
          onBuildOriginal={() => handleBuildOriginal(content.projectId, content.originalIdea, content.verdict)}
          onBuildSuggested={() => handleBuildSuggested(content.projectId, content.pivotIdea, content.verdict)}
          onMoreAlternatives={handleMoreOptions}
          disabled={selectionMade || isRunning || isGateShowing} />
      )
    }

    if (content.type === 'build_approved') {
      const isGateShowing = !!pendingProject
      if (content.deepAnalysis) {
        return (
          <DeepAnalysisCard analysis={content.deepAnalysis} originalIdea={content.idea} pivotIdea=""
            projectId={content.projectId}
            onBuildOriginal={() => handleBuildApproved(content.projectId, content.idea, content.verdict)}
            onBuildImproved={() => handleBuildImproved(content.projectId, content.deepAnalysis!)}
            onMoreAlternatives={handleMoreOptions}
            disabled={selectionMade || isRunning || isGateShowing} />
        )
      }
      return (
        <BuildApprovedCard projectId={content.projectId} idea={content.idea}
          pros={content.pros} minorCons={content.minorCons}
          onBuild={() => handleBuildApproved(content.projectId, content.idea, content.verdict)}
          onMoreAlternatives={handleMoreOptions}
          disabled={selectionMade || isRunning || isGateShowing} />
      )
    }

    if (content.type === 'confirmation_gate') return (
      <ConfirmationGateCard selectedProject={content.selectedProject}
        onProceed={handleConfirmProceed} onDiscuss={handleStartDiscussion} disabled={isRunning} />
    )

    if (content.type === 'discussion') return (
      <DiscussionCard selectedProject={content.selectedProject} history={content.history}
        onSend={handleDiscussionSend} onProceed={handleDiscussionProceed}
        isLoading={isDiscussing} disabled={selectionMade} />
    )

    if (content.type === 'chosen') return (
      <div className="flex items-center gap-2 py-0.5 pl-1">
        <div className="w-px h-3 bg-[#30363d]" />
        <span className="text-xs text-[#484f58] font-mono">{content.choice}</span>
      </div>
    )

    if (content.type === 'diagrams') return (
      <DiagramsCard
        diagrams={content.diagrams}
        onOpenPreview={(diagrams, activeIndex) => setPreviewContent({
          type: 'diagrams',
          diagrams,
          activeIndex,
        })}
      />
    )

   if (content.type === 'graph') return (
      <GraphCard
        summary={content.summary}
        elapsed={content.elapsed}
        onOpenPreview={(graph) => setPreviewContent({
          type:    'graph',
          summary: graph,
          graph:   content.graph,
        })}
      />
    )
    if (content.type === 'quiz') return (
      <QuizCard
        projectId={content.projectId}
        idea={content.idea}
        role={content.role}
        projectGraph={content.projectGraph}
        diagrams={content.diagrams}
        onSkip={() => {
          setShowQuiz(false)
          addMsg({ type: 'chosen', choice: '→ Quiz skipped — moving to next stage' })
        }}
        onComplete={(gaps) => {
          setShowQuiz(false)
          addMsg({ type: 'chosen', choice: `→ Quiz complete — ${gaps.length} knowledge gaps saved` })
        }}
      />
    )
    if (content.type === 'complete') return (
      <div className="space-y-3">
        <div className="flex items-center gap-3 bg-[#1a2e1a] border border-[#2ea04326] rounded-xl px-4 py-3">
          <div className="w-1.5 h-1.5 rounded-full bg-[#3fb950] flex-shrink-0" />
          <div>
            <div className="text-xs font-mono text-[#3fb950] mb-0.5">Pipeline Complete</div>
            <p className="text-xs text-[#484f58] font-mono">id: {content.projectId}</p>
          </div>
        </div>
        {showNewSession && (
          <NewSessionCard
            reason="pipeline_complete"
            projectTitle={gateData.idea || 'Your Project'}
            messageCount={messages.length}
            onStartNewSession={handleStartNewSession}
            onContinue={() => setShowNewSession(false)}
          />
        )}
      </div>
    )

    if (content.type === 'download') return (
      <DownloadCard
        filename={content.filename}
        content={content.content}
        mimeType={content.mimeType}
        label={content.label}
      />
    )

    if (content.type === 'pro_council') return (
      <ProCouncilCard
        verdict={content.verdict}
        agentOutputs={content.agentOutputs}
        task={content.task}
        projectId={content.projectId}
        role={content.role}
        resolvedContext={content.resolvedContext}
        onStartBuilding={() => {
          addMsg({ type: 'chosen', choice: '→ Starting build pipeline — Planning Agent activating...' })
        }}
        onResolveBlockers={(resolutions) => {
          addMsg({ type: 'user', text: `Blocker resolutions: ${resolutions.slice(0, 80)}...` })
          runProFlow(content.task, resolutions)
        }}
        disabled={isRunning}
      />
    )
    if (content.type === 'briefing') return (
      <div className="bg-[#161b22] border border-[#f0b429]/20 rounded-xl px-4 py-3 w-full">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-5 h-5 rounded-md bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center flex-shrink-0">
            <span className="text-[#f0b429] text-xs font-bold">3</span>
          </div>
          <span className="text-xs font-mono text-amber-400">
            Project Briefing
          </span>
        </div>
        <p className="text-sm text-[#e6edf3] leading-relaxed whitespace-pre-wrap">
          {content.text}
        </p>
        <p className="text-xs text-[#484f58] font-mono mt-2">
          Type any question to continue →
        </p>
      </div>
    )
    if (content.type === 'agent_response') return (
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl px-4 py-3 w-full">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-5 h-5 rounded-md bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center flex-shrink-0">
            <span className="text-[#f0b429] text-xs font-bold">3</span>
          </div>
          <span className="text-xs font-mono text-[#484f58]">
            Agent · {content.sources?.join(', ') || 'project context'}
          </span>
        </div>
        <p className="text-sm text-[#e6edf3] leading-relaxed whitespace-pre-wrap">
          {content.text}
        </p>
      </div>
    )

    if (content.type === 'error') return (
      <div className="flex items-start gap-3 bg-[#2d1b1b] border border-[#f8514926] rounded-xl px-4 py-3">
        <div className="w-1.5 h-1.5 rounded-full bg-[#f85149] flex-shrink-0 mt-1" />
        <div>
          <div className="text-xs font-mono text-[#f85149] mb-1">Error</div>
          <p className="text-sm text-[#8b949e] leading-relaxed">{content.message}</p>
        </div>
      </div>
    )

    return null
  }

  // ── Loading ───────────────────────────────────

  if (isInitializing || isLoadingProject) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0d1117]">
        <div className="text-center">
          <div className="flex gap-1 justify-center mb-3">
            {[0,1,2].map(i => (
              <div key={i} style={{ animationDelay: `${i*0.2}s` }}
                className="w-2 h-2 rounded-full bg-[#f0b429] animate-pulse" />
            ))}
          </div>
          <p className="text-xs text-[#484f58] font-mono">Loading...</p>
        </div>
      </div>
    )
  }

  // ── Gate screen ───────────────────────────────

  if (gateStep < 5) {
    return (
      <div className="flex h-screen bg-[#0d1117] text-[#e6edf3] overflow-hidden">
        <Sidebar {...sidebarProps} />
        <div className="flex flex-col flex-1 min-w-0 h-screen">
          <header className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-[#21262d]">
            <div className="flex items-center gap-2">
              
              <div className="w-7 h-7 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center">
                <span className="text-[#f0b429] text-sm font-bold">3</span>
              </div>
              <button
                onClick={() => window.location.href = '/dashboard'}
                className="text-sm font-semibold text-[#e6edf3] hover:text-[#f0b429] transition-colors"
              >
                3Netra<span className="text-[#f0b429]">-AI</span>
              </button>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                {(userType === 'professional' ? [1] : [1,2,3,4]).map(s => (
                  <div key={s} className={`rounded-full transition-all ${
                    s < gateStep ? 'w-5 h-1.5 bg-[#3fb950]'
                    : s === gateStep ? 'w-5 h-1.5 bg-[#f0b429]'
                    : 'w-1.5 h-1.5 bg-[#30363d]'
                  }`} />
                ))}
              </div>
              <UserMenu onSignOut={handleSignOut} role={gateData.role} purpose={gateData.purpose} />
            </div>
          </header>

          <main className="flex-1 flex flex-col items-center justify-center px-6">
            <div className="text-center mb-10">
              <h1 className="text-3xl font-semibold mb-3 tracking-tight">Your AI engineering team.</h1>
              <p className="text-sm text-[#8b949e] max-w-sm leading-relaxed">
                {gateStep === 1 && "Tell us who you are — this shapes every agent decision."}
                {gateStep === 2 && "Your role shapes every piece of advice our agents give."}
                {gateStep === 3 && "Have an idea? Great. No idea? We'll find the best one for you."}
                {gateStep === 4 && "Purpose determines what success looks like for this project."}
              </p>
            </div>
            {gateStep === 1 && <GateStep1 onAnswer={val => handleGateAnswer(1, val)} />}
            {gateStep === 2 && <GateStep2 onAnswer={val => handleGateAnswer(2, val)} onBack={() => handleGateBack(2)} />}
            {gateStep === 3 && <GateStep3 onAnswer={val => handleGateAnswer(3, val)} onBack={() => handleGateBack(3)} userType={userType} />}
            {gateStep === 4 && <GateStep4 onAnswer={val => handleGateAnswer(4, val)} onBack={() => handleGateBack(4)} />}
          </main>

          <footer className="flex-shrink-0 px-6 py-4 text-center">
            <p className="text-xs text-[#30363d] font-mono">
              Research · Expert Analysis · Deep Analysis · Architecture · Build · Test · Deploy
            </p>
          </footer>
        </div>
      </div>
    )
  }

  // ── Main chat ─────────────────────────────────

  return (
    <div className="flex h-screen bg-[#0d1117] text-[#e6edf3] overflow-hidden">
      <Sidebar {...sidebarProps} />

      <div className="flex flex-col flex-1 min-w-0 h-screen">
        <header className="flex-shrink-0 flex items-center justify-between px-5 py-3.5 border-b border-[#21262d] bg-[#0d1117]/95 backdrop-blur-sm sticky top-0 z-10">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button onClick={() => setSidebarOpen(true)}
                className="text-[#484f58] hover:text-[#e6edf3] transition-colors text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-[#161b22]">
                →
              </button>
            )}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center">
                <span className="text-[#f0b429] text-sm font-bold">3</span>
              </div>
              <button
                onClick={() => window.location.href = '/dashboard'}
                className="text-sm font-semibold text-[#e6edf3] hover:text-[#f0b429] transition-colors"
              >
                3Netra<span className="text-[#f0b429]">-AI</span>
              </button>
            </div>
            <div className="w-px h-4 bg-[#21262d]" />
            <span className="hidden sm:block text-xs text-[#484f58] font-mono">Your AI engineering team</span>
          </div>

          <div className="flex items-center gap-3">
            {isRunning && activeStage && <PipelineProgress activeStage={activeStage} />}
            {dbProjectId && !isRunning && !pendingProject && !viewingSession && (
              <button
                onClick={() => window.location.href = `/project/${dbProjectId}`}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-[#161b22] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3] hover:border-[#484f58] rounded-lg transition-colors font-mono"
              >
                📋 Project
              </button>
            )}
            
            <div className="flex items-center gap-1.5">
              <div className={`w-1.5 h-1.5 rounded-full ${isRunning || isDiscussing ? 'bg-amber-400 animate-pulse' : 'bg-[#3fb950]'}`} />
              <span className="text-xs text-[#484f58] font-mono hidden sm:block">
                {isRunning ? 'running' : isDiscussing ? 'discussing' : 'ready'}
              </span>
            </div>
            <UserMenu onSignOut={handleSignOut} role={gateData.role} purpose={gateData.purpose} />
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="px-5 py-5">

            {/* Session history view */}
            {viewingSession ? (
              <div className="max-w-2xl mx-auto">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <div className="text-xs font-mono text-[#484f58] uppercase tracking-widest mb-1">
                      Session History — Read Only
                    </div>
                    <p className="text-xs text-[#30363d]">{sessionHistory.length} messages</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setViewingSession(null)
                        setSessionHistory([])
                        if (cameFromGate) {
                          setGateStep(1)
                          setMessages([])
                          setCameFromGate(false)
                        }
                      }}
                      className="text-xs px-3 py-1.5 bg-[#161b22] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3] rounded-lg transition-colors font-mono"
                    >
                      ← Back
                    </button>
                    <button
                      onClick={() => {
                        setViewingSession(null)
                        setSessionHistory([])
                        handleStartNewSession()
                      }}
                      className="text-xs px-3 py-1.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] transition-colors"
                    >
                      Resume Project →
                    </button>
                  </div>
                </div>

                {isLoadingHistory ? (
                  <div className="space-y-3">
                    {[1,2,3].map(i => (
                      <div key={i} className="h-16 bg-[#161b22] border border-[#21262d] rounded-xl animate-pulse" />
                    ))}
                  </div>
                ) : sessionHistory.length === 0 ? (
                  <div className="text-center py-12">
                    <p className="text-sm text-[#484f58]">No messages in this session yet.</p>
                  </div>
                ) : (
                  <div className="space-y-3 opacity-80 pointer-events-none">
                    {sessionHistory.map(msg => (
                      <div key={msg.id}>{renderMessage(msg)}</div>
                    ))}
                  </div>
                )}
              </div>

            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
                <div className="w-14 h-14 rounded-2xl bg-[#f0b429]/10 border border-[#f0b429]/20 flex items-center justify-center mb-5">
                  <span className="text-[#f0b429] text-2xl font-bold">3</span>
                </div>
                <h2 className="text-xl font-semibold mb-2 tracking-tight">Ready. What would you like to build?</h2>
                <p className="text-sm text-[#8b949e] max-w-md leading-relaxed mb-5">
                  Type a project idea, or ask anything about architecture, career, or engineering.
                </p>
                <div className="flex items-center gap-2 text-xs font-mono">
                  {gateData.role && (
                    <span className="px-2.5 py-1 bg-[#161b22] border border-[#30363d] text-[#8b949e] rounded-lg">
                      {gateData.role}
                    </span>
                  )}
                  {gateData.purpose && (
                    <span className="px-2.5 py-1 bg-[#161b22] border border-[#30363d] text-[#8b949e] rounded-lg">
                      {PURPOSE_OPTIONS.find(p => p.id === gateData.purpose)?.label}
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <div className="max-w-2xl mx-auto space-y-3">
                {userType !== 'professional' && <GateSummary gateData={gateData} onUpdate={handleGateUpdate} />}
                {messages.map(msg => <div key={msg.id}>{renderMessage(msg)}</div>)}
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </main>

        <footer className="flex-shrink-0 border-t border-[#21262d] bg-[#0d1117] px-5 py-4">
          <div className="max-w-3xl mx-auto">
            <div className="flex gap-2 bg-[#161b22] border border-[#30363d] rounded-xl px-4 py-3 focus-within:border-[#484f58] transition-colors">
              <textarea value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
                placeholder={
                  gateStep < 5 ? 'Complete the setup above first...'
                  : pendingProject ? 'Confirm or discuss your selected project above first...'
                  : viewingSession ? 'Resume project to continue chatting...'
                  : 'Describe a project, ask about architecture, debug code, plan your career...'
                }
                disabled={isRunning || gateStep < 5 || !!pendingProject || isDiscussing || !!viewingSession}
                rows={2}
                className="flex-1 bg-transparent text-sm text-[#e6edf3] placeholder-[#484f58] outline-none resize-none leading-relaxed disabled:opacity-40"
              />
              <div className="flex flex-col justify-end">
                <button onClick={handleSend}
                  disabled={isRunning || !input.trim() || gateStep < 5 || !!pendingProject || isDiscussing || !!viewingSession}
                  className="px-4 py-2 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg hover:bg-[#e0a419] disabled:opacity-30 disabled:cursor-not-allowed transition-all text-sm">
                  {isRunning ? (
                    <span className="flex items-center gap-1">
                      {[0,1,2].map(i => (
                        <span key={i} style={{ animationDelay: `${i*0.15}s` }}
                          className="w-1 h-1 rounded-full bg-[#0d1117] animate-pulse" />
                      ))}
                    </span>
                  ) : '↑'}
                </button>
              </div>
            </div>
            <p className="text-xs text-[#21262d] text-center mt-2 font-mono">
              Research · Analysis · Deep Analysis · Architecture · Build · Test · Deploy · Career
            </p>
          </div>
        </footer>
      </div>

      {/* Preview panel */}
      <PreviewPanel
        content={previewContent}
        onClose={() => setPreviewContent(null)}
      />
    </div>
  )
}