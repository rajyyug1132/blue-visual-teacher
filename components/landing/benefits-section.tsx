import { ArrowUpRight, Download, Eye, Globe2, Mic } from 'lucide-react'
import { StartLink } from '@/components/site/start-link'

const BENEFITS = [
  { icon: Eye, title: 'Visual-first explanations', body: 'Diagrams, labels and step-by-step scenes do the heavy lifting.' },
  { icon: Mic, title: 'Narrated learning', body: 'Listen along as each step is explained in plain, calm language.' },
  { icon: Globe2, title: 'Multilingual accessibility', body: 'Lessons designed for English, Hindi and Kannada learners.' },
  { icon: Download, title: 'Downloadable video lessons', body: 'Save the MP4 for offline revision whenever export succeeds.' },
]

export function BenefitsSection() {
  return (
    <section aria-labelledby="benefits-heading" className="border-b border-ink bg-ink text-cream">
      <div className="mx-auto max-w-7xl px-4 py-16 md:px-6 md:py-24">
        <h2 id="benefits-heading" className="font-display text-5xl font-black leading-[0.9] tracking-tighter md:text-7xl">
          Built for <span className="text-brand-yellow">clarity.</span>
        </h2>
        <ul className="mt-12 grid border-l border-t border-cream/30 sm:grid-cols-2 lg:grid-cols-4">
          {BENEFITS.map((b) => (
            <li key={b.title} className="flex min-h-56 flex-col justify-between gap-8 border-b border-r border-cream/30 p-6">
              <b.icon className="size-8 text-brand-yellow" aria-hidden="true" />
              <div>
                <h3 className="font-display text-xl font-extrabold tracking-tight">{b.title}</h3>
                <p className="mt-2 text-pretty text-sm leading-relaxed text-cream/75">{b.body}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

export function FinalCta() {
  return (
    <section aria-labelledby="cta-heading" className="relative overflow-hidden border-b border-ink">
      <div aria-hidden="true" className="absolute inset-0 bg-grid [--grid-size:48px] md:[--grid-size:64px]" />
      <div className="relative mx-auto max-w-7xl px-4 py-20 md:px-6 md:py-28">
        <div className="rounded-[2rem] border-2 border-ink bg-brand-yellow p-8 md:p-14">
          <h2
            id="cta-heading"
            className="max-w-4xl font-display text-4xl font-black leading-[0.92] tracking-tighter text-balance md:text-7xl"
          >
            {'Your next \u201CI get it now\u201D moment starts here.'}
          </h2>
          <StartLink className="group mt-10 inline-flex items-center gap-3 rounded-full bg-ink px-8 py-4 font-bold text-cream transition-transform hover:-translate-y-0.5">
            Create a lesson
            <span className="inline-flex size-7 items-center justify-center rounded-full bg-brand-yellow text-ink transition-transform group-hover:rotate-45">
              <ArrowUpRight className="size-4" aria-hidden="true" />
            </span>
          </StartLink>
        </div>
      </div>
    </section>
  )
}
