'use client'

import { useState, useEffect } from 'react'
import { CheckCircle2, XCircle, RotateCcw, ArrowRight } from 'lucide-react'

interface Question {
  question: string
  options: string[]
  answer: number
  explanation: string
}

interface QuizData {
  questions: Question[]
}

export function QuizCard({ quizUrl }: { quizUrl: string }) {
  const [quiz, setQuiz] = useState<QuizData | null>(null)
  const [currentIdx, setCurrentIdx] = useState(0)
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)
  const [score, setScore] = useState(0)
  const [isCompleted, setIsCompleted] = useState(false)

  useEffect(() => {
    let active = true
    fetch(quizUrl)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (active && data?.questions?.length) {
          setQuiz(data)
        }
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [quizUrl])

  if (!quiz || !quiz.questions || quiz.questions.length === 0) return null

  const currentQ = quiz.questions[currentIdx]

  function handleSelect(optionIdx: number) {
    if (selectedIdx !== null) return
    setSelectedIdx(optionIdx)
    if (optionIdx === currentQ.answer) {
      setScore((s) => s + 1)
    }
  }

  function handleNext() {
    if (quiz && currentIdx + 1 < quiz.questions.length) {
      setCurrentIdx((i) => i + 1)
      setSelectedIdx(null)
    } else {
      setIsCompleted(true)
    }
  }

  function handleReset() {
    setCurrentIdx(0)
    setSelectedIdx(null)
    setScore(0)
    setIsCompleted(false)
  }

  return (
    <div className="overflow-hidden rounded-3xl border-2 border-ink bg-white p-6 shadow-[8px_8px_0_0_#3474E5]">
      <div className="flex items-center justify-between border-b-2 border-ink/10 pb-3">
        <h3 className="font-display text-xl font-black tracking-tight text-ink">
          Quick check
        </h3>
        {!isCompleted && (
          <span className="rounded-full border border-ink/20 bg-cream px-3 py-1 font-mono text-xs font-bold text-ink">
            Question {currentIdx + 1} of {quiz.questions.length}
          </span>
        )}
      </div>

      {isCompleted ? (
        <div className="py-6 text-center">
          <p className="font-display text-2xl font-black text-ink">
            Quiz complete!
          </p>
          <p className="mt-2 text-sm text-ink/75">
            You scored {score} out of {quiz.questions.length}.
          </p>
          <button
            type="button"
            onClick={handleReset}
            className="mt-5 inline-flex items-center gap-2 rounded-full border-2 border-ink bg-brand-blue px-6 py-2.5 text-sm font-bold text-white shadow-sm transition-transform hover:scale-105"
          >
            <RotateCcw className="size-4" />
            Try again
          </button>
        </div>
      ) : (
        <div className="mt-4">
          <p className="text-base font-bold text-ink">{currentQ.question}</p>
          <div className="mt-4 flex flex-col gap-2.5">
            {currentQ.options.map((opt, idx) => {
              const isSelected = selectedIdx === idx
              const isCorrect = idx === currentQ.answer
              let btnStyle = 'border-2 border-ink bg-cream text-ink hover:bg-ink/5'
              if (selectedIdx !== null) {
                if (isCorrect) {
                  btnStyle = 'border-2 border-emerald-600 bg-emerald-50 text-emerald-950 font-bold'
                } else if (isSelected) {
                  btnStyle = 'border-2 border-rose-600 bg-rose-50 text-rose-950 font-bold'
                } else {
                  btnStyle = 'border-2 border-ink/30 bg-gray-50 text-ink/50'
                }
              }

              return (
                <button
                  key={idx}
                  type="button"
                  disabled={selectedIdx !== null}
                  onClick={() => handleSelect(idx)}
                  className={`flex w-full items-center justify-between rounded-2xl px-4 py-3 text-left text-sm font-semibold transition-all ${btnStyle}`}
                >
                  <span>{opt}</span>
                  {selectedIdx !== null && isCorrect && (
                    <CheckCircle2 className="size-5 shrink-0 text-emerald-600" />
                  )}
                  {selectedIdx !== null && isSelected && !isCorrect && (
                    <XCircle className="size-5 shrink-0 text-rose-600" />
                  )}
                </button>
              )
            })}
          </div>

          {selectedIdx !== null && (
            <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-ink/15 bg-cream/50 p-3.5">
              <p className="text-xs leading-relaxed text-ink/80">
                <span className="font-bold">Explanation: </span>
                {currentQ.explanation}
              </p>
              <button
                type="button"
                onClick={handleNext}
                className="inline-flex items-center justify-center gap-1.5 self-end rounded-full bg-ink px-5 py-2 text-xs font-bold text-cream transition-transform hover:scale-105"
              >
                <span>{currentIdx + 1 < quiz.questions.length ? 'Next question' : 'Finish quiz'}</span>
                <ArrowRight className="size-3.5" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
