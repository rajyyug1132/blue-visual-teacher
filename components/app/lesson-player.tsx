'use client'

import { useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  Download,
  ExternalLink,
  Loader2,
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  Sparkles,
} from 'lucide-react'
import { replanScene } from '@/lib/api'

interface Scene {
  id?: number | string
  start_sec?: number
  end_sec?: number
  duration_sec?: number
  narration?: string
  visual?: any
}

interface Manifest {
  title?: string
  total_sec?: number
  lang?: string
  scenes?: Scene[]
}

export function LessonPlayer({
  src,
  title,
  manifestUrl,
  topic,
  lang,
}: {
  src: string
  title: string
  manifestUrl?: string | null
  topic?: string | null
  lang?: string | null
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [failed, setFailed] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [manifest, setManifest] = useState<Manifest | null>(null)
  const [replanning, setReplanning] = useState(false)
  const [replanStatus, setReplanStatus] = useState<string | null>(null)

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

  async function handleReplanSimpler() {
    if (!manifest?.scenes || manifest.scenes.length === 0) return
    const activeScene = manifest.scenes[activeSceneIdx]
    const sceneId = typeof activeScene.id === 'number' ? activeScene.id : activeSceneIdx + 1
    const effTopic = topic || manifest.title || title
    const effLang = lang || manifest.lang || 'en'

    setReplanning(true)
    setReplanStatus(null)

    try {
      const res = await replanScene({
        topic: effTopic,
        sceneId,
        currentScene: activeScene,
        lang: effLang,
      })

      if (res.ok) {
        if (res.manifest) {
          setManifest(res.manifest)
        } else if (res.scene) {
          const updated = [...manifest.scenes]
          updated[activeSceneIdx] = {
            ...updated[activeSceneIdx],
            narration: res.scene.narration,
            visual: res.scene.visual ?? updated[activeSceneIdx].visual,
            duration_sec: res.duration_sec ?? updated[activeSceneIdx].duration_sec,
          }
          setManifest({ ...manifest, scenes: updated })
        }
        setReplanStatus(`Scene ${activeSceneIdx + 1} simplified!`)
        setTimeout(() => setReplanStatus(null), 3000)

        if (videoRef.current && sceneBoundaries[activeSceneIdx] !== undefined) {
          videoRef.current.currentTime = sceneBoundaries[activeSceneIdx]
          videoRef.current.play().catch(() => {})
        }
      } else {
        setReplanStatus('Simplification failed.')
        setTimeout(() => setReplanStatus(null), 3000)
      }
    } catch {
      setReplanStatus('Could not replan scene.')
      setTimeout(() => setReplanStatus(null), 3000)
    } finally {
      setReplanning(false)
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
              if (videoRef.current) setDuration(videoRef.current.duration)
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
          <div className="flex flex-wrap items-center gap-2">
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
              <div className="ml-1 flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-ink/20 bg-ink/5 px-2.5 py-1 text-xs font-bold text-ink/75">
                  Scene {activeSceneIdx + 1} of {manifest.scenes.length}
                </span>

                <button
                  type="button"
                  onClick={handleReplanSimpler}
                  disabled={replanning}
                  className="inline-flex items-center gap-1.5 rounded-full border-2 border-brand-orange bg-brand-yellow/30 px-3 py-1 text-xs font-extrabold text-ink shadow-sm transition-transform hover:scale-105 hover:bg-brand-yellow disabled:cursor-not-allowed disabled:opacity-50"
                  title="Explain again with a simpler 10-year-old everyday Indian analogy"
                >
                  {replanning ? (
                    <Loader2 className="size-3.5 animate-spin text-brand-orange" />
                  ) : (
                    <Sparkles className="size-3.5 text-brand-orange" />
                  )}
                  <span>{replanning ? 'Simplifying…' : 'Explain Again, Simpler'}</span>
                </button>

                {replanStatus && (
                  <span className="rounded-full border border-brand-green/40 bg-brand-green/20 px-2.5 py-0.5 text-[11px] font-bold text-brand-green">
                    {replanStatus}
                  </span>
                )}
              </div>
            )}
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
