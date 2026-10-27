'use client'

import { RefreshCw } from 'lucide-react'
import { useHealth } from '@/hooks/use-api'
import { useShowcase } from '@/hooks/use-showcase'
import { API_BASE_URL } from '@/lib/api'
import { cn } from '@/lib/utils'

export function BackendStatus({ className }: { className?: string }) {
  const showcase = useShowcase()
  const { data, isLoading, isValidating, mutate } = useHealth()
  const state = isLoading ? 'checking' : data?.ok ? 'up' : 'down'

  if (showcase) {
    return (
      <div className={cn('rounded-2xl border-2 border-ink bg-white p-4', className)}>
        <h2 className="text-xs font-bold uppercase tracking-[0.2em]">Lesson server</h2>
        <p className="mt-2 flex items-center gap-2 font-semibold" role="status">
          <span aria-hidden="true" className="size-2.5 rounded-full bg-brand-yellow" />
          Preview mode
        </p>
        <p className="mt-1 text-xs text-muted-foreground">Lessons generate offline on your own machine.</p>
      </div>
    )
  }

  return (
    <div className={cn('rounded-2xl border-2 border-ink bg-white p-4', className)}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xs font-bold uppercase tracking-[0.2em]">Lesson server</h2>
        <button
          type="button"
          onClick={() => mutate()}
          disabled={isValidating}
          className="inline-flex size-8 items-center justify-center rounded-full hover:bg-ink/10 disabled:opacity-50"
        >
          <RefreshCw className={cn('size-4', isValidating && 'animate-spin')} aria-hidden="true" />
          <span className="sr-only">Re-check lesson server</span>
        </button>
      </div>
      <p className="mt-2 flex items-center gap-2 font-semibold" role="status">
        <span
          aria-hidden="true"
          className={cn(
            'size-2.5 rounded-full',
            state === 'up' ? 'bg-brand-green' : state === 'down' ? 'bg-destructive' : 'bg-brand-yellow',
          )}
        />
        {state === 'checking' ? 'Checking connection…' : data?.message}
      </p>
      <p className="mt-1 break-all text-xs text-muted-foreground">{API_BASE_URL}</p>
      {state === 'down' && (
        <p className="mt-2 text-xs">
          Start it with <code className="font-bold">run_demo</code> in the project folder.
        </p>
      )}
    </div>
  )
}
