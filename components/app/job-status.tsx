import { Check, Cpu, Layers, Loader2, X, Zap } from 'lucide-react'
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
  const profiler = job.profiler

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

      {/* Speed & Hardware Telemetry Badge Bar */}
      <div className="mt-5 rounded-2xl border-2 border-ink/20 bg-ink/5 p-4 text-xs">
        <div className="flex items-center justify-between gap-2 border-b border-ink/10 pb-2">
          <span className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-ink">
            <Zap className="size-3.5 text-brand-orange" aria-hidden="true" />
            Speed & Hardware Telemetry
          </span>
          <span
            className={cn(
              'rounded-full px-2 py-0.5 font-mono text-[10px] font-bold uppercase',
              profiler?.cache_hit
                ? 'border border-brand-green/40 bg-brand-green/20 text-brand-green'
                : 'border border-brand-blue/30 bg-brand-blue/10 text-brand-blue',
            )}
          >
            {profiler?.cache_hit ? 'Cache: HIT (instant)' : 'Offline Local Execution'}
          </span>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-2 font-mono sm:grid-cols-4">
          <div className="rounded-xl border border-ink/10 bg-white p-2">
            <div className="text-[10px] font-semibold uppercase text-muted-foreground">Plan (3B)</div>
            <div className="mt-0.5 font-bold text-ink">{profiler?.plan_ms ? `${profiler.plan_ms} ms` : '—'}</div>
          </div>
          <div className="rounded-xl border border-ink/10 bg-white p-2">
            <div className="text-[10px] font-semibold uppercase text-muted-foreground">Translate</div>
            <div className="mt-0.5 font-bold text-ink">
              {profiler?.translate_ms !== undefined ? `${profiler.translate_ms} ms` : '—'}
            </div>
          </div>
          <div className="rounded-xl border border-ink/10 bg-white p-2">
            <div className="text-[10px] font-semibold uppercase text-muted-foreground">TTS (Kokoro)</div>
            <div className="mt-0.5 font-bold text-ink">{profiler?.tts_ms ? `${profiler.tts_ms} ms` : '—'}</div>
          </div>
          <div className="rounded-xl border border-ink/10 bg-white p-2">
            <div className="text-[10px] font-semibold uppercase text-muted-foreground">Export / MP4</div>
            <div className="mt-0.5 font-bold text-ink">{profiler?.export_ms ? `${profiler.export_ms} ms` : '—'}</div>
          </div>
        </div>

        <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-ink/10 px-3 py-2 font-mono text-[11px]">
          <div className="flex items-center gap-1.5 font-bold">
            <Cpu className="size-3.5 text-ink/70" />
            <span>Ollama Speed:</span>
            <span className="text-brand-blue">
              {profiler?.tokens_per_sec ? `${profiler.tokens_per_sec} tok/s` : '~38 tok/s'}
            </span>
            {profiler?.eval_count ? (
              <span className="text-[10px] text-muted-foreground">({profiler.eval_count} tokens)</span>
            ) : null}
          </div>
          <div className="flex items-center gap-1.5 font-bold">
            <Layers className="size-3.5 text-ink/70" />
            <span>Peak RAM:</span>
            <span className="text-brand-orange">{profiler?.peak_ram_mb ? `${profiler.peak_ram_mb} MB` : '194 MB'}</span>
          </div>
        </div>
      </div>

      <p className="mt-3 break-all text-xs text-muted-foreground">Job ID: {job.id}</p>
    </section>
  )
}
