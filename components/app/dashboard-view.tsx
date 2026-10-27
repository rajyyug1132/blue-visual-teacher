import Link from 'next/link'
import { ArrowUpRight, History } from 'lucide-react'
import type { DemoSession } from '@/lib/demo-session'
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
            <div className="mt-4 flex flex-col items-start gap-3">
              <span className="inline-flex size-10 items-center justify-center rounded-xl bg-brand-purple text-white">
                <History className="size-5" aria-hidden="true" />
              </span>
              <p className="font-bold">No lesson history yet.</p>
              <p className="text-sm leading-relaxed text-muted-foreground">
                The lesson server doesn&apos;t expose a history endpoint, so past lessons can&apos;t be listed here.
                Keep the lesson page link to revisit a video.
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
