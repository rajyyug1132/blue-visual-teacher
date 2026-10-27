'use client'

import { useRouter } from 'next/navigation'
import { Film, Laptop, Server } from 'lucide-react'
import { DEMO_LESSONS, REPO_URL } from '@/lib/showcase'

/**
 * Shown instead of an error when no lesson server is reachable.
 * "preview": the public shop window, which never has one. "down": a local install whose server isn't running.
 * In "preview" it also offers the real, pre-made lessons that ship with the site, in the selected language.
 */
export function RunLocally({ variant, language = 'en' }: { variant: 'preview' | 'down'; language?: string }) {
  const router = useRouter()

  if (variant === 'down') {
    return (
      <div role="status" className="flex flex-col gap-3 rounded-2xl border-2 border-ink bg-brand-yellow/30 p-4">
        <p className="flex items-center gap-2 font-bold">
          <Server className="size-5 shrink-0" aria-hidden="true" />
          The lesson server isn&apos;t running
        </p>
        <p className="text-sm leading-relaxed">Start it from the project folder, then generate again:</p>
        <pre className="overflow-x-auto rounded-xl bg-ink px-3 py-2 text-xs text-cream">
          <code>{'powershell -ExecutionPolicy Bypass -File run_demo.ps1      # macOS/Linux: ./run_demo.sh'}</code>
        </pre>
      </div>
    )
  }

  const demoTopics = Object.entries(DEMO_LESSONS).filter(([, d]) => d.langs.includes(language))

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
      {demoTopics.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="flex items-center gap-2 text-sm font-bold">
            <Film className="size-4 shrink-0" aria-hidden="true" />
            Or try a ready-made lesson in this language:
          </p>
          <div className="flex flex-wrap gap-2">
            {demoTopics.map(([slug, d]) => {
              const id = `demo_${slug}_${language}`
              const topic = d.topic
              return (
                <button
                  key={slug}
                  type="button"
                  onClick={() =>
                    router.push(`/lesson/${id}?topic=${encodeURIComponent(topic)}&language=${encodeURIComponent(language)}`)
                  }
                  className="rounded-full border-2 border-ink bg-white px-3 py-1.5 text-sm font-bold transition-colors hover:bg-ink hover:text-cream"
                >
                  {topic}
                </button>
              )
            })}
          </div>
        </div>
      )}
      <pre className="overflow-x-auto rounded-xl bg-ink px-3 py-2 text-xs text-cream">
        <code>
          {`git clone --branch v1 https://github.com/rajyyug1132/blue-visual-teacher
cd blue-visual-teacher
# one-time setup: see README "Run it locally" (Python 3.11 venv, Ollama + qwen2.5:3b, FFmpeg, model download)
# terminal 1: lesson server
powershell -ExecutionPolicy Bypass -File run_demo.ps1      # macOS/Linux: ./run_demo.sh
# terminal 2: the app
npm install
npm run dev                                                # open http://localhost:3000`}
        </code>
      </pre>
      <a href={`${REPO_URL}/tree/v1#readme`} target="_blank" rel="noreferrer" className="self-start text-sm font-bold underline underline-offset-4">
        Setup and requirements on GitHub
      </a>
    </div>
  )
}
