'use client'

import { useSyncExternalStore } from 'react'

/**
 * DEMO-ONLY session. No authentication backend exists in this project.
 * We keep only a display name and email in sessionStorage so the demo can
 * navigate between pages. Passwords are never stored. This is NOT secure
 * authentication and must be replaced with a real provider before launch.
 */

export type DemoSession = { name: string; email: string; createdAt: number }

const KEY = 'bvt-demo-session'
const EVENT = 'bvt-demo-session-change'

let cachedRaw: string | null | undefined
let cachedValue: DemoSession | null = null

function read(): DemoSession | null {
  const raw = window.sessionStorage.getItem(KEY)
  if (raw === cachedRaw) return cachedValue
  cachedRaw = raw
  try {
    cachedValue = raw ? (JSON.parse(raw) as DemoSession) : null
  } catch {
    cachedValue = null
  }
  return cachedValue
}

function subscribe(callback: () => void) {
  window.addEventListener(EVENT, callback)
  window.addEventListener('storage', callback)
  return () => {
    window.removeEventListener(EVENT, callback)
    window.removeEventListener('storage', callback)
  }
}

export function startDemoSession(input: { name: string; email: string }) {
  const session: DemoSession = { name: input.name, email: input.email, createdAt: Date.now() }
  window.sessionStorage.setItem(KEY, JSON.stringify(session))
  window.dispatchEvent(new Event(EVENT))
}

export function endDemoSession() {
  window.sessionStorage.removeItem(KEY)
  window.dispatchEvent(new Event(EVENT))
}

/** Returns `undefined` during SSR/hydration, then the session or null. */
export function useDemoSession(): DemoSession | null | undefined {
  return useSyncExternalStore(subscribe, read, () => undefined)
}
