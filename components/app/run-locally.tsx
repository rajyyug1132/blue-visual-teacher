'use client'

import { Laptop, Server } from 'lucide-react'
import { REPO_URL } from '@/lib/showcase'

/**
 * Shown instead of an error when no lesson server is reachable.
 * "preview": the public shop window, which never has one. "down": a local install whose server isn't running.
 */
export function RunLocally({ variant }: { variant: 'preview' | 'down' }) {
  if (variant === 'down') {
    return (
      <div role="status" className="flex flex-col gap-3 rounded-2xl border-2 border-ink bg-brand-yellow/30 p-4">
        <p className="flex items-center gap-2 font-bold">
          <Server className="size-5 shrink-0" aria-hidden="true" />
          The lesson server isn&apos;t running
        </p>
        <p className="text-sm leading-relaxed">Start it from the project folder, then generate again:</p>
        <pre className="overflow-x-auto rounded-xl bg-ink px-3 py-2 text-xs text-cream">
          <code>{'./run_demo.ps1    # Windows\n./run_demo.sh     # macOS / Linux'}</code>
        </pre>
      </div>
    )
  }

  return (
    <div role="status" className="flex flex-col gap-3 rounded-2xl border-2 border-ink bg-brand-yellow/30 p-4">
      <p className="flex items-center gap-2 font-bold">
        <Laptop className="size-5 shrink-0" aria-hidden="true" />
        Generate lessons on your own machine
      </p>
      <p className="text-sm leading-relaxed">
        This is a live preview of the interface. Blue Visual Teacher builds every lesson offline: planning, translation,
        narration and video all run on your computer with no cloud calls, so there&apos;s no lesson server here.
      </p>
      <pre className="overflow-x-auto rounded-xl bg-ink px-3 py-2 text-xs text-cream">
        <code>
          {`git clone ${REPO_URL}\ncd blue-visual-teacher\n./run_demo.ps1              # or ./run_demo.sh: starts the lesson server\nnpm install && npm run dev  # then open http://localhost:3000`}
        </code>
      </pre>
      <a href={REPO_URL} target="_blank" rel="noreferrer" className="self-start text-sm font-bold underline underline-offset-4">
        Setup and requirements on GitHub
      </a>
    </div>
  )
}
