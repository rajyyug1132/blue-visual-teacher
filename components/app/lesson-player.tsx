'use client'

import { useState } from 'react'
import { AlertTriangle, Download, ExternalLink } from 'lucide-react'

export function LessonPlayer({ src, title }: { src: string; title: string }) {
  const [failed, setFailed] = useState(false)
  const fileName = `${title.replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '').toLowerCase() || 'lesson'}.mp4`

  return (
    <section aria-labelledby="player-heading" className="overflow-hidden rounded-3xl border-2 border-ink bg-ink shadow-[8px_8px_0_0_#3474E5]">
      <h2 id="player-heading" className="sr-only">
        Lesson video
      </h2>
      {failed ? (
        <div className="flex aspect-video flex-col items-center justify-center gap-3 bg-ink p-6 text-center text-cream" role="alert">
          <AlertTriangle className="size-8 text-brand-yellow" aria-hidden="true" />
          <p className="font-bold">{"The video couldn't be played in the browser."}</p>
          <p className="max-w-md text-sm text-cream/75">
            The file may still be available. Try opening it directly or downloading it below.
          </p>
        </div>
      ) : (
        <video
          key={src}
          src={src}
          controls
          playsInline
          preload="metadata"
          onError={() => setFailed(true)}
          className="aspect-video w-full bg-ink"
        >
          {'Your browser does not support embedded video.'}
        </video>
      )}
      <div className="flex flex-col gap-2 border-t-2 border-ink bg-cream p-3 sm:flex-row">
        <a
          href={src}
          download={fileName}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-brand-blue px-6 py-3 font-bold text-white transition-transform hover:-translate-y-0.5"
        >
          <Download className="size-4" aria-hidden="true" />
          Download MP4
        </a>
        <a
          href={src}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center justify-center gap-2 rounded-full border-2 border-ink px-6 py-3 font-bold hover:bg-ink hover:text-cream"
        >
          <ExternalLink className="size-4" aria-hidden="true" />
          Open in new tab
        </a>
      </div>
    </section>
  )
}
