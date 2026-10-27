'use client'

import { useRef, useState, useEffect } from 'react'
import {
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  Maximize2,
  Download,
  AlertTriangle,
  FileVideo,
  CheckCircle2,
  Subtitles,
  ExternalLink
} from 'lucide-react'

export function LessonPlayer({
  src,
  title,
  manifestUrl
}: {
  src: string
  title: string
  manifestUrl?: string | null
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLElement>(null)

  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [showCaptions, setShowCaptions] = useState(true)
  const [currentCaption, setCurrentCaption] = useState<string>('')
  const [manifest, setManifest] = useState<any>(null)
  const [scenes, setScenes] = useState<any[]>([])
  const [activeSceneIndex, setActiveSceneIndex] = useState(0)
  const [hasError, setHasError] = useState(false)

  const fileName = `${title.replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '').toLowerCase() || 'lesson'}.mp4`

  // Fetch lesson manifest (scenes and narration) if available
  useEffect(() => {
    if (!manifestUrl) return
    let active = true
    fetch(manifestUrl)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!active || !data) return
        setManifest(data)
        if (Array.isArray(data.scenes)) {
          setScenes(data.scenes)
        }
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [manifestUrl])

  // Sync scene captions with video current time
  useEffect(() => {
    if (!scenes.length) return
    let accumulated = 0
    let foundIndex = 0
    let foundText = ''

    for (let i = 0; i < scenes.length; i++) {
      const s = scenes[i]
      const sceneDur = typeof s.duration === 'number' ? s.duration : (s.spoken_words?.length ? s.spoken_words.length * 0.4 : 5)
      if (currentTime >= accumulated && currentTime < accumulated + sceneDur) {
        foundIndex = i
        foundText = s.narration || s.text || s.title || ''
        break
      }
      accumulated += sceneDur
    }

    setActiveSceneIndex(foundIndex)
    setCurrentCaption(foundText)
  }, [currentTime, scenes])

  const togglePlay = () => {
    if (!videoRef.current) return
    if (videoRef.current.paused) {
      videoRef.current.play()
    } else {
      videoRef.current.pause()
    }
  }

  const handleTimeUpdate = () => {
    if (!videoRef.current) return
    setCurrentTime(videoRef.current.currentTime)
  }

  const handleLoadedMetadata = () => {
    if (!videoRef.current) return
    setDuration(videoRef.current.duration)
    setHasError(false)
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value)
    if (videoRef.current) {
      videoRef.current.currentTime = time
      setCurrentTime(time)
    }
  }

  const toggleMute = () => {
    if (!videoRef.current) return
    videoRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const vol = parseFloat(e.target.value)
    setVolume(vol)
    if (videoRef.current) {
      videoRef.current.volume = vol
      videoRef.current.muted = vol === 0
      setIsMuted(vol === 0)
    }
  }

  const restart = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = 0
      videoRef.current.play()
    }
  }

  const jumpToScene = (sceneIdx: number) => {
    if (!videoRef.current || !scenes.length) return
    let t = 0
    for (let i = 0; i < sceneIdx; i++) {
      const s = scenes[i]
      t += typeof s.duration === 'number' ? s.duration : 5
    }
    videoRef.current.currentTime = t
    videoRef.current.play()
  }

  const toggleFullscreen = () => {
    if (!containerRef.current) return
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => {})
    } else {
      document.exitFullscreen().catch(() => {})
    }
  }

  const formatTime = (secs: number) => {
    if (isNaN(secs)) return '0:00'
    const m = Math.floor(secs / 60)
    const s = Math.floor(secs % 60)
    return `${m}:${s < 10 ? '0' : ''}${s}`
  }

  return (
    <section
      ref={containerRef}
      aria-labelledby="player-heading"
      className="flex flex-col overflow-hidden rounded-3xl border-2 border-ink bg-white shadow-[8px_8px_0_0_#3474E5] transition-all"
    >
      <h2 id="player-heading" className="sr-only">
        {title} - Video Player
      </h2>

      {/* Main Video Screen with Editorial Outlines */}
      <div className="relative aspect-video w-full overflow-hidden bg-ink select-none">
        {hasError ? (
          <div className="flex size-full flex-col items-center justify-center gap-3 p-6 text-center text-cream" role="alert">
            <AlertTriangle className="size-10 text-brand-yellow" aria-hidden="true" />
            <p className="font-bold text-lg">Unable to stream video in this browser view.</p>
            <p className="max-w-md text-sm text-cream/75">
              The MP4 file has been exported. You can download it directly or open it in a new tab.
            </p>
          </div>
        ) : (
          <>
            <video
              ref={videoRef}
              key={src}
              src={src}
              playsInline
              preload="metadata"
              onClick={togglePlay}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={handleLoadedMetadata}
              onError={() => setHasError(true)}
              className="size-full cursor-pointer object-contain bg-ink"
            />

            {/* Floating Captions Overlay */}
            {showCaptions && currentCaption && (
              <div className="pointer-events-none absolute bottom-16 inset-x-4 flex justify-center text-center">
                <span className="rounded-2xl border-2 border-ink bg-ink/90 px-5 py-2.5 text-sm md:text-base font-bold text-white shadow-lg backdrop-blur-sm max-w-2xl text-balance">
                  {currentCaption}
                </span>
              </div>
            )}

            {/* Big Centered Play Button when paused */}
            {!isPlaying && (
              <button
                type="button"
                onClick={togglePlay}
                className="absolute inset-0 m-auto flex size-16 items-center justify-center rounded-full border-2 border-ink bg-brand-yellow text-ink shadow-[4px_4px_0_0_#000] transition-transform hover:scale-105 active:scale-95"
                aria-label="Play video"
              >
                <Play className="ml-1 size-8 fill-current" />
              </button>
            )}
          </>
        )}
      </div>

      {/* Custom Player Controls Bar */}
      <div className="flex flex-col gap-3 border-t-2 border-ink bg-cream p-4">
        {/* Progress Scrubber */}
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono font-bold w-10 text-right">{formatTime(currentTime)}</span>
          <input
            type="range"
            min={0}
            max={duration || 100}
            step={0.1}
            value={currentTime}
            onChange={handleSeek}
            className="flex-1 h-2 bg-ink/20 rounded-lg appearance-none cursor-pointer accent-brand-blue"
            aria-label="Seek time"
          />
          <span className="text-xs font-mono font-bold w-10">{formatTime(duration)}</span>
        </div>

        {/* Buttons and volume row */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={togglePlay}
              className="inline-flex size-10 items-center justify-center rounded-full border-2 border-ink bg-white hover:bg-ink hover:text-white transition-colors"
              aria-label={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <Pause className="size-4 fill-current" /> : <Play className="ml-0.5 size-4 fill-current" />}
            </button>
            <button
              type="button"
              onClick={restart}
              className="inline-flex size-10 items-center justify-center rounded-full border-2 border-ink bg-white hover:bg-ink hover:text-white transition-colors"
              aria-label="Restart video"
              title="Restart"
            >
              <RotateCcw className="size-4" />
            </button>

            {/* Volume control */}
            <div className="flex items-center gap-1.5 ml-2">
              <button
                type="button"
                onClick={toggleMute}
                className="inline-flex size-9 items-center justify-center rounded-full hover:bg-ink/10 transition-colors"
                aria-label={isMuted ? 'Unmute' : 'Mute'}
              >
                {isMuted ? <VolumeX className="size-4 text-destructive" /> : <Volume2 className="size-4" />}
              </button>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                className="w-16 h-1.5 bg-ink/20 rounded appearance-none cursor-pointer accent-brand-blue hidden sm:block"
                aria-label="Volume"
              />
            </div>

            {/* Captions toggle */}
            <button
              type="button"
              onClick={() => setShowCaptions((s) => !s)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border-2 text-xs font-bold transition-colors ${
                showCaptions ? 'border-ink bg-brand-yellow text-ink' : 'border-ink/40 bg-white text-muted-foreground'
              }`}
              aria-pressed={showCaptions}
            >
              <Subtitles className="size-3.5" />
              <span>CC</span>
            </button>
          </div>

          {/* Right Action buttons */}
          <div className="flex items-center gap-2">
            <a
              href={src}
              download={fileName}
              className="inline-flex items-center gap-2 rounded-full bg-brand-blue px-5 py-2.5 text-xs font-bold text-white transition-transform hover:-translate-y-0.5"
            >
              <Download className="size-3.5" />
              <span>Download MP4</span>
            </a>
            <a
              href={src}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center size-9 rounded-full border-2 border-ink bg-white hover:bg-ink hover:text-cream transition-colors"
              title="Open raw MP4 in new tab"
            >
              <ExternalLink className="size-3.5" />
            </a>
            <button
              type="button"
              onClick={toggleFullscreen}
              className="inline-flex size-9 items-center justify-center rounded-full border-2 border-ink bg-white hover:bg-ink hover:text-white transition-colors"
              aria-label="Toggle fullscreen"
            >
              <Maximize2 className="size-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Step-by-Step Scenes Navigator (if manifest contains scenes) */}
      {scenes.length > 0 && (
        <div className="border-t-2 border-ink bg-cream/30 p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
              Lesson Chapters ({scenes.length} steps)
            </p>
            <span className="text-xs font-bold text-brand-blue">
              Step {activeSceneIndex + 1} of {scenes.length}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
            {scenes.map((scene, idx) => {
              const active = idx === activeSceneIndex
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => jumpToScene(idx)}
                  className={`flex flex-col text-left p-3 rounded-2xl border-2 transition-all ${
                    active
                      ? 'border-brand-blue bg-white shadow-[4px_4px_0_0_#3474E5] -translate-y-0.5'
                      : 'border-ink/20 bg-white/70 hover:border-ink hover:bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between w-full mb-1">
                    <span className="font-mono text-[10px] font-black uppercase text-muted-foreground">
                      0{idx + 1} {scene.template ? `· ${scene.template}` : ''}
                    </span>
                    {active && <CheckCircle2 className="size-3 text-brand-blue" />}
                  </div>
                  <span className="font-bold text-xs truncate w-full">
                    {scene.title || scene.heading || `Scene ${idx + 1}`}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </section>
  )
}
