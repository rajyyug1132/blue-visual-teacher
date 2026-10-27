import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import { LessonPreview } from './lesson-preview'
import { StartLink } from '@/components/site/start-link'

const BLOCKS = [
  { col: 11, row: 0, color: 'bg-brand-purple', className: 'hidden lg:block', h: 16 },
  { col: 0, row: 3, color: 'bg-brand-blue', className: 'hidden md:block' },
  { col: 9, row: 10, color: 'bg-brand-orange', className: 'hidden lg:block' },
  { col: 10, row: 11, color: 'bg-brand-green', className: 'hidden lg:block' },
]

export function HeroSection() {
  return (
    <section id="product" aria-labelledby="hero-heading" className="relative overflow-hidden border-b border-ink">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-grid [--grid-size:48px] md:[--grid-size:64px]">
        {BLOCKS.map((b) => (
          <span
            key={`${b.col}-${b.row}`}
            className={`absolute ${b.color} ${b.className}`}
            style={{ left: `${b.col * 64 + 1}px`, top: `${b.row * 64 + 1}px`, width: 63, height: b.h ?? 63 }}
          />
        ))}
      </div>

      <div className="relative mx-auto grid max-w-7xl items-center gap-10 px-4 py-8 md:px-6 md:py-14 lg:grid-cols-[1.05fr_1fr] lg:gap-14">
        <div>
          <h1
            id="hero-heading"
            className="font-display text-[3.4rem] font-black leading-[0.86] tracking-[-0.045em] text-balance sm:text-7xl lg:text-[6.5rem]"
          >
            Big ideas.
            <br />
            Made
            <br />
            <span className="relative inline-block">
              visual.
              <span
                aria-hidden="true"
                className="absolute bottom-2 -right-8 size-6 bg-brand-blue"
              />
            </span>
          </h1>

          <div className="mt-8 max-w-md rounded-3xl border border-ink bg-cream p-6">
            <p className="text-pretty text-lg leading-relaxed font-medium">
              Turn any lesson topic into a visual learning experience with narration in your language.
            </p>
            <ul className="mt-4 flex flex-wrap gap-2" aria-label="Primary languages">
              {['English', 'हिंदी', 'ಕನ್ನಡ'].map((l) => (
                <li key={l} className="rounded-full border border-ink bg-white px-3.5 py-1 text-sm font-semibold">
                  {l}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div id="preview" className="scroll-mt-28">
          <LessonPreview />
        </div>
      </div>
    </section>
  )
}
