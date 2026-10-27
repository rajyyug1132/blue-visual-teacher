'use client'

import Link from 'next/link'
import type { ComponentProps } from 'react'
import { useDemoSession } from '@/lib/demo-session'

/** Routes to /create when a (demo) session exists, otherwise to sign-up with a return path. */
export function StartLink({ topic, ...props }: Omit<ComponentProps<typeof Link>, 'href'> & { topic?: string }) {
  const session = useDemoSession()
  const createPath = topic ? `/create?topic=${encodeURIComponent(topic)}` : '/create'
  const href = session ? createPath : `/signup?next=${encodeURIComponent(createPath)}`
  return <Link href={href} {...props} />
}
