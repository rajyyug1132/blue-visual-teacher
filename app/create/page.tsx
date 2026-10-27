import type { Metadata } from 'next'
import { AppShellClient } from '@/components/app/app-shell-client'

export const metadata: Metadata = { title: 'Create a lesson' }

function first(v: string | string[] | undefined) {
  return Array.isArray(v) ? v[0] : v
}

export default async function CreatePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const sp = await searchParams
  const topic = first(sp.topic)
  const language = first(sp.language)
  const qs = new URLSearchParams()
  if (topic) qs.set('topic', topic)
  if (language) qs.set('language', language)
  const next = `/create${qs.size ? `?${qs}` : ''}`

  return <AppShellClient view="create" next={next} topic={topic} language={language} />
}
