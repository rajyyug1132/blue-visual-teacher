import { ArrowUpRight } from 'lucide-react'
import { StartLink } from '@/components/site/start-link'

const EXAMPLES = [
  {
    topic: 'Photosynthesis',
    tag: 'Biology',
    blurb: 'How plants turn sunlight, water and air into food.',
    bg: 'bg-brand-green',
    art: <PhotosynthesisArt />,
  },
  {
    topic: 'Binary search',
    tag: 'Computer science',
    blurb: 'Why halving a sorted list beats checking every item.',
    bg: 'bg-brand-purple',
    art: <BinarySearchArt />,
  },
  {
    topic: 'The water cycle',
    tag: 'Earth science',
    blurb: 'Evaporation, condensation, rain and back again.',
    bg: 'bg-brand-blue',
    art: <WaterArt />,
  },
]

export function ExampleLessons() {
  return (
    <section id="examples" aria-labelledby="examples-heading" className="scroll-mt-20 border-b border-ink bg-white">
      <div className="mx-auto max-w-7xl px-4 py-16 md:px-6 md:py-24">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <h2 id="examples-heading" className="font-display text-5xl font-black leading-[0.9] tracking-tighter md:text-7xl">
            Start with
            <br />
            an example.
          </h2>
          <p className="max-w-sm text-pretty text-muted-foreground">
            Pick a card to drop its topic straight into the lesson creator.
          </p>
        </div>

        <ul className="mt-12 grid gap-5 md:grid-cols-3">
          {EXAMPLES.map((ex) => (
            <li key={ex.topic}>
              <StartLink
                topic={ex.topic}
                className="group flex h-full flex-col overflow-hidden rounded-3xl border-2 border-ink bg-cream transition-all hover:-translate-y-1 hover:shadow-[6px_6px_0_0_#080808]"
              >
                <div className={`relative aspect-[4/3] border-b-2 border-ink ${ex.bg}`}>{ex.art}</div>
                <div className="flex flex-1 flex-col gap-3 p-5">
                  <span className="w-fit rounded-full border border-ink px-3 py-0.5 text-xs font-bold uppercase tracking-wider">
                    {ex.tag}
                  </span>
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-display text-2xl font-extrabold tracking-tight">{ex.topic}</h3>
                    <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-full bg-ink text-cream transition-transform group-hover:rotate-45">
                      <ArrowUpRight className="size-4" aria-hidden="true" />
                    </span>
                  </div>
                  <p className="text-pretty text-sm leading-relaxed text-muted-foreground">{ex.blurb}</p>
                </div>
              </StartLink>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

function PhotosynthesisArt() {
  return (
    <svg viewBox="0 0 200 150" className="absolute inset-0 size-full" aria-hidden="true">
      <circle cx="160" cy="34" r="20" fill="#FFB90B" stroke="#080808" strokeWidth="2" />
      <path d="M140 46 L110 70 M146 54 L118 80" stroke="#080808" strokeWidth="2" strokeDasharray="4 4" />
      <rect x="0" y="122" width="200" height="28" fill="#FF650B" stroke="#080808" strokeWidth="2" />
      <path d="M90 122 L90 70" stroke="#080808" strokeWidth="3" />
      <path d="M90 92 C 60 92, 52 70, 56 58 C 76 58, 90 72, 90 92 Z" fill="#F4EAE1" stroke="#080808" strokeWidth="2" />
      <path d="M90 80 C 116 80, 126 60, 122 48 C 102 48, 90 62, 90 80 Z" fill="#F4EAE1" stroke="#080808" strokeWidth="2" />
      <text x="22" y="40" fontSize="14" fontWeight="800" fill="#080808">
        CO₂
      </text>
      <text x="22" y="62" fontSize="14" fontWeight="800" fill="#080808">
        H₂O
      </text>
      <text x="132" y="108" fontSize="14" fontWeight="800" fill="#080808">
        O₂
      </text>
    </svg>
  )
}

function BinarySearchArt() {
  const cells = [3, 8, 12, 19, 24, 31, 37, 42]
  return (
    <svg viewBox="0 0 200 150" className="absolute inset-0 size-full" aria-hidden="true">
      {cells.map((n, i) => {
        const x = 12 + i * 22
        const dim = i < 4
        const mid = i === 5
        return (
          <g key={n}>
            <rect
              x={x}
              y="62"
              width="20"
              height="26"
              fill={mid ? '#FFB90B' : dim ? '#A94CF5' : '#F4EAE1'}
              stroke="#080808"
              strokeWidth="2"
              opacity={dim ? 0.55 : 1}
            />
            <text x={x + 10} y="80" fontSize="10" fontWeight="800" textAnchor="middle" fill="#080808">
              {n}
            </text>
          </g>
        )
      })}
      <path d="M133 40 L133 56 M127 50 L133 57 L139 50" stroke="#080808" strokeWidth="2.5" fill="none" />
      <text x="133" y="34" fontSize="11" fontWeight="800" textAnchor="middle" fill="#080808">
        mid
      </text>
      <path d="M12 104 L188 104" stroke="#080808" strokeWidth="2" />
      <path d="M12 98 L12 110 M100 98 L100 110 M188 98 L188 110" stroke="#080808" strokeWidth="2" />
      <text x="100" y="128" fontSize="11" fontWeight="700" textAnchor="middle" fill="#080808">
        n → n/2 → n/4
      </text>
    </svg>
  )
}

function WaterArt() {
  return (
    <svg viewBox="0 0 200 150" className="absolute inset-0 size-full" aria-hidden="true">
      <circle cx="100" cy="74" r="48" fill="none" stroke="#F4EAE1" strokeWidth="3" strokeDasharray="10 8" />
      <path d="M146 64 L150 76 L140 72" stroke="#F4EAE1" strokeWidth="3" fill="none" />
      <path d="M54 84 L50 72 L60 76" stroke="#F4EAE1" strokeWidth="3" fill="none" />
      <rect x="76" y="20" width="56" height="22" rx="11" fill="#fff" stroke="#080808" strokeWidth="2" />
      <path d="M100 58 C 88 76, 88 90, 100 92 C 112 90, 112 76, 100 58 Z" fill="#FFB90B" stroke="#080808" strokeWidth="2" />
      <rect x="0" y="126" width="200" height="24" fill="#080808" />
      <path d="M10 138 q10 -6 20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0" fill="none" stroke="#3474E5" strokeWidth="2" />
    </svg>
  )
}
