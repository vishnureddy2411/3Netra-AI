'use client'

import { useState } from 'react'
import {
  startQuiz,
  submitQuizAnswer,
  getNextQuizRound,
  summarizeQuizRound,
  completeQuiz,
} from '../../lib/api'

// ── Types ──────────────────────────────────────────────────────────────────

interface Question {
  id:             string
  category:       string
  difficulty:     string
  question:       string
  correct_answer: string
  key_concepts:   string[]
  why_it_matters: string
}

interface Evaluation {
  is_correct:        boolean
  verdict:           string
  score:             number
  short_verdict:     string
  explanation:       string
  what_they_got_right: string | null
  what_was_missing:  string | null
  knowledge_gap:     string | null
  study_tip:         string | null
}

interface RoundSummary {
  score_pct:         number
  correct:           number
  total:             number
  performance_label: string
  summary:           string
  strengths:         string[]
  gaps:              string[]
  recommendation:    string
}

interface Props {
  projectId:    string
  idea:         string
  role:         string
  projectGraph: any
  diagrams:     any[]
  onSkip:       () => void
  onComplete:   (gaps: string[]) => void
}

type Phase =
  | 'intro'
  | 'loading'
  | 'question'
  | 'evaluating'
  | 'evaluated'
  | 'round_complete'
  | 'completing'
  | 'complete'

const CATEGORY_ICONS: Record<string, string> = {
  architecture:       '🏗',
  tech_choice:        '⚙️',
  data_flow:          '🔄',
  core_feature:       '✨',
  stack_justification:'📚',
  scalability:        '📈',
  failure_modes:      '⚠️',
  security:           '🔒',
  database_design:    '🗄',
  api_design:         '🔌',
  interview_sim:      '🎤',
  trade_offs:         '⚖️',
  improvements:       '🚀',
  production:         '🚢',
  stakeholder_explain:'👔',
}

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner:     'text-emerald-400 border-emerald-400/20 bg-emerald-400/5',
  intermediate: 'text-amber-400 border-amber-400/20 bg-amber-400/5',
  advanced:     'text-purple-400 border-purple-400/20 bg-purple-400/5',
}

// ── Component ──────────────────────────────────────────────────────────────

export default function QuizCard({
  projectId,
  idea,
  role,
  projectGraph,
  diagrams,
  onSkip,
  onComplete,
}: Props) {
  const [phase,                setPhase]                = useState<Phase>('intro')
  const [questions,            setQuestions]            = useState<Question[]>([])
  const [currentIdx,           setCurrentIdx]           = useState(0)
  const [userAnswer,           setUserAnswer]           = useState('')
  const [currentEvaluation,    setCurrentEvaluation]    = useState<Evaluation | null>(null)
  const [roundEvaluations,     setRoundEvaluations]     = useState<Evaluation[]>([])
  const [roundSummary,         setRoundSummary]         = useState<RoundSummary | null>(null)
  const [allRounds,            setAllRounds]            = useState<RoundSummary[]>([])
  const [allGaps,              setAllGaps]              = useState<string[]>([])
  const [askedQuestions,       setAskedQuestions]       = useState<string[]>([])
  const [roundNumber,          setRoundNumber]          = useState(1)
  const [finalSummary,         setFinalSummary]         = useState<any>(null)
  const [error,                setError]                = useState<string | null>(null)

  const currentQuestion = questions[currentIdx] || null
  const totalQuestions  = questions.length
  const correctSoFar    = roundEvaluations.filter(e => e.is_correct).length

  // ── Handlers ───────────────────────────────────────────────────────────

  const handleStart = async () => {
    setPhase('loading')
    setError(null)
    try {
      const r = await startQuiz(projectId, idea, role, projectGraph, diagrams)
      setQuestions(r.questions || [])
      setAskedQuestions(r.questions?.map((q: Question) => q.question) || [])
      setCurrentIdx(0)
      setRoundEvaluations([])
      setPhase('question')
    } catch (e) {
      setError('Failed to generate questions. Please try again.')
      setPhase('intro')
    }
  }

  const handleSubmitAnswer = async () => {
    if (!userAnswer.trim() || !currentQuestion) return
    setPhase('evaluating')
    setError(null)
    try {
      const r = await submitQuizAnswer(
        projectId, idea, role,
        currentQuestion, userAnswer.trim(), projectGraph,
      )
      const evaluation: Evaluation = r.evaluation
      setCurrentEvaluation(evaluation)
      setPhase('evaluated')
    } catch (e) {
      setError('Evaluation failed. Please try again.')
      setPhase('question')
    }
  }

  const handleNextQuestion = () => {
    if (!currentEvaluation) return
    const newEvals = [...roundEvaluations, currentEvaluation]
    setRoundEvaluations(newEvals)
    setCurrentEvaluation(null)
    setUserAnswer('')

    if (currentIdx + 1 >= totalQuestions) {
      // Round complete — summarize
      handleRoundComplete(newEvals)
    } else {
      setCurrentIdx(prev => prev + 1)
      setPhase('question')
    }
  }

  const handleRoundComplete = async (evals: Evaluation[]) => {
    setPhase('loading')
    try {
      const r = await summarizeQuizRound(
        projectId, questions, evals, roundNumber, idea, role,
      )
      const summary: RoundSummary = r.summary

      // Accumulate gaps
      const newGaps = evals
        .filter(e => !e.is_correct && e.knowledge_gap)
        .map(e => e.knowledge_gap as string)
      setAllGaps(prev => [...prev, ...newGaps])
      setAllRounds(prev => [...prev, summary])
      setRoundSummary(summary)
      setPhase('round_complete')
    } catch (e) {
      setError('Could not summarize round.')
      setPhase('round_complete')
    }
  }

  const handleNextRound = async () => {
    setPhase('loading')
    setError(null)
    const nextRound = roundNumber + 1
    try {
      const r = await getNextQuizRound(
        projectId, idea, role, projectGraph, diagrams,
        nextRound, askedQuestions,
      )
      const newQuestions: Question[] = r.questions || []
      setQuestions(newQuestions)
      setAskedQuestions(prev => [...prev, ...newQuestions.map(q => q.question)])
      setRoundNumber(nextRound)
      setCurrentIdx(0)
      setRoundEvaluations([])
      setRoundSummary(null)
      setPhase('question')
    } catch (e) {
      setError('Failed to generate next round.')
      setPhase('round_complete')
    }
  }

  const handleComplete = async () => {
    setPhase('completing')
    try {
      const r = await completeQuiz(projectId, allGaps, allRounds, idea, role)
      setFinalSummary(r.final_summary)
      setPhase('complete')
      onComplete(allGaps)
    } catch (e) {
      setPhase('complete')
      onComplete(allGaps)
    }
  }

  // ── Render phases ──────────────────────────────────────────────────────

  // INTRO
  if (phase === 'intro') {
    return (
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 w-full">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="text-xs font-mono text-amber-400 uppercase tracking-widest mb-1">
              Stage 7 — Knowledge Check
            </div>
            <p className="text-sm font-medium text-[#e6edf3]">
              Test your understanding of what you built
            </p>
            <p className="text-xs text-[#484f58] mt-1 leading-relaxed">
              5 questions per round · strict evaluation · unlimited rounds
            </p>
          </div>
          <span className="text-2xl">🎓</span>
        </div>

        <div className="grid grid-cols-3 gap-2 mb-5">
          {[
            { icon: '🏗', label: 'Architecture' },
            { icon: '⚙️', label: 'Tech Choices' },
            { icon: '🎤', label: 'Interview Sim' },
          ].map(item => (
            <div key={item.label} className="text-center px-3 py-2.5 bg-[#0d1117] border border-[#21262d] rounded-lg">
              <div className="text-lg mb-1">{item.icon}</div>
              <div className="text-xs text-[#484f58]">{item.label}</div>
            </div>
          ))}
        </div>

        {error && (
          <div className="mb-3 px-3 py-2 bg-red-400/10 border border-red-400/20 rounded-lg">
            <p className="text-xs text-red-400">{error}</p>
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={handleStart}
            className="flex-1 py-2.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg text-sm hover:bg-[#e0a419] transition-colors"
          >
            Start Quiz →
          </button>
          <button
            onClick={onSkip}
            className="px-4 py-2.5 bg-[#0d1117] border border-[#30363d] text-[#484f58] hover:text-[#e6edf3] hover:border-[#8b949e] rounded-lg text-sm transition-colors"
          >
            Skip
          </button>
        </div>
      </div>
    )
  }

  // LOADING
  if (phase === 'loading' || phase === 'completing') {
    return (
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 w-full">
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            {[0, 1, 2].map(i => (
              <div
                key={i}
                style={{ animationDelay: `${i * 0.2}s` }}
                className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"
              />
            ))}
          </div>
          <span className="text-xs text-[#484f58] font-mono">
            {phase === 'completing' ? 'Saving your results...' : `Generating round ${roundNumber} questions...`}
          </span>
        </div>
      </div>
    )
  }

  // QUESTION + EVALUATING + EVALUATED
  if ((phase === 'question' || phase === 'evaluating' || phase === 'evaluated') && currentQuestion) {
    return (
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden w-full">

        {/* Progress header */}
        <div className="px-4 py-3 border-b border-[#21262d] bg-[#0d1117]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-amber-400">
                Round {roundNumber}
              </span>
              <span className="text-xs text-[#30363d]">·</span>
              <span className="text-xs text-[#484f58] font-mono">
                Question {currentIdx + 1} of {totalQuestions}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-emerald-400 font-mono">
                {correctSoFar} correct
              </span>
              <button
                onClick={onSkip}
                className="text-xs text-[#30363d] hover:text-[#484f58] font-mono transition-colors"
              >
                skip quiz
              </button>
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full h-1 bg-[#21262d] rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-400 transition-all duration-300"
              style={{ width: `${((currentIdx) / totalQuestions) * 100}%` }}
            />
          </div>
        </div>

        {/* Question */}
        <div className="px-4 py-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-base">
              {CATEGORY_ICONS[currentQuestion.category] || '❓'}
            </span>
            <span className={`text-xs font-mono px-2 py-0.5 rounded-full border ${DIFFICULTY_COLORS[currentQuestion.difficulty] || DIFFICULTY_COLORS.beginner}`}>
              {currentQuestion.difficulty}
            </span>
            <span className="text-xs text-[#484f58] font-mono">
              {currentQuestion.category.replace(/_/g, ' ')}
            </span>
          </div>

          <p className="text-sm text-[#e6edf3] leading-relaxed mb-4">
            {currentQuestion.question}
          </p>

          {/* Answer input — only when in question phase */}
          {phase === 'question' && (
            <div className="space-y-3">
              <textarea
                value={userAnswer}
                onChange={e => setUserAnswer(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey && userAnswer.trim()) {
                    e.preventDefault()
                    handleSubmitAnswer()
                  }
                }}
                placeholder="Type your answer here..."
                rows={4}
                autoFocus
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2.5 text-sm text-[#e6edf3] placeholder-[#484f58] outline-none focus:border-[#f0b429]/30 transition-colors resize-none"
              />
              <div className="flex justify-end">
                <button
                  onClick={handleSubmitAnswer}
                  disabled={!userAnswer.trim()}
                  className="px-5 py-2 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg text-sm hover:bg-[#e0a419] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Submit →
                </button>
              </div>
            </div>
          )}

          {/* Evaluating spinner */}
          {phase === 'evaluating' && (
            <div className="flex items-center gap-2 py-3">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div key={i} style={{ animationDelay: `${i * 0.2}s` }}
                    className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                ))}
              </div>
              <span className="text-xs text-[#484f58] font-mono">Evaluating your answer...</span>
            </div>
          )}

          {/* Evaluation result */}
          {phase === 'evaluated' && currentEvaluation && (
            <div className="space-y-3">
              {/* User's answer */}
              <div className="px-3 py-2 bg-[#0d1117] border border-[#21262d] rounded-lg">
                <div className="text-xs font-mono text-[#484f58] mb-1">Your answer:</div>
                <p className="text-xs text-[#8b949e] leading-relaxed">{userAnswer}</p>
              </div>

              {/* Verdict */}
              <div className={`px-4 py-3 rounded-lg border ${
                currentEvaluation.is_correct
                  ? 'bg-emerald-400/10 border-emerald-400/20'
                  : 'bg-red-400/10 border-red-400/20'
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">
                    {currentEvaluation.is_correct ? '✓' : '✗'}
                  </span>
                  <span className={`text-sm font-semibold ${
                    currentEvaluation.is_correct ? 'text-emerald-400' : 'text-red-400'
                  }`}>
                    {currentEvaluation.verdict}
                  </span>
                </div>
                <p className="text-xs text-[#e6edf3] leading-relaxed">
                  {currentEvaluation.short_verdict}
                </p>
              </div>

              {/* Explanation */}
              <div className="px-3 py-3 bg-[#0d1117] border border-[#21262d] rounded-lg">
                <div className="text-xs font-mono text-amber-400 mb-1.5">Explanation:</div>
                <p className="text-xs text-[#8b949e] leading-relaxed">
                  {currentEvaluation.explanation}
                </p>
                {currentEvaluation.what_they_got_right && (
                  <div className="mt-2">
                    <span className="text-xs font-mono text-emerald-400">✓ You got: </span>
                    <span className="text-xs text-[#8b949e]">{currentEvaluation.what_they_got_right}</span>
                  </div>
                )}
                {currentEvaluation.what_was_missing && (
                  <div className="mt-1">
                    <span className="text-xs font-mono text-red-400">✗ Missing: </span>
                    <span className="text-xs text-[#8b949e]">{currentEvaluation.what_was_missing}</span>
                  </div>
                )}
                {currentEvaluation.study_tip && (
                  <div className="mt-2 pt-2 border-t border-[#21262d]">
                    <span className="text-xs font-mono text-[#484f58]">Study: </span>
                    <span className="text-xs text-[#484f58]">{currentEvaluation.study_tip}</span>
                  </div>
                )}
              </div>

              <button
                onClick={handleNextQuestion}
                className="w-full py-2.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg text-sm hover:bg-[#e0a419] transition-colors"
              >
                {currentIdx + 1 >= totalQuestions ? 'See Round Summary →' : 'Next Question →'}
              </button>
            </div>
          )}
        </div>
      </div>
    )
  }

  // ROUND COMPLETE
  if (phase === 'round_complete' && roundSummary) {
    const scoreColor =
      roundSummary.score_pct >= 80 ? 'text-emerald-400' :
      roundSummary.score_pct >= 60 ? 'text-amber-400' :
      'text-red-400'

    return (
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden w-full">

        {/* Header */}
        <div className="px-4 py-3 border-b border-[#21262d] bg-[#0d1117]">
          <div className="flex items-center justify-between">
            <div className="text-xs font-mono text-amber-400 uppercase tracking-widest">
              Round {roundNumber} Complete
            </div>
            <span className={`text-lg font-bold font-mono ${scoreColor}`}>
              {roundSummary.score_pct}%
            </span>
          </div>
        </div>

        <div className="px-4 py-4 space-y-4">
          {/* Score */}
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className={`text-3xl font-bold font-mono ${scoreColor}`}>
                {roundSummary.correct}/{roundSummary.total}
              </div>
              <div className="text-xs text-[#484f58] font-mono">correct</div>
            </div>
            <div className="flex-1">
              <div className={`text-sm font-semibold mb-1 ${scoreColor}`}>
                {roundSummary.performance_label}
              </div>
              <p className="text-xs text-[#8b949e] leading-relaxed">
                {roundSummary.summary}
              </p>
            </div>
          </div>

          {/* Strengths */}
          {roundSummary.strengths.length > 0 && (
            <div>
              <div className="text-xs font-mono text-emerald-400 mb-1.5">Strong areas:</div>
              <div className="flex flex-wrap gap-1.5">
                {roundSummary.strengths.map((s, i) => (
                  <span key={i} className="text-xs font-mono px-2 py-0.5 bg-emerald-400/10 border border-emerald-400/20 text-emerald-400 rounded-full">
                    {s.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Gaps */}
          {roundSummary.gaps.length > 0 && (
            <div>
              <div className="text-xs font-mono text-red-400 mb-1.5">Knowledge gaps:</div>
              <div className="flex flex-wrap gap-1.5">
                {roundSummary.gaps.map((g, i) => (
                  <span key={i} className="text-xs font-mono px-2 py-0.5 bg-red-400/10 border border-red-400/20 text-red-400 rounded-full">
                    {g.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Accumulated stats */}
          {allRounds.length > 1 && (
            <div className="px-3 py-2 bg-[#0d1117] border border-[#21262d] rounded-lg">
              <span className="text-xs text-[#484f58] font-mono">
                Total: {allRounds.reduce((sum, r) => sum + r.correct, 0)}/
                {allRounds.reduce((sum, r) => sum + r.total, 0)} across {allRounds.length} rounds ·{' '}
                {allGaps.length} gaps identified
              </span>
            </div>
          )}

          {error && (
            <div className="px-3 py-2 bg-red-400/10 border border-red-400/20 rounded-lg">
              <p className="text-xs text-red-400">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleNextRound}
              className="flex-1 py-2.5 bg-[#0d1117] border border-[#f0b429]/30 text-[#f0b429] hover:border-[#f0b429]/60 rounded-lg text-sm font-semibold transition-colors"
            >
              5 More Questions →
            </button>
            <button
              onClick={handleComplete}
              className="flex-1 py-2.5 bg-[#f0b429] text-[#0d1117] font-semibold rounded-lg text-sm hover:bg-[#e0a419] transition-colors"
            >
              Move to Next Stage →
            </button>
          </div>
        </div>
      </div>
    )
  }

  // COMPLETE
  if (phase === 'complete') {
    const totalQ = allRounds.reduce((s, r) => s + r.total, 0)
    const totalC = allRounds.reduce((s, r) => s + r.correct, 0)
    const finalPct = totalQ > 0 ? Math.round((totalC / totalQ) * 100) : 0

    return (
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 w-full">
        <div className="text-xs font-mono text-emerald-400 uppercase tracking-widest mb-3">
          ✓ Quiz Complete
        </div>
        <div className="flex items-center gap-4 mb-4">
          <div className="text-center">
            <div className="text-3xl font-bold font-mono text-amber-400">{finalPct}%</div>
            <div className="text-xs text-[#484f58] font-mono">overall</div>
          </div>
          <div className="flex-1 text-xs text-[#8b949e] leading-relaxed">
            {totalC}/{totalQ} correct across {allRounds.length} round{allRounds.length !== 1 ? 's' : ''}
            {allGaps.length > 0 && `. ${allGaps.length} knowledge gap${allGaps.length !== 1 ? 's' : ''} saved for Stage 8.`}
          </div>
        </div>
        {allGaps.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {allGaps.slice(0, 5).map((g, i) => (
              <span key={i} className="text-xs font-mono px-2 py-0.5 bg-amber-400/10 border border-amber-400/20 text-amber-400/70 rounded-full">
                {g.replace(/_/g, ' ')}
              </span>
            ))}
            {allGaps.length > 5 && (
              <span className="text-xs text-[#484f58] font-mono">+{allGaps.length - 5} more</span>
            )}
          </div>
        )}
      </div>
    )
  }

  return null
}