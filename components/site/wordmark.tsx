import Link from 'next/link'
import { cn } from '@/lib/utils'

export function Wordmark({ className, href = '/' }: { className?: string; href?: string }) {
  return (
    <Link
      href={href}
      className={cn('group inline-flex flex-col leading-none rounded-md', className)}
      aria-label="Blue Visual Teacher home"
    >
      <span className="flex items-end font-display text-2xl font-black tracking-tighter md:text-[1.75rem]">
        blue
        <span aria-hidden="true" className="mb-1 ml-0.5 size-2.5 bg-brand-blue transition-transform group-hover:rotate-45" />
      </span>
      <span className="mt-1 text-[0.6rem] font-semibold uppercase tracking-[0.2em]">Visual Teacher</span>
    </Link>
  )
}
