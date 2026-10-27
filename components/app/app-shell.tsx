'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { FlaskConical, Loader2, LogOut } from 'lucide-react'
import { Wordmark } from '@/components/site/wordmark'
import { endDemoSession, useDemoSession, type DemoSession } from '@/lib/demo-session'
import { cn } from '@/lib/utils'

const NAV = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/create', label: 'Create' },
]

export function AppShell({ children, next }: { children: (session: DemoSession) => React.ReactNode; next: string }) {
  const session = useDemoSession()
  const pathname = usePathname()
  const router = useRouter()

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-30 border-b border-ink bg-cream/95 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 md:px-6">
          <Wordmark href={session ? '/dashboard' : '/'} />
          {session && (
            <nav aria-label="App" className="flex items-center gap-1">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={pathname === item.href ? 'page' : undefined}
                  className={cn(
                    'rounded-full px-3 py-2 text-sm font-semibold transition-colors sm:px-4',
                    pathname === item.href ? 'bg-ink text-cream' : 'hover:bg-ink/10',
                  )}
                >
                  {item.label}
                </Link>
              ))}
              <button
                type="button"
                onClick={() => {
                  endDemoSession()
                  router.push('/')
                }}
                className="ml-1 inline-flex size-10 items-center justify-center rounded-full border border-ink hover:bg-ink hover:text-cream"
              >
                <LogOut className="size-4" aria-hidden="true" />
                <span className="sr-only">Sign out</span>
              </button>
            </nav>
          )}
        </div>
        {session && !session.token && (
          <div className="border-t border-ink/20 bg-brand-yellow/70">
            <p className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-1.5 text-xs font-semibold md:px-6">
              <FlaskConical className="size-3.5 shrink-0" aria-hidden="true" />
              Local demo session for {session.email}. Sign in to save lessons to your account.
            </p>
          </div>
        )}
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 md:px-6 md:py-12">
        {session === undefined ? (
          <div className="flex items-center gap-2 py-20 text-muted-foreground" role="status">
            <Loader2 className="size-5 animate-spin" aria-hidden="true" />
            Loading…
          </div>
        ) : session === null && pathname === '/dashboard' ? (
          <SignedOut next={next} />
        ) : (
          children(session ?? { id: 'guest', name: 'Learner', email: 'guest@accord.dev', token: '', createdAt: Date.now() })
        )}
      </main>
    </div>
  )
}

function SignedOut({ next }: { next: string }) {
  const q = `?next=${encodeURIComponent(next)}`
  return (
    <div className="mx-auto max-w-lg rounded-3xl border-2 border-ink bg-white p-8 text-center">
      <h1 className="font-display text-4xl font-black tracking-tighter">Sign in to continue.</h1>
      <p className="mt-3 text-muted-foreground">Start a demo session to create and track lessons.</p>
      <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
        <Link href={`/signup${q}`} className="rounded-full bg-brand-blue px-6 py-3 font-bold text-white">
          Sign up
        </Link>
        <Link href={`/login${q}`} className="rounded-full border-2 border-ink px-6 py-3 font-bold">
          Log in
        </Link>
      </div>
    </div>
  )
}
