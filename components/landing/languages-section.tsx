const LANGS = [
  { native: 'English', name: 'English', sample: 'Plants make food from sunlight.', color: 'bg-brand-blue text-white', lang: 'en' },
  { native: 'हिंदी', name: 'Hindi', sample: 'पौधे सूरज की रोशनी से भोजन बनाते हैं।', color: 'bg-brand-yellow text-ink', lang: 'hi' },
  { native: 'ಕನ್ನಡ', name: 'Kannada', sample: 'ಸಸ್ಯಗಳು ಸೂರ್ಯನ ಬೆಳಕಿನಿಂದ ಆಹಾರ ತಯಾರಿಸುತ್ತವೆ.', color: 'bg-brand-orange text-ink', lang: 'kn' },
]

export function LanguagesSection() {
  return (
    <section id="languages" aria-labelledby="languages-heading" className="scroll-mt-20 border-b border-ink">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-16 md:px-6 md:py-24 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <h2
            id="languages-heading"
            className="font-display text-5xl font-black leading-[0.9] tracking-tighter text-balance md:text-7xl"
          >
            Learn in your language.
          </h2>
          <p className="mt-6 max-w-md text-pretty text-lg leading-relaxed text-muted-foreground">
            Understanding comes faster in the language you think in. Narration and captions are designed for English,
            Hindi and Kannada.
          </p>
        </div>

        <ul className="grid gap-4">
          {LANGS.map((l) => (
            <li
              key={l.name}
              className={`flex flex-col gap-4 rounded-3xl border-2 border-ink p-6 sm:flex-row sm:items-center sm:justify-between ${l.color}`}
            >
              <div>
                <p lang={l.lang} className="font-display text-4xl font-black tracking-tight md:text-5xl">
                  {l.native}
                </p>
                <p className="mt-1 text-sm font-bold uppercase tracking-[0.2em] opacity-80">{l.name}</p>
              </div>
              <p
                lang={l.lang}
                className="max-w-xs rounded-2xl border border-ink bg-cream px-4 py-3 text-sm font-medium text-ink"
              >
                {l.sample}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
