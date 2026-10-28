'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { Play } from 'lucide-react'
import { API_BASE_URL } from '@/lib/api'

interface LivePreviewProps {
  manifestUrl: string
  audioUrl: string
  stage?: string | null
  onTimeChange?: (t: number) => void
}

export function LivePreview({
  manifestUrl,
  audioUrl,
  stage,
  onTimeChange,
}: LivePreviewProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const animRef = useRef<number | null>(null)

  const postTime = useCallback((t: number) => {
    if (iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage({ type: 'bvt:time', t }, '*')
    }
  }, [])

  const stopLoop = useCallback(() => {
    if (animRef.current !== null) {
      cancelAnimationFrame(animRef.current)
      animRef.current = null
    }
  }, [])

  const startLoop = useCallback(() => {
    stopLoop()
    const tick = () => {
      const audio = audioRef.current
      if (audio && !audio.paused && !audio.ended) {
        const t = audio.currentTime
        postTime(t)
        onTimeChange?.(t)
        animRef.current = requestAnimationFrame(tick)
      } else {
        stopLoop()
      }
    }
    animRef.current = requestAnimationFrame(tick)
  }, [postTime, stopLoop, onTimeChange])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopLoop()
      if (audioRef.current) {
        audioRef.current.pause()
      }
    }
  }, [stopLoop])

  // Listen for bvt:ready from iframe
  useEffect(() => {
    function handleMessage(e: MessageEvent) {
      if (e.data && e.data.type === 'bvt:ready') {
        const t = audioRef.current?.currentTime ?? 0
        postTime(t)
      }
    }
    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [postTime])

  function handlePlayClick() {
    if (audioRef.current) {
      audioRef.current.play().catch(console.error)
    }
  }

  function handlePlay() {
    setIsPlaying(true)
    startLoop()
  }

  function handlePause() {
    setIsPlaying(false)
    stopLoop()
    if (audioRef.current) {
      const t = audioRef.current.currentTime
      postTime(t)
      onTimeChange?.(t)
    }
  }

  function handleSeeked() {
    if (audioRef.current) {
      const t = audioRef.current.currentTime
      postTime(t)
      onTimeChange?.(t)
    }
  }

  function handleEnded() {
    setIsPlaying(false)
    stopLoop()
    if (audioRef.current) {
      const t = audioRef.current.currentTime
      postTime(t)
      onTimeChange?.(t)
    }
  }

  function handleTimeUpdate() {
    if (audioRef.current) {
      onTimeChange?.(audioRef.current.currentTime)
    }
  }

  const iframeSrc = `${API_BASE_URL}/renderer/player.html?manifest=${encodeURIComponent(manifestUrl)}&embed=1`

  return (
    <section
      aria-label="Live lesson preview"
      className="overflow-hidden rounded-3xl border-2 border-ink bg-ink shadow-[8px_8px_0_0_#3474E5]"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-ink bg-amber-100 px-4 py-2 text-xs font-bold text-ink">
        <div className="flex items-center gap-2">
          <span className="relative flex size-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
            <span className="relative inline-flex size-2.5 rounded-full bg-amber-500" />
          </span>
          <span>Live preview · HD video still rendering…</span>
        </div>
        <span className="rounded-full border border-ink/20 bg-white/90 px-2.5 py-0.5 font-mono text-[11px] font-bold uppercase tracking-wider text-ink/80">
          Stage: {stage || 'render'}
        </span>
      </div>

      <div className="relative aspect-video w-full overflow-hidden bg-[#0B1530]">
        <iframe
          ref={iframeRef}
          src={iframeSrc}
          className="size-full border-0 block"
          title="Live lesson preview player"
        />

        {!isPlaying && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-[1px]">
            <button
              type="button"
              onClick={handlePlayClick}
              className="inline-flex items-center gap-2.5 rounded-full border-2 border-ink bg-brand-blue px-7 py-3.5 text-base font-bold text-white shadow-[4px_4px_0_0_#000] transition-transform hover:scale-105 active:scale-95"
              aria-label="Play preview"
            >
              <Play className="size-5 fill-current" />
              <span>Play preview</span>
            </button>
          </div>
        )}
      </div>

      <div className="border-t-2 border-ink bg-cream p-3 sm:p-4">
        <audio
          ref={audioRef}
          src={audioUrl}
          controls
          className="w-full"
          onPlay={handlePlay}
          onPause={handlePause}
          onSeeked={handleSeeked}
          onEnded={handleEnded}
          onTimeUpdate={handleTimeUpdate}
        />
      </div>
    </section>
  )
}
