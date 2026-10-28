'use client'

import { useEffect, useState } from 'react'
import { Pause, Play, RotateCcw } from 'lucide-react'
import { cn } from '@/lib/utils'

type LangCode = 'en' | 'hi' | 'kn'

const STAGES: { key: string; label: Record<LangCode, string>; caption: Record<LangCode, string> }[] = [
  {
    key: 'evaporation',
    label: { en: 'Evaporation', hi: 'वाष्पीकरण', kn: 'ಆವಿಯಾಗುವಿಕೆ' },
    caption: {
      en: 'Sunlight warms the sea. Water turns into vapour and rises into the sky.',
      hi: 'सूरज की गर्मी से समुद्र का पानी भाप बनकर ऊपर उठता है।',
      kn: 'ಸೂರ್ಯನ ಶಾಖದಿಂದ ಸಮುದ್ರದ ನೀರು ಆವಿಯಾಗಿ ಮೇಲೇರುತ್ತದೆ.',
    },
  },
  {
    key: 'condensation',
    label: { en: 'Condensation', hi: 'संघनन', kn: 'ಸಾಂದ್ರೀಕರಣ' },
    caption: {
      en: 'High up, the air is cold. Vapour cools into tiny droplets that form clouds.',
      hi: 'ऊपर की ठंडी हवा में भाप छोटी बूंदों में बदलकर बादल बनाती है।',
      kn: 'ಮೇಲಿನ ತಂಪಾದ ಗಾಳಿಯಲ್ಲಿ ಆವಿ ಸಣ್ಣ ಹನಿಗಳಾಗಿ ಮೋಡವಾಗುತ್ತದೆ.',
    },
  },
  {
    key: 'precipitation',
    label: { en: 'Precipitation', hi: 'वर्षण', kn: 'ಮಳೆ' },
    caption: {
      en: 'Droplets join together and grow heavy. They fall back down as rain.',
      hi: 'बूंदें मिलकर भारी हो जाती हैं और बारिश बनकर गिरती हैं।',
      kn: 'ಹನಿಗಳು ಸೇರಿ ಭಾರವಾಗಿ ಮಳೆಯಾಗಿ ಕೆಳಗೆ ಬೀಳುತ್ತವೆ.',
    },
  },
  {
    key: 'collection',
    label: { en: 'Collection', hi: 'संग्रहण', kn: 'ಸಂಗ್ರಹಣೆ' },
    caption: {
      en: 'Rain flows into rivers and lakes and back to the sea. The cycle begins again.',
      hi: 'बारिश का पानी नदियों से होकर फिर समुद्र में पहुँचता है। चक्र फिर शुरू होता है।',
      kn: 'ಮಳೆನೀರು ನದಿಗಳ ಮೂಲಕ ಮತ್ತೆ ಸಮುದ್ರ ಸೇರುತ್ತದೆ. ಚಕ್ರ ಮತ್ತೆ ಆರಂಭವಾಗುತ್ತದೆ.',
    },
  },
]

const LANGS: { code: LangCode; label: string }[] = [
  { code: 'en', label: 'EN' },
  { code: 'hi', label: 'हिं' },
  { code: 'kn', label: 'ಕನ್ನ' },
]

const TITLES: Record<LangCode, string> = {
  en: 'The water cycle',
  hi: 'जल चक्र',
  kn: 'ಜಲ ಚಕ್ರ',
}

const STEP_MS = 3200

export function LessonPreview() {
  const [step, setStep] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [lang, setLang] = useState<LangCode>('en')

  useEffect(() => {
    if (!playing) return
    const id = window.setInterval(() => {
      setStep((s) => {
        if (s >= STAGES.length - 1) {
          setPlaying(false)
          return s
        }
        return s + 1
      })
    }, STEP_MS)
    return () => window.clearInterval(id)
  }, [playing])

  const stage = STAGES[step]
  const atEnd = step === STAGES.length - 1 && !playing

  function togglePlay() {
    if (atEnd) setStep(0)
    setPlaying((p) => !p || atEnd)
  }

  return (
    <figure
      className="relative overflow-hidden rounded-3xl border-2 border-ink bg-white shadow-[8px_8px_0_0_#080808]"
      aria-label="Interactive preview of a Blue Visual Teacher lesson about the water cycle"
    >
      {/* Window chrome */}
      <div className="flex items-center justify-between gap-3 border-b-2 border-ink bg-cream px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="size-3 shrink-0 rounded-full bg-brand-orange" aria-hidden="true" />
          <span className="size-3 shrink-0 rounded-full bg-brand-yellow" aria-hidden="true" />
          <span className="size-3 shrink-0 rounded-full bg-brand-green" aria-hidden="true" />
          <span className="ml-2 truncate text-xs font-semibold">Lesson · {TITLES[lang]}</span>
        </div>
        <div role="group" aria-label="Preview language" className="flex shrink-0 rounded-full border border-ink p-0.5">
          {LANGS.map((l) => (
            <button
              key={l.code}
              type="button"
              onClick={() => setLang(l.code)}
              aria-pressed={lang === l.code}
              className={cn(
                'rounded-full px-2.5 py-1 text-xs font-bold transition-colors',
                lang === l.code ? 'bg-brand-blue text-white' : 'hover:bg-ink/10',
              )}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stage */}
      <div className="relative bg-[#fbf6f1] bg-grid-faint [--grid-size:32px]">
        <WaterCycleDiagram active={stage.key} playing={playing} />
        <div className="absolute left-3 top-3 rounded-full border border-ink bg-white px-3 py-1 text-[0.7rem] font-bold uppercase tracking-wider">
          {String(step + 1).padStart(2, '0')} · {stage.label[lang]}
        </div>
      </div>

      {/* Caption */}
      <figcaption className="min-h-[5.5rem] border-t-2 border-ink px-4 py-3 md:px-5">
        <p lang={lang} className="text-pretty text-sm font-medium leading-relaxed md:text-base" aria-live="polite">
          {stage.caption[lang]}
        </p>
      </figcaption>

      {/* Controls */}
      <div className="flex items-center gap-3 border-t-2 border-ink bg-ink px-4 py-3 text-cream">
        <button
          type="button"
          onClick={togglePlay}
          className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-brand-yellow text-ink transition-transform hover:scale-105"
        >
          {playing ? (
            <Pause className="size-4" aria-hidden="true" />
          ) : atEnd ? (
            <RotateCcw className="size-4" aria-hidden="true" />
          ) : (
            <Play className="size-4 translate-x-px" aria-hidden="true" />
          )}
          <span className="sr-only">{playing ? 'Pause preview' : atEnd ? 'Replay preview' : 'Play preview'}</span>
        </button>

        <div className="flex flex-1 gap-1" role="group" aria-label="Lesson chapters">
          {STAGES.map((s, i) => (
            <button
              key={s.key}
              type="button"
              onClick={() => {
                setStep(i)
                setPlaying(false)
              }}
              className="group h-6 flex-1 py-2"
              aria-label={`Go to step ${i + 1}: ${s.label.en}`}
              aria-current={i === step ? 'step' : undefined}
            >
              <span
                className={cn(
                  'block h-full rounded-full transition-colors',
                  i < step ? 'bg-cream' : i === step ? 'bg-brand-blue' : 'bg-cream/25 group-hover:bg-cream/50',
                )}
              />
            </button>
          ))}
        </div>

        <div className="flex h-5 w-8 shrink-0 items-end gap-0.5" aria-hidden="true">
          {[0, 1, 2, 3].map((i) => (
            <span
              key={i}
              className={cn('w-1 flex-1 rounded-sm bg-brand-yellow', playing ? 'animate-bar' : 'h-1')}
              style={playing ? { height: '100%', animationDelay: `${i * 120}ms` } : undefined}
            />
          ))}
        </div>
        <span className="sr-only">{playing ? 'Narration indicator active' : 'Narration paused'}</span>
      </div>

      <p className="border-t border-ink/20 bg-cream px-4 py-2 text-[0.7rem] font-medium text-muted-foreground">
        Interactive design preview built from local illustrations — not a generated lesson.
      </p>
    </figure>
  )
}

function WaterCycleDiagram({ active, playing }: { active: string; playing: boolean }) {
  const on = (key: string) => (active === key ? 1 : 0.28)
  return (
    <svg viewBox="0 0 400 230" className="block h-auto w-full" role="img" aria-label="Diagram of the water cycle">
      {/* Sun */}
      <g style={{ opacity: on('evaporation'), transition: 'opacity 400ms' }}>
        <circle cx="58" cy="56" r="24" fill="#FFB90B" stroke="#080808" strokeWidth="2" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
          <line
            key={deg}
            x1="58"
            y1="22"
            x2="58"
            y2="14"
            stroke="#080808"
            strokeWidth="2"
            strokeLinecap="round"
            transform={`rotate(${deg} 58 56)`}
          />
        ))}
      </g>

      {/* Cloud */}
      <g style={{ opacity: Math.max(on('condensation'), on('precipitation')), transition: 'opacity 400ms' }}>
        <g className={playing && active === 'condensation' ? 'animate-float' : undefined}>
          <rect x="196" y="36" width="128" height="40" rx="20" fill="#fff" stroke="#080808" strokeWidth="2" />
          <circle cx="232" cy="38" r="20" fill="#fff" stroke="#080808" strokeWidth="2" />
          <circle cx="272" cy="32" r="24" fill="#fff" stroke="#080808" strokeWidth="2" />
          <rect x="198" y="46" width="124" height="28" rx="14" fill="#fff" />
        </g>
      </g>

      {/* Rain drops */}
      <g style={{ opacity: on('precipitation'), transition: 'opacity 400ms' }}>
        {[222, 248, 274, 300].map((x, i) => (
          <rect
            key={x}
            x={x}
            y="88"
            width="5"
            height="14"
            rx="2.5"
            fill="#3474E5"
            className={playing && active === 'precipitation' ? 'animate-drop' : undefined}
            style={{ animationDelay: `${i * 220}ms` }}
          />
        ))}
      </g>

      {/* Mountain */}
      <polygon points="250,200 320,110 392,200" fill="#2EAC43" stroke="#080808" strokeWidth="2" strokeLinejoin="round" />
      <polygon points="320,110 304,131 312,128 320,136 328,128 336,131" fill="#fff" stroke="#080808" strokeWidth="1.5" />

      {/* River */}
      <path
        d="M330 200 C 300 170, 270 210, 220 196"
        fill="none"
        stroke="#3474E5"
        strokeWidth="7"
        strokeLinecap="round"
        style={{ opacity: on('collection'), transition: 'opacity 400ms' }}
      />

      {/* Sea */}
      <rect x="0" y="184" width="250" height="46" fill="#3474E5" stroke="#080808" strokeWidth="2" />
      <path d="M10 200 q10 -6 20 0 t20 0 t20 0" fill="none" stroke="#fff" strokeWidth="2" />
      <path d="M120 212 q10 -6 20 0 t20 0 t20 0" fill="none" stroke="#fff" strokeWidth="2" />
      <rect x="250" y="200" width="150" height="30" fill="#FF650B" stroke="#080808" strokeWidth="2" />

      {/* Evaporation arrows */}
      <g
        style={{ opacity: on('evaporation'), transition: 'opacity 400ms' }}
        stroke="#080808"
        strokeWidth="2.5"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {[110, 150].map((x) => (
          <g key={x} className={playing && active === 'evaporation' ? 'animate-float' : undefined}>
            <path d={`M${x} 170 C ${x - 10} 150, ${x + 10} 130, ${x} 110`} strokeDasharray="4 6" />
            <path d={`M${x - 7} 118 L${x} 108 L${x + 7} 118`} />
          </g>
        ))}
      </g>

      {/* Cycle arrow from sea to cloud */}
      <path
        d="M168 104 Q 180 60, 190 58"
        fill="none"
        stroke="#A94CF5"
        strokeWidth="3"
        strokeLinecap="round"
        style={{ opacity: on('condensation'), transition: 'opacity 400ms' }}
      />
    </svg>
  )
}
