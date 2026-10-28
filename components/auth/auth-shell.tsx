import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { Wordmark } from '@/components/site/wordmark'

export function AuthShell({ children, mode = 'login' }: { children: React.ReactNode; mode?: 'signup' | 'login' }) {
  const isSignup = mode === 'signup'

  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <aside
        aria-hidden="true"
        className="relative hidden overflow-hidden border-r-2 border-ink bg-brand-blue text-white lg:flex lg:flex-col lg:justify-between"
      >
        <div className="absolute inset-0 bg-grid opacity-30 [--grid-size:64px]" />

        {isSignup ? (
          <span className="absolute left-[65px] top-[1px] size-[63px] bg-brand-purple" />
        ) : (
          <>
            <span className="absolute left-[257px] top-[65px] size-[63px] bg-brand-yellow" />
            <span className="absolute left-[385px] top-[257px] size-[63px] bg-brand-orange" />
            <span className="absolute left-[65px] top-[385px] size-[63px] bg-brand-purple" />
          </>
        )}

        <div className="relative p-10" />
        <div className="relative p-10 md:p-14">
          <p className="font-display text-[5.5rem] font-black leading-[0.85] tracking-[-0.05em] text-balance">
            See it.
            <br />
            Hear it.
            <br />
            <span className="text-ink">Get it.</span>
          </p>
          <p className="mt-6 max-w-sm text-lg font-medium text-white/90">
            Visual, narrated lessons in English, हिंदी and ಕನ್ನಡ.
          </p>
        </div>
      </aside>

      <div className="flex min-h-dvh flex-col justify-center bg-cream px-6 py-10 md:px-16">
        <div className="mx-auto w-full max-w-md">{children}</div>
      </div>
    </div>
  )
}

export function safeNext(value: string | string[] | undefined, fallback = '/dashboard') {
  const v = Array.isArray(value) ? value[0] : value
  if (!v || !v.startsWith('/') || v.startsWith('//')) return fallback
  return v
}
