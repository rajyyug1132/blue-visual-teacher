'use client'

import Link from 'next/link'
import { useState } from 'react'
import { ArrowUpRight, Menu, X } from 'lucide-react'
import { Wordmark } from './wordmark'
import { useDemoSession } from '@/lib/demo-session'

const LINKS = [
  { href: '/#product', label: 'Product' },
  { href: '/#how-it-works', label: 'How it works' },
  { href: '/#languages', label: 'Languages' },
]

export function Navbar() {
  const [open, setOpen] = useState(false)
  const session = useDemoSession()

  return (
    <header className="sticky top-0 z-40 border-b border-ink bg-cream/95 backdrop-blur-sm">
      <nav aria-label="Main" className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 md:h-20 md:px-6">
        <Wordmark />

        <ul className="hidden items-center gap-1 md:flex">
          {LINKS.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="rounded-full px-4 py-2 text-sm font-semibold transition-colors hover:bg-ink hover:text-cream"
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>

        <div className="hidden items-center gap-2 md:flex">
          {session ? (
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-full bg-brand-blue px-5 py-2.5 text-sm font-bold text-white transition-transform hover:-translate-y-0.5"
            >
              Dashboard
              <ArrowUpRight className="size-4" aria-hidden="true" />
            </Link>
          ) : (
            <>
              <Link href="/login" className="rounded-full px-4 py-2.5 text-sm font-semibold hover:underline">
                Log in
              </Link>
              <Link
                href="/signup"
                className="inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm font-bold text-cream transition-transform hover:-translate-y-0.5"
              >
                Get started
                <ArrowUpRight className="size-4" aria-hidden="true" />
              </Link>
            </>
          )}
        </div>

        <button
          type="button"
          className="inline-flex size-11 items-center justify-center rounded-xl border border-ink md:hidden"
          aria-expanded={open}
          aria-controls="mobile-menu"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="size-5" aria-hidden="true" /> : <Menu className="size-5" aria-hidden="true" />}
          <span className="sr-only">{open ? 'Close menu' : 'Open menu'}</span>
        </button>
      </nav>

      {open && (
        <div id="mobile-menu" className="border-t border-ink bg-cream px-4 pb-6 pt-2 md:hidden">
          <ul className="flex flex-col">
            {LINKS.map((link) => (
              <li key={link.href} className="border-b border-ink/15">
                <Link
                  href={link.href}
                  onClick={() => setOpen(false)}
                  className="block py-4 font-display text-2xl font-extrabold tracking-tight"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="mt-6 grid grid-cols-2 gap-3">
            {session ? (
              <Link
                href="/dashboard"
                className="col-span-2 rounded-2xl bg-brand-blue px-5 py-4 text-center font-bold text-white"
              >
                Go to dashboard
              </Link>
            ) : (
              <>
                <Link href="/login" className="rounded-2xl border border-ink px-5 py-4 text-center font-bold">
                  Log in
                </Link>
                <Link href="/signup" className="rounded-2xl bg-ink px-5 py-4 text-center font-bold text-cream">
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
