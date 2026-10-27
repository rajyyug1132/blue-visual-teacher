import { BackendStatus } from './backend-status'
import { LessonForm } from './lesson-form'

const TIPS = [
  'Ask a question: “Why is the sky blue?” works better than “sky”.',
  'Keep it to one concept per lesson.',
  'Add your level: “for class 8” or “for beginners”.',
]

export function CreateView({ topic, language }: { topic?: string; language?: string }) {
  return (
    <div className="flex flex-col gap-10">
      <div>
        <p className="text-sm font-bold uppercase tracking-[0.2em] text-muted-foreground">Create</p>
        <h1 className="mt-2 font-display text-5xl font-black leading-[0.9] tracking-tighter text-balance md:text-7xl">
          New lesson<span className="text-brand-orange">.</span>
        </h1>
      </div>
      <div className="grid items-start gap-6 lg:grid-cols-[1.6fr_1fr]">
        <section aria-label="Lesson details" className="rounded-3xl border-2 border-ink bg-white p-5 md:p-8">
          <LessonForm initialTopic={topic} initialLanguage={language} />
        </section>
        <aside className="flex flex-col gap-6">
          <BackendStatus />
          <section aria-labelledby="tips-heading" className="rounded-2xl border-2 border-ink bg-brand-green p-5 text-ink">
            <h2 id="tips-heading" className="text-xs font-bold uppercase tracking-[0.2em]">
              Tips for better lessons
            </h2>
            <ul className="mt-4 flex flex-col gap-3">
              {TIPS.map((tip, i) => (
                <li key={tip} className="flex gap-3 text-sm font-medium leading-relaxed">
                  <span className="font-display font-black">{String(i + 1).padStart(2, '0')}</span>
                  {tip}
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </div>
  )
}
