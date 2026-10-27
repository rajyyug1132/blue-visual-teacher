'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { ArrowUpRight, History, Play, CheckCircle2, Clock, AlertCircle, Download } from 'lucide-react'
import type { UserSession } from '@/lib/demo-session'
import { getUserLessonHistory, type LessonRecord } from '@/lib/api'
import { languageLabel } from '@/lib/languages'
import { BackendStatus } from './backend-status'
import { LessonForm } from './lesson-form'

export function DashboardView({ session }: { session: UserSession }) {
  const firstName = session.name.split(' ')[0]
  const [lessons, setLessons] = useState<LessonRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const hist = await getUserLessonHistory()
        if (active) setLessons(hist)
      } catch {
        // user not authenticated or network error
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => {
      active = false
    }
  }, [])

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
        <div className="flex flex-col gap-8">
          <section aria-labelledby="quick-create" className="rounded-3xl border-2 border-ink bg-white p-5 md:p-8">
            <h2 id="quick-create" className="text-sm font-bold uppercase tracking-[0.2em] text-muted-foreground mb-4">
              Quick create lesson
            </h2>
            <LessonForm compact />
          </section>

          {/* User's Persistent Lesson History */}
          <section aria-labelledby="history-heading" className="rounded-3xl border-2 border-ink bg-white p-5 md:p-8">
            <div className="flex items-center justify-between mb-6">
              <h2 id="history-heading" className="font-display text-2xl font-black tracking-tight">
                Your Saved Lessons ({lessons.length})
              </h2>
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">SQLite Storage</span>
            </div>

            {loading ? (
              <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
                <Clock className="size-4 animate-spin text-brand-blue" />
                Loading your lessons...
              </div>
            ) : lessons.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center rounded-2xl border-2 border-dashed border-ink/20">
                <span className="inline-flex size-12 items-center justify-center rounded-2xl bg-brand-yellow/30 text-ink mb-3">
                  <History className="size-6" />
                </span>
                <p className="font-bold text-lg">No lessons yet.</p>
                <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                  Enter any concept above (like Ohm&apos;s Law or Photosynthesis) to generate your first narrated visual lesson.
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {lessons.map((item) => (
                  <div
                    key={item.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl border-2 border-ink bg-cream/40 hover:bg-cream transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="truncate font-bold text-base">{item.topic}</span>
                        <span className="shrink-0 rounded-full border border-ink bg-white px-2 py-0.5 text-xs font-semibold">
                          {languageLabel(item.lang)}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground font-medium">
                        <span className="flex items-center gap-1">
                          {item.status === 'completed' ? (
                            <CheckCircle2 className="size-3.5 text-emerald-600" />
                          ) : item.status === 'failed' ? (
                            <AlertCircle className="size-3.5 text-rose-600" />
                          ) : (
                            <Clock className="size-3.5 text-brand-blue animate-pulse" />
                          )}
                          <span className="capitalize">{item.status}</span>
                        </span>
                        <span>•</span>
                        <span>{new Date(item.createdAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {item.mp4Url && (
                        <a
                          href={item.mp4Url}
                          download={`${item.topic.replace(/\s+/g, '_')}.mp4`}
                          className="inline-flex items-center justify-center size-9 rounded-full border-2 border-ink bg-white hover:bg-ink hover:text-white transition-colors"
                          title="Download MP4"
                        >
                          <Download className="size-4" />
                        </a>
                      )}
                      <Link
                        href={`/lesson/${item.id}?topic=${encodeURIComponent(item.topic)}&language=${encodeURIComponent(item.lang)}`}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border-2 border-ink bg-brand-blue text-white text-xs font-bold hover:-translate-y-0.5 transition-transform"
                      >
                        <Play className="size-3.5 fill-current" />
                        Watch
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        <div className="flex flex-col gap-6">
          <BackendStatus />
          <section aria-labelledby="tips-heading" className="rounded-2xl border-2 border-ink bg-cream p-5">
            <h2 id="tips-heading" className="text-xs font-bold uppercase tracking-[0.2em]">
              Learning Tips
            </h2>
            <div className="mt-4 flex flex-col items-start gap-3">
              <span className="inline-flex size-10 items-center justify-center rounded-xl bg-brand-yellow text-ink font-bold text-sm">
                AI
              </span>
              <p className="font-bold">Offline & Synchronized</p>
              <p className="text-sm leading-relaxed text-muted-foreground">
                All visual lesson timings are derived directly from the speech audio. Each scene matches the spoken explanation with zero drift.
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
