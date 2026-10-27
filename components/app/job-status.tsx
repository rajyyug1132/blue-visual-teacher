import { Check, Loader2, X } from 'lucide-react'
import type { Job } from '@/lib/api'
import { cn } from '@/lib/utils'

const STEPS = [
  { key: 'queued', label: 'Queued' },
  { key: 'processing', label: 'Generating' },
  { key: 'completed', label: 'Ready' },
] as const

function stepIndex(status: Job['status']) {
  if (status === 'queued' || status === 'unknown') return 0
  if (status === 'processing') return 1
  return 2
}

export function JobStatus({ job, polling }: { job: Job; polling: boolean }) {
  const current = stepIndex(job.status)
  const failed = job.status === 'failed'

  return (
    <section aria-labelledby="status-heading" className="rounded-3xl border-2 border-ink bg-white p-5 md:p-6">
      <div className="flex items-center justify-between gap-3">
        <h2 id="status-heading" className="text-xs font-bold uppercase tracking-[0.2em]">
          Generation status
        </h2>
        {polling && (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
            Checking every few seconds
          </span>
        )}
      </div>

      <ol className="mt-5 grid grid-cols-3 gap-2">
        {STEPS.map((step, i) => {
          const done = !failed && (i < current || job.status === 'completed')
          const active = !failed && i === current && job.status !== 'completed'
          const failedHere = failed && i === Math.max(current, 1)
          return (
            <li key={step.key} className="flex flex-col gap-2">
              <span
                className={cn(
                  'h-2.5 rounded-full border border-ink',
                  done ? 'bg-brand-green' : active ? 'bg-brand-yellow' : failedHere ? 'bg-destructive' : 'bg-cream',
                )}
              />
              <span className="flex items-center gap-1.5 text-sm font-bold">
                {done && <Check className="size-4" aria-hidden="true" />}
                {active && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
                {failedHere && <X className="size-4" aria-hidden="true" />}
                {failedHere ? 'Failed' : step.label}
                <span className="sr-only">
                  {done ? ' (done)' : active ? ' (in progress)' : failedHere ? '' : ' (pending)'}
                </span>
              </span>
            </li>
          )
        })}
      </ol>

      <div className="mt-5 rounded-2xl bg-cream px-4 py-3 text-sm" role="status" aria-live="polite">
        <p className="font-semibold">
          {failed
            ? 'Lesson generation failed.'
            : job.status === 'completed'
              ? 'Your lesson is ready.'
              : job.status === 'processing'
                ? 'Building visuals and narration…'
                : job.status === 'queued'
                  ? 'Waiting for the lesson server to pick up your job…'
                  : `Server reported status "${job.rawStatus ?? 'unknown'}".`}
        </p>
        {job.stage && <p className="mt-1 text-muted-foreground">Stage: {job.stage}</p>}
        {job.message && job.message !== job.stage && <p className="mt-1 text-muted-foreground">{job.message}</p>}
      </div>
      <p className="mt-3 break-all text-xs text-muted-foreground">Job ID: {job.id}</p>
    </section>
  )
}
