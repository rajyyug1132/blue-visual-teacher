'use client'

import Link from 'next/link'
import { ArrowUpRight, History, Loader2 } from 'lucide-react'
import type { DemoSession } from '@/lib/demo-session'
import { useLessonHistory } from '@/hooks/use-api'
import { useShowcase } from '@/hooks/use-showcase'
import { BackendStatus } from './backend-status'
import { LessonForm } from './lesson-form'

export function DashboardView({ session }: { session: DemoSession }) {
  const firstName = session.name.split(' ')[0]
  return (
    <div className="flex flex-col gap-10">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-muted-foreground">Dashboard</p>
          <h1 className="mt-2 font-display text-5xl font-black leading-[0.9] tracking-tighter text-balance md:text-7xl">
            Hi, {firstName}
            <span className="text-brand-blue">.</span>
          </h1>
        </div>
        <Link
          href="/create"
          className="inline-flex items-center gap-2 self-start rounded-full border-2 border-ink px-5 py-2.5 font-bold hover:bg-ink hover:text-cream md:self-auto"
        >
          Full lesson creator
          <ArrowUpRight className="size-4" aria-hidden="true" />
        </Link>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[1.6fr_1fr]">
        <section aria-labelledby="quick-create" className="rounded-3xl border-2 border-ink bg-white p-5 md:p-8">
          <h2 id="quick-create" className="sr-only">
            Quick create
          </h2>
          <LessonForm compact />
        </section>

        <div className="flex flex-col gap-6">
          <BackendStatus />
          <section aria-labelledby="recent-heading" className="rounded-2xl border-2 border-ink bg-cream p-5">
            <h2 id="recent-heading" className="text-xs font-bold uppercase tracking-[0.2em]">
              Recent lessons
            </h2>
            <RecentLessons signedIn={Boolean(session.token)} />
          </section>
        </div>
      </div>
    </div>
  )
}

const LANG_LABEL: Record<string, string> = { en: 'English', hi: 'Hindi', kn: 'Kannada' }

function RecentLessons({ signedIn }: { signedIn: boolean }) {
  const showcase = useShowcase()
  const { data, error, isLoading } = useLessonHistory(signedIn && !showcase)

  if (showcase) {
    return (
      <div className="mt-4 flex flex-col items-start gap-3">
        <span className="inline-flex size-10 items-center justify-center rounded-xl bg-brand-purple text-white">
          <History className="size-5" aria-hidden="true" />
        </span>
        <p className="font-bold">Your lessons live on your machine.</p>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Run Blue Visual Teacher locally and every lesson you generate is listed here.
        </p>
      </div>
    )
  }

  if (!signedIn) {
    return (
      <div className="mt-4 flex flex-col items-start gap-3">
        <span className="inline-flex size-10 items-center justify-center rounded-xl bg-brand-purple text-white">
          <History className="size-5" aria-hidden="true" />
        </span>
        <p className="font-bold">Sign in to keep your lessons.</p>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Lessons you generate are saved to your account and listed here.
        </p>
        <Link href="/login" className="font-bold underline underline-offset-4">
          Sign in
        </Link>
      </div>
    )
  }

  if (isLoading) {
    return (
      <p className="mt-4 flex items-center gap-2 text-sm text-muted-foreground" role="status">
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
        Loading your lessons…
      </p>
    )
  }

  if (error) {
    return <p className="mt-4 text-sm text-muted-foreground">Couldn&apos;t reach the lesson server just now.</p>
  }

  const lessons = data ?? []
  if (lessons.length === 0) {
    return (
      <div className="mt-4 flex flex-col items-start gap-3">
        <span className="inline-flex size-10 items-center justify-center rounded-xl bg-brand-purple text-white">
          <History className="size-5" aria-hidden="true" />
        </span>
        <p className="font-bold">No lessons yet.</p>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Generate your first lesson and it will appear here.
        </p>
      </div>
    )
  }

  return (
    <ul className="mt-4 flex flex-col gap-2">
      {lessons.slice(0, 5).map((lesson) => (
        <li key={lesson.id}>
          <Link
            href={`/lesson/${encodeURIComponent(lesson.id)}`}
            className="flex items-center justify-between gap-3 rounded-xl border-2 border-ink/15 px-3 py-2 hover:border-ink"
          >
            <span className="truncate font-bold">{lesson.topic}</span>
            <span className="shrink-0 text-xs uppercase tracking-wider text-muted-foreground">
              {LANG_LABEL[lesson.lang] ?? lesson.lang}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  )
}
