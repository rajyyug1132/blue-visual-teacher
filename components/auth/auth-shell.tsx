import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { Wordmark } from '@/components/site/wordmark'

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <aside
        aria-hidden="true"
        className="relative hidden overflow-hidden border-r-2 border-ink bg-brand-blue text-white lg:flex lg:flex-col lg:justify-between"
      >
        <div className="absolute inset-0 bg-grid opacity-40 [--grid-size:64px]" />
        <span className="absolute left-[257px] top-[193px] size-[63px] bg-brand-yellow" />
        <span className="absolute left-[385px] top-[385px] size-[63px] bg-brand-orange" />
        <span className="absolute left-[65px] top-[449px] size-[63px] bg-brand-purple" />
        <div className="relative p-10" />
        <div className="relative p-10">
          <p className="font-display text-[5.5rem] font-black leading-[0.85] tracking-[-0.05em] text-balance">
            See it.
            <br />
            Hear it.
            <br />
            <span className="text-ink">Get it.</span>
          </p>
          <p className="mt-6 max-w-sm text-lg text-white/85">Visual, narrated lessons in English, हिंदी and ಕನ್ನಡ.</p>
        </div>
      </aside>

      <div className="flex flex-col">
        <header className="flex items-center justify-between border-b border-ink px-4 py-4 md:px-8">
          <Wordmark />
          <Link href="/" className="inline-flex items-center gap-2 text-sm font-semibold hover:underline">
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to home
          </Link>
        </header>
        <main className="flex flex-1 items-center justify-center px-4 py-10 md:px-8">{children}</main>
      </div>
    </div>
  )
}

export function safeNext(value: string | string[] | undefined, fallback = '/dashboard') {
  const v = Array.isArray(value) ? value[0] : value
  if (!v || !v.startsWith('/') || v.startsWith('//')) return fallback
  return v
}
