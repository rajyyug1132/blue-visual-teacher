import type { Metadata } from 'next'
import { AppShellClient } from '@/components/app/app-shell-client'
import { API_BASE_URL } from '@/lib/api'

export const metadata: Metadata = { title: 'Lesson' }

function first(v: string | string[] | undefined) {
  return Array.isArray(v) ? v[0] : v
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

  let initialJob = null
  try {
    const res = await fetch(`${API_BASE_URL}/api/status/${encodeURIComponent(id)}`, { cache: 'no-store' })
    if (res.ok) initialJob = await res.json()
  } catch {}

  return <AppShellClient view="lesson" next={next} id={id} topic={topic} language={language} initialJob={initialJob} />
}
