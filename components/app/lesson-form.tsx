'use client'

import { useRouter } from 'next/navigation'
import { useState, type FormEvent } from 'react'
import { AlertTriangle, ArrowUpRight, Loader2, RotateCcw } from 'lucide-react'
import { ApiError, createLesson } from '@/lib/api'
import { RunLocally } from './run-locally'
import { EXAMPLE_TOPICS } from '@/lib/languages'
import { useLanguages } from '@/hooks/use-api'
import { useShowcase } from '@/hooks/use-showcase'
import { cn } from '@/lib/utils'

const MIN_TOPIC = 3
const MAX_TOPIC = 300

export function lessonHref(id: string, topic: string, language: string) {
  return `/lesson/${encodeURIComponent(id)}?topic=${encodeURIComponent(topic)}&language=${encodeURIComponent(language)}`
}

export function LessonForm({
  initialTopic = '',
  initialLanguage = 'en',
  compact = false,
}: {
  initialTopic?: string
  initialLanguage?: string
  compact?: boolean
}) {
  const router = useRouter()
  const { data: langData, isLoading: langsLoading } = useLanguages()
  const showcase = useShowcase()
  const languages = langData?.languages ?? []

  const [topic, setTopic] = useState(initialTopic.slice(0, MAX_TOPIC))
  const [language, setLanguage] = useState(initialLanguage)
  const [level, setLevel] = useState<'beginner' | 'intermediate'>('beginner')
  const [targetSec, setTargetSec] = useState<number>(60)
  const [topicError, setTopicError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<{ message: string; retryable: boolean; offline?: 'preview' | 'down' } | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const selectedLanguage = languages.some((l) => l.code === language) ? language : (languages[0]?.code ?? language)

  function validateTopic(value: string) {
    const t = value.trim()
    if (!t) return 'Enter a topic you want to learn about.'
    if (t.length < MIN_TOPIC) return `Make the topic at least ${MIN_TOPIC} characters.`
    if (t.length > MAX_TOPIC) return `Keep the topic under ${MAX_TOPIC} characters.`
    return null
  }

  async function onSubmit(e?: FormEvent<HTMLFormElement>) {
    e?.preventDefault()
    if (submitting) return
    const err = validateTopic(topic)
    setTopicError(err)
    if (err) {
      document.getElementById('lesson-topic')?.focus()
      return
    }
    setSubmitting(true)
    setSubmitError(null)
    try {
      const job = await createLesson({
        topic: topic.trim(),
        language: selectedLanguage,
        level,
        target_sec: targetSec,
      })
      router.push(lessonHref(job.id, topic.trim(), selectedLanguage))
    } catch (error) {
      const apiErr = error instanceof ApiError ? error : null
      const isClientError = apiErr?.kind === 'http' && apiErr.status !== undefined && apiErr.status < 500
      setSubmitError({
        message: apiErr?.message ?? 'Something went wrong while creating your lesson.',
        retryable: !isClientError,
        offline: apiErr?.kind === 'showcase' ? 'preview' : apiErr?.kind === 'network' ? 'down' : undefined,
      })
      setSubmitting(false)
    }
  }

  return (
    <form noValidate onSubmit={onSubmit} className="flex flex-col gap-6" aria-busy={submitting}>
      <div className="flex flex-col gap-2">
        <label htmlFor="lesson-topic" className="font-display text-xl font-extrabold tracking-tight">
          What do you want to learn?
        </label>
        <textarea
          id="lesson-topic"
          value={topic}
          onChange={(e) => {
            setTopic(e.target.value)
            if (topicError) setTopicError(validateTopic(e.target.value))
          }}
          rows={compact ? 2 : 3}
          maxLength={MAX_TOPIC}
          placeholder="What is binary search, and why is it faster than linear search?"
          aria-invalid={topicError ? true : undefined}
          aria-describedby={topicError ? 'topic-error' : 'topic-count'}
          className={cn(
            'w-full resize-none rounded-2xl border-2 bg-white px-4 py-3.5 text-base leading-relaxed outline-none transition-shadow focus:shadow-[4px_4px_0_0_#3474E5] md:text-lg',
            topicError ? 'border-destructive' : 'border-ink',
          )}
        />
        <div className="flex items-start justify-between gap-3">
          {topicError ? (
            <p id="topic-error" className="text-sm font-semibold text-destructive">
              {topicError}
            </p>
          ) : (
            <span />
          )}
          <p id="topic-count" className="shrink-0 text-xs text-muted-foreground">
            {topic.length}/{MAX_TOPIC}
          </p>
        </div>
        <div className="flex flex-wrap gap-2" aria-label="Example topics">
          {EXAMPLE_TOPICS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => {
                setTopic(t)
                setTopicError(null)
              }}
              className="rounded-full border border-ink bg-cream px-3 py-1.5 text-sm font-medium transition-colors hover:bg-ink hover:text-cream"
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 font-display text-xl font-extrabold tracking-tight">Narration language</legend>
        {langsLoading ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
            <Loader2 className="size-4 animate-spin" aria-hidden="true" /> Loading languages…
          </p>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {languages.map((l) => {
                const checked = selectedLanguage === l.code
                return (
                  <label
                    key={l.code}
                    className={cn(
                      'flex cursor-pointer items-center justify-between gap-3 rounded-2xl border-2 border-ink px-4 py-3 transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-brand-blue',
                      checked ? 'bg-brand-blue text-white' : 'bg-white hover:bg-cream',
                    )}
                  >
                    <input
                      type="radio"
                      name="language"
                      value={l.code}
                      checked={checked}
                      onChange={() => setLanguage(l.code)}
                      className="sr-only"
                    />
                    <span>
                      <span className="block font-bold" lang={l.code}>
                        {l.nativeName}
                      </span>
                      {l.nativeName !== l.name && <span className="block text-xs opacity-80">{l.name}</span>}
                    </span>
                    <span
                      aria-hidden="true"
                      className={cn('size-4 rounded-full border-2', checked ? 'border-white bg-white' : 'border-ink')}
                    />
                  </label>
                )
              })}
            </div>
            {langData?.source === 'fallback' && !showcase && (
              <p className="text-xs text-muted-foreground">
                {"Couldn't load languages from the server. Showing the default list (English, Hindi, Kannada)."}
              </p>
            )}
          </>
        )}
      </fieldset>


      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 font-display text-xl font-extrabold tracking-tight">Learner level</legend>
          <div className="grid grid-cols-2 gap-2">
            {(['beginner', 'intermediate'] as const).map((lvl) => {
              const checked = level === lvl
              return (
                <label
                  key={lvl}
                  className={cn(
                    'flex cursor-pointer items-center justify-between gap-2 rounded-2xl border-2 border-ink px-3.5 py-3 transition-colors font-bold capitalize text-sm sm:text-base',
                    checked ? 'bg-brand-blue text-white' : 'bg-white hover:bg-cream',
                  )}
                >
                  <input
                    type="radio"
                    name="level"
                    value={lvl}
                    checked={checked}
                    onChange={() => setLevel(lvl)}
                    className="sr-only"
                  />
                  <span>{lvl}</span>
                  <span
                    aria-hidden="true"
                    className={cn('size-3.5 rounded-full border-2 shrink-0', checked ? 'border-white bg-white' : 'border-ink')}
                  />
                </label>
              )
            })}
          </div>
        </fieldset>

        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label htmlFor="target-sec" className="font-display text-xl font-extrabold tracking-tight">
              Target length
            </label>
            <span className="rounded-full border-2 border-ink bg-white px-3 py-0.5 text-xs font-black">
              {targetSec}s
            </span>
          </div>
          <div className="mt-2 flex items-center">
            <input
              id="target-sec"
              type="range"
              min={30}
              max={90}
              step={5}
              value={targetSec}
              onChange={(e) => setTargetSec(Number(e.target.value))}
              className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-ink/20 accent-brand-blue"
            />
          </div>
          <div className="flex justify-between text-[11px] font-semibold text-muted-foreground">
            <span>30s (quick)</span>
            <span>60s (standard)</span>
            <span>90s (deep)</span>
          </div>
        </div>
      </div>


      {submitError?.offline ? (
        <RunLocally variant={submitError.offline} />
      ) : submitError && (

        <div role="alert" className="flex flex-col gap-3 rounded-2xl border-2 border-destructive bg-white p-4 sm:flex-row sm:items-start">
          <AlertTriangle className="size-5 shrink-0 text-destructive" aria-hidden="true" />
          <div className="flex-1">
            <p className="font-bold">{"We couldn't start your lesson."}</p>
            <p className="mt-1 text-sm text-muted-foreground">{submitError.message}</p>
          </div>
          {submitError.retryable && (
            <button
              type="button"
              onClick={() => onSubmit()}
              className="inline-flex items-center gap-2 self-start rounded-full border-2 border-ink px-4 py-2 text-sm font-bold hover:bg-ink hover:text-cream"
            >
              <RotateCcw className="size-4" aria-hidden="true" />
              Retry
            </button>
          )}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting || langsLoading}
        className="group inline-flex h-14 items-center justify-center gap-3 rounded-full bg-ink px-8 font-bold text-cream transition-transform hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 sm:self-start"
      >
        {submitting ? (
          <>
            <Loader2 className="size-5 animate-spin" aria-hidden="true" />
            Sending to lesson server…
          </>
        ) : (
          <>
            Generate lesson
            <span className="inline-flex size-7 items-center justify-center rounded-full bg-brand-yellow text-ink transition-transform group-hover:rotate-45">
              <ArrowUpRight className="size-4" aria-hidden="true" />
            </span>
          </>
        )}
      </button>
    </form>
  )
}
