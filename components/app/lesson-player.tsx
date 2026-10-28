'use client'

import { useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  Download,
  ExternalLink,
  Play,
  Pause,
  RotateCcw,
  SkipForward,
} from 'lucide-react'

interface Scene {
  id?: number | string
  start_sec?: number
  end_sec?: number
  duration_sec?: number
  narration?: string
}

const SPEEDS = [0.75, 1, 1.25, 1.5] as const

function applySpeed(el: HTMLMediaElement | null, rate: number) {
  if (!el) return
  el.playbackRate = rate
  el.preservesPitch = true
  const anyEl = el as any
  if ('mozPreservesPitch' in anyEl) anyEl.mozPreservesPitch = true
  if ('webkitPreservesPitch' in anyEl) anyEl.webkitPreservesPitch = true
}

interface Manifest {
  title?: string
  total_sec?: number
  scenes?: Scene[]
}

export function LessonPlayer({
  src,
  title,
  manifestUrl,
  initialTime = 0,
  initialSpeed,
  onSpeedChange,
}: {
  src: string
  title: string
  manifestUrl?: string | null
  initialTime?: number
  initialSpeed?: number
  onSpeedChange?: (s: number) => void
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [failed, setFailed] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [manifest, setManifest] = useState<Manifest | null>(null)
  const [speed, setSpeed] = useState<number>(() => {
    if (initialSpeed && (SPEEDS as readonly number[]).includes(initialSpeed)) return initialSpeed
    try {
      const saved = localStorage.getItem('bvt-playback-speed')
      if (saved) {
        const val = parseFloat(saved)
        if ((SPEEDS as readonly number[]).includes(val)) return val
      }
    } catch {}
    return 1
  })

  function updateSpeed(newSpeed: number) {
    setSpeed(newSpeed)
    onSpeedChange?.(newSpeed)
    try {
      localStorage.setItem('bvt-playback-speed', String(newSpeed))
    } catch {}
    applySpeed(videoRef.current, newSpeed)
  }

  useEffect(() => {
    applySpeed(videoRef.current, speed)
  }, [speed])

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
        return
      }
      if (e.key === '<' || (e.shiftKey && e.key === ',')) {
        e.preventDefault()
        const idx = SPEEDS.indexOf(speed as (typeof SPEEDS)[number])
        if (idx > 0) updateSpeed(SPEEDS[idx - 1])
      } else if (e.key === '>' || (e.shiftKey && e.key === '.')) {
        e.preventDefault()
        const idx = SPEEDS.indexOf(speed as (typeof SPEEDS)[number])
        if (idx !== -1 && idx < SPEEDS.length - 1) updateSpeed(SPEEDS[idx + 1])
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [speed])

  const fileName = `${title.replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '').toLowerCase() || 'lesson'}.mp4`

  useEffect(() => {
    if (!manifestUrl) return
    let active = true
    fetch(manifestUrl)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (active && data) setManifest(data)
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [manifestUrl])

  // Compute scene boundaries (timestamps in seconds)
  const sceneBoundaries: number[] = []
  if (manifest?.scenes && manifest.scenes.length > 0) {
    let cumulative = 0
    for (let i = 0; i < manifest.scenes.length; i++) {
      const s = manifest.scenes[i]
      if (typeof s.start_sec === 'number') {
        sceneBoundaries.push(s.start_sec)
        cumulative = s.end_sec ?? (s.start_sec + (s.duration_sec ?? 0))
      } else {
        sceneBoundaries.push(cumulative)
        cumulative += s.duration_sec ?? 0
      }
    }
  }

  // Find active scene index
  let activeSceneIdx = 0
  if (sceneBoundaries.length > 0) {
    for (let i = sceneBoundaries.length - 1; i >= 0; i--) {
      if (currentTime >= sceneBoundaries[i] - 0.25) {
        activeSceneIdx = i
        break
      }
    }
  }

  function togglePlay() {
    if (!videoRef.current) return
    if (videoRef.current.paused) {
      videoRef.current.play().catch(() => {})
    } else {
      videoRef.current.pause()
    }
  }

  function replay() {
    if (!videoRef.current) return
    videoRef.current.currentTime = 0
    videoRef.current.play().catch(() => {})
  }

  function nextScene() {
    if (!videoRef.current) return
    const cur = videoRef.current.currentTime
    // Find next boundary strictly ahead of current position
    const nextTime = sceneBoundaries.find((t) => t > cur + 0.35)
    if (nextTime !== undefined) {
      videoRef.current.currentTime = nextTime
      videoRef.current.play().catch(() => {})
    } else if (duration > 0 && cur < duration - 0.5) {
      videoRef.current.currentTime = duration
    }
  }

  function formatTime(sec: number) {
    const s = Math.floor(sec)
    const m = Math.floor(s / 60)
    const rem = s % 60
    return `${m}:${rem.toString().padStart(2, '0')}`
  }

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
        <div className="relative aspect-video w-full bg-black">
          <video
            ref={videoRef}
            key={src}
            src={src}
            controls
            playsInline
            preload="metadata"
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
            onTimeUpdate={() => {
              if (videoRef.current) setCurrentTime(videoRef.current.currentTime)
            }}
            onLoadedMetadata={() => {
              if (videoRef.current) {
                applySpeed(videoRef.current, speed)
                setDuration(videoRef.current.duration)
                if (initialTime > 0 && initialTime < videoRef.current.duration) {
                  videoRef.current.currentTime = initialTime
                }
              }
            }}
            onError={() => setFailed(true)}
            className="size-full bg-black"
          >
            {'Your browser does not support embedded video.'}
          </video>
        </div>
      )}

      {/* Primary Video Controls Bar */}
      <div className="border-t-2 border-ink bg-white px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={togglePlay}
              className="inline-flex size-11 items-center justify-center rounded-full bg-brand-blue text-white shadow-sm transition-transform hover:scale-105"
              aria-label={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <Pause className="size-5" /> : <Play className="ml-0.5 size-5" />}
            </button>

            <button
              type="button"
              onClick={replay}
              className="inline-flex size-10 items-center justify-center rounded-full border-2 border-ink bg-cream text-ink transition-transform hover:scale-105 hover:bg-ink hover:text-cream"
              title="Replay from start"
              aria-label="Replay lesson"
            >
              <RotateCcw className="size-4" />
            </button>

            <button
              type="button"
              onClick={nextScene}
              disabled={sceneBoundaries.length === 0 || activeSceneIdx >= sceneBoundaries.length - 1}
              className="inline-flex items-center gap-1.5 rounded-full border-2 border-ink bg-cream px-3.5 py-2 text-xs font-bold text-ink transition-transform hover:scale-105 hover:bg-ink hover:text-cream disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:scale-100 disabled:hover:bg-cream disabled:hover:text-ink"
              title="Skip to next scene"
            >
              <SkipForward className="size-3.5" />
              <span>Next scene</span>
            </button>

            {manifest?.scenes && manifest.scenes.length > 0 && (
              <span className="ml-2 rounded-full border border-ink/20 bg-ink/5 px-2.5 py-1 text-xs font-bold text-ink/75">
                Scene {activeSceneIdx + 1} of {manifest.scenes.length}
              </span>
            )}

            {/* Playback speed selector */}
            <div
              role="group"
              aria-label="Playback speed"
              className="ml-2 inline-flex items-center rounded-full border-2 border-ink bg-cream p-0.5 text-xs font-bold"
            >
              {SPEEDS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => updateSpeed(s)}
                  className={`rounded-full px-2.5 py-1 text-xs font-bold transition-all ${
                    speed === s
                      ? 'bg-brand-blue text-white shadow-sm'
                      : 'text-ink hover:bg-ink/10'
                  }`}
                  aria-pressed={speed === s}
                  aria-label={`${s}x speed`}
                >
                  {s}×
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono font-bold text-ink/70">
            <span>{formatTime(currentTime)}</span>
            <span>/</span>
            <span>{formatTime(duration || manifest?.total_sec || 0)}</span>
          </div>
        </div>
      </div>

      {/* Export / Download Bar */}
      <div className="flex flex-col gap-2 border-t-2 border-ink bg-cream p-3 sm:flex-row">
        <a
          href={src}
          download={fileName}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-brand-blue px-6 py-2.5 text-sm font-bold text-white transition-transform hover:-translate-y-0.5"
        >
          <Download className="size-4" aria-hidden="true" />
          Download MP4
        </a>
        <a
          href={src}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center justify-center gap-2 rounded-full border-2 border-ink px-6 py-2.5 text-sm font-bold hover:bg-ink hover:text-cream"
        >
          <ExternalLink className="size-4" aria-hidden="true" />
          Open in new tab
        </a>
      </div>
    </section>
  )
}
