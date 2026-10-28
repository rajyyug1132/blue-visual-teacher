'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { AlertTriangle, ArrowLeft, Loader2, RotateCcw } from 'lucide-react'
import { useJob } from '@/hooks/use-api'
import { ApiError, createLesson, resolveArtifactUrl } from '@/lib/api'
import { languageLabel } from '@/lib/languages'
import { JobStatus } from './job-status'
import { LessonPlayer } from './lesson-player'
import { LivePreview } from './live-preview'
import { useShowcase } from '@/hooks/use-showcase'
import { lessonHref } from './lesson-form'

export function LessonView({ id, topic: topicParam, language: languageParam, initialJob }: { id: string; topic?: string; language?: string; initialJob?: any }) {
  const router = useRouter()
  const { data: polledJob, error, isLoading, isValidating, mutate } = useJob(id)
  const job = polledJob ?? (initialJob ? {
    id: initialJob.job_id || id,
    status: initialJob.status || 'completed',
    rawStatus: initialJob.status || 'completed',
    stage: initialJob.stage || 'done',
    message: null,
    error: initialJob.error || null,
    videoUrl: resolveArtifactUrl(initialJob.mp4_url || initialJob.video_url),
    manifestUrl: resolveArtifactUrl(initialJob.manifest_url),
    audioUrl: resolveArtifactUrl(initialJob.audio_url),
    topic: initialJob.topic || topicParam || null,
    language: initialJob.lang || languageParam || null,
    pct: initialJob.pct ?? 100
  } : undefined)
  if (typeof window !== 'undefined') console.log('[DEBUG LessonView]', { id, job, error: error ? String(error) : null, isLoading })
  const [regenerating, setRegenerating] = useState(false)
  const [regenError, setRegenError] = useState<string | null>(null)
  const [previewTime, setPreviewTime] = useState<number>(0)
  const showcase = useShowcase()
  const isDemo = id.startsWith('demo_') || showcase
  const showLivePreview = Boolean(!isDemo && job && job.status !== 'completed' && job.manifestUrl && job.audioUrl)

  const topic = job?.topic ?? topicParam ?? null
  const language = job?.language ?? languageParam ?? null
  const title = topic ?? 'Untitled lesson'
  const terminal = job?.status === 'completed' || job?.status === 'failed'

  async function regenerate() {
    if (!topic || !language) return
    setRegenerating(true)
    setRegenError(null)
    try {
      const next = await createLesson({ topic, language })
      router.push(lessonHref(next.id, topic, language))
    } catch (e) {
      setRegenError(e instanceof ApiError ? e.message : 'Could not start a new lesson.')
      setRegenerating(false)
    }
  }

  const retryCreatePath = topic
    ? `/create?topic=${encodeURIComponent(topic)}${language ? `&language=${encodeURIComponent(language)}` : ''}`
    : '/create'

  return (
    <div className="flex flex-col gap-8">
      <div>
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold hover:underline">
          <ArrowLeft className="size-4" aria-hidden="true" />
          Dashboard
        </Link>
        <h1 className="mt-4 font-display text-4xl font-black leading-[0.92] tracking-tighter text-balance md:text-6xl">
          {title}
        </h1>
        {language && (
          <p className="mt-3 inline-block rounded-full border border-ink bg-white px-3 py-1 text-sm font-semibold">
            {languageLabel(language)}
          </p>
        )}
      </div>

      {isLoading && !job ? (
        <div className="flex items-center gap-2 rounded-3xl border-2 border-ink bg-white p-6" role="status">
          <Loader2 className="size-5 animate-spin" aria-hidden="true" />
          Fetching lesson status…
        </div>
      ) : null}

      {error && (
        <div role="alert" className="flex flex-col gap-4 rounded-3xl border-2 border-destructive bg-white p-6 sm:flex-row sm:items-start">
          <AlertTriangle className="size-6 shrink-0 text-destructive" aria-hidden="true" />
          <div className="flex-1">
            <p className="font-bold">
              {error instanceof ApiError && error.status === 404
                ? "We couldn't find this lesson job."
                : 'Lost contact with the lesson server.'}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {error instanceof Error ? error.message : 'Unknown error.'}{' '}
              {job && !terminal ? 'Status updates are paused.' : ''}
            </p>
          </div>
          <button
            type="button"
            onClick={() => mutate()}
            disabled={isValidating}
            className="inline-flex items-center gap-2 self-start rounded-full border-2 border-ink px-4 py-2 text-sm font-bold hover:bg-ink hover:text-cream disabled:opacity-50"
          >
            <RotateCcw className={isValidating ? 'size-4 animate-spin' : 'size-4'} aria-hidden="true" />
            Retry
          </button>
        </div>
      )}

      {job && (
        <div className="grid items-start gap-6 lg:grid-cols-[1.6fr_1fr]">
          <div className="flex flex-col gap-6">
            {job.status === 'completed' && job.videoUrl ? (
              <LessonPlayer
                src={job.videoUrl}
                title={title}
                manifestUrl={job.manifestUrl}
                initialTime={previewTime}
              />
            ) : job.status === 'completed' ? (
              <Notice
                title="Lesson finished, but no video link was returned."
                body="The server reported completion without an MP4 URL. Check the exporter's status response for the video field."
              />
            ) : job.status === 'failed' ? (
              <div className="rounded-3xl border-2 border-ink bg-white p-6" role="alert">
                <p className="font-display text-2xl font-extrabold tracking-tight">This lesson failed to generate.</p>
                <p className="mt-2 text-sm text-muted-foreground">
                  {job.error ?? job.message ?? 'The server did not give a reason.'}
                </p>
                <div className="mt-5 flex flex-col gap-2 sm:flex-row">
                  {topic && language ? (
                    <button
                      type="button"
                      onClick={regenerate}
                      disabled={regenerating}
                      className="inline-flex items-center justify-center gap-2 rounded-full bg-ink px-6 py-3 font-bold text-cream disabled:opacity-60"
                    >
                      {regenerating ? (
                        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                      ) : (
                        <RotateCcw className="size-4" aria-hidden="true" />
                      )}
                      {regenerating ? 'Starting again…' : 'Try again'}
                    </button>
                  ) : null}
                  <Link
                    href={retryCreatePath}
                    className="inline-flex items-center justify-center rounded-full border-2 border-ink px-6 py-3 font-bold hover:bg-ink hover:text-cream"
                  >
                    Edit topic
                  </Link>
                </div>
                {regenError && (
                  <p className="mt-3 text-sm font-semibold text-destructive" role="alert">
                    {regenError}
                  </p>
                )}
              </div>
            ) : showLivePreview ? (
              <LivePreview
                manifestUrl={job.manifestUrl!}
                audioUrl={job.audioUrl!}
                stage={job.stage}
                onTimeChange={setPreviewTime}
              />
            ) : (
              <GeneratingPlaceholder />
            )}
          </div>
          <JobStatus job={job} polling={!terminal && !error} />
        </div>
      )}
    </div>
  )
}

function Notice({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-3xl border-2 border-ink bg-brand-yellow p-6" role="status">
      <p className="font-display text-2xl font-extrabold tracking-tight">{title}</p>
      <p className="mt-2 text-sm">{body}</p>
    </div>
  )
}

function GeneratingPlaceholder() {
  return (
    <div className="relative flex aspect-video flex-col items-center justify-center gap-4 overflow-hidden rounded-3xl border-2 border-ink bg-cream">
      <div aria-hidden="true" className="absolute inset-0 bg-grid opacity-60 [--grid-size:40px]" />
      <div aria-hidden="true" className="relative grid grid-cols-3 gap-2">
        {['bg-brand-blue', 'bg-brand-yellow', 'bg-brand-orange', 'bg-brand-green', 'bg-brand-purple', 'bg-ink'].map(
          (c, i) => (
            <span key={c} className={`size-8 animate-pulse rounded-md ${c}`} style={{ animationDelay: `${i * 150}ms` }} />
          ),
        )}
      </div>
      <p className="relative rounded-full border border-ink bg-white px-4 py-1.5 text-sm font-bold">
        Your lesson is being generated
      </p>
    </div>
  )
}
