import type { Metadata } from 'next'
import { AppShellClient } from '@/components/app/app-shell-client'
import { API_BASE_URL } from '@/lib/api'
import { DEMO_LESSONS, demoManifestUrl, demoVideoUrl, parseDemoId } from '@/lib/showcase'

export const metadata: Metadata = { title: 'Lesson' }

function first(v: string | string[] | undefined) {
  return Array.isArray(v) ? v[0] : v
}

/** A server-safe initial job for a shop-window lesson, in the same shape /api/status returns. */
function demoInitialJob(id: string) {
  const parsed = parseDemoId(id)
  if (!parsed) return null
  return {
    job_id: id,
    status: 'completed',
    stage: 'done',
    pct: 100,
    topic: DEMO_LESSONS[parsed.slug].topic,
    lang: parsed.lang,
    mp4_url: demoVideoUrl(parsed.slug, parsed.lang),
    manifest_url: demoManifestUrl(parsed.slug, parsed.lang),
  }
}

export default async function LessonPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const { id } = await params
  const sp = await searchParams
  const topic = first(sp.topic)
  const language = first(sp.language)
  const qs = new URLSearchParams()
  if (topic) qs.set('topic', topic)
  if (language) qs.set('language', language)
  const next = `/lesson/${encodeURIComponent(id)}${qs.size ? `?${qs}` : ''}`

  let initialJob = demoInitialJob(id)
  if (!initialJob) {
    try {
      const res = await fetch(`${API_BASE_URL}/api/status/${encodeURIComponent(id)}`, { cache: 'no-store' })
      if (res.ok) initialJob = await res.json()
    } catch {}
  }

  return <AppShellClient view="lesson" next={next} id={id} topic={topic} language={language} initialJob={initialJob} />
}
