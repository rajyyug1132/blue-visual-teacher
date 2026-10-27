import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import { LessonPreview } from './lesson-preview'
import { StartLink } from '@/components/site/start-link'

const BLOCKS = [
  { col: 9, row: 1, color: 'bg-brand-purple', className: 'hidden lg:block' },
  { col: 0, row: 3, color: 'bg-brand-blue', className: 'hidden md:block' },
  { col: 19, row: 4, color: 'bg-brand-yellow', className: 'hidden xl:block' },
  { col: 7, row: 8, color: 'bg-brand-orange', className: 'hidden lg:block' },
  { col: 8, row: 9, color: 'bg-brand-green', className: 'hidden lg:block' },
]

export function HeroSection() {
  return (
    <section id="product" aria-labelledby="hero-heading" className="relative overflow-hidden border-b border-ink">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-grid [--grid-size:48px] md:[--grid-size:64px]">
        {BLOCKS.map((b) => (
          <span
            key={`${b.col}-${b.row}`}
            className={`absolute ${b.color} ${b.className}`}
            style={{ left: `${b.col * 64 + 1}px`, top: `${b.row * 64 + 1}px`, width: 63, height: 63 }}
          />
        ))}
      </div>

      <div className="relative mx-auto grid max-w-7xl items-center gap-10 px-4 py-12 md:px-6 md:py-20 lg:grid-cols-[1.05fr_1fr] lg:gap-14">
        <div>
          <p className="inline-block rounded-full border border-ink bg-brand-yellow px-4 py-1.5 text-xs font-bold uppercase tracking-[0.2em]">
            Learning, reimagined.
          </p>
          <h1
            id="hero-heading"
            className="mt-6 font-display text-[3.4rem] font-black leading-[0.86] tracking-[-0.045em] text-balance sm:text-7xl lg:text-[6.5rem]"
          >
            Big ideas.
            <br />
            <span className="relative inline-block">
              Made visual
              <span aria-hidden="true" className="text-brand-blue">
                .
              </span>
            </span>
          </h1>

          <div className="mt-8 max-w-md rounded-2xl border border-ink bg-cream p-5">
            <p className="text-pretty text-lg leading-relaxed">
              Turn any lesson topic into a visual learning experience with narration in your language.
            </p>
            <ul className="mt-4 flex flex-wrap gap-2" aria-label="Primary languages">
              {['English', 'हिंदी', 'ಕನ್ನಡ'].map((l) => (
                <li key={l} className="rounded-full border border-ink bg-white px-3 py-1 text-sm font-semibold">
                  {l}
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <StartLink className="group inline-flex items-center justify-center gap-3 rounded-full bg-brand-blue px-7 py-4 font-bold text-white transition-transform hover:-translate-y-0.5">
              Create your first lesson
              <span className="inline-flex size-7 items-center justify-center rounded-full bg-white text-ink transition-transform group-hover:rotate-45">
                <ArrowUpRight className="size-4" aria-hidden="true" />
              </span>
            </StartLink>
            <Link
              href="#preview"
              className="inline-flex items-center justify-center rounded-full border-2 border-ink bg-cream px-7 py-4 font-bold transition-colors hover:bg-ink hover:text-cream"
            >
              Explore the preview
            </Link>
          </div>
        </div>

        <div id="preview" className="scroll-mt-28">
          <LessonPreview />
        </div>
      </div>
    </section>
  )
}
