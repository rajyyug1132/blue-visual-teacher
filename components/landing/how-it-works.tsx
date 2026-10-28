import { Languages, PlayCircle, Type } from 'lucide-react'

const STEPS = [
  {
    n: '01',
    title: 'Choose a topic',
    body: 'Type anything you want to understand, from photosynthesis to database normalization.',
    color: 'bg-brand-blue text-white',
    icon: Type,
  },
  {
    n: '02',
    title: 'Select your language',
    body: 'Pick English, Hindi or Kannada for narration and on-screen captions.',
    color: 'bg-brand-yellow text-ink',
    icon: Languages,
  },
  {
    n: '03',
    title: 'Learn through visuals and narration',
    body: 'Follow a step-by-step visual explanation and download the video when export succeeds.',
    color: 'bg-brand-orange text-ink',
    icon: PlayCircle,
  },
]

export function HowItWorks() {
  return (
    <section id="how-it-works" aria-labelledby="how-heading" className="scroll-mt-20 border-b border-ink">
      <div className="mx-auto max-w-7xl px-4 py-16 md:px-6 md:py-24">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <h2 id="how-heading" className="font-display text-5xl font-black leading-[0.9] tracking-tighter md:text-7xl">
            How it works
          </h2>
          <p className="max-w-sm text-pretty text-muted-foreground">
            Three steps from {'"I don\u2019t get it"'} to a lesson you can watch, replay and share.
          </p>
        </div>

        <ol className="mt-12 grid gap-4 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <li
              key={step.n}
              className={`group relative flex min-h-72 flex-col justify-between overflow-hidden rounded-3xl border-2 border-ink p-6 transition-transform hover:-translate-y-1 ${step.color} ${i === 1 ? 'md:translate-y-8 md:hover:translate-y-7' : ''}`}
            >
              <div className="flex items-start justify-between">
                <span className="font-display text-7xl font-black leading-none tracking-tighter">{step.n}</span>
                <step.icon className="size-7" aria-hidden="true" />
              </div>
              <div>
                <h3 className="font-display text-2xl font-extrabold leading-tight tracking-tight">{step.title}</h3>
                <p className="mt-2 text-pretty leading-relaxed opacity-90">{step.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
