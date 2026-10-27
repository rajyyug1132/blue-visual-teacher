'use client'

import { useSyncExternalStore } from 'react'

export type UserSession = {
  id: string
  name: string
  email: string
  token: string
  createdAt: number
}

const KEY = 'bvt-auth-session'
const EVENT = 'bvt-auth-session-change'

let cachedRaw: string | null | undefined
let cachedValue: UserSession | null = null

function read(): UserSession | null {
  if (typeof window === 'undefined') return null
  const raw = window.localStorage.getItem(KEY) || window.sessionStorage.getItem(KEY)
  if (raw === cachedRaw) return cachedValue
  cachedRaw = raw
  try {
    cachedValue = raw ? (JSON.parse(raw) as UserSession) : null
  } catch {
    cachedValue = null
  }
  return cachedValue
}

function subscribe(callback: () => void) {
  if (typeof window === 'undefined') return () => {}
  window.addEventListener(EVENT, callback)
  window.addEventListener('storage', callback)
  return () => {
    window.removeEventListener(EVENT, callback)
    window.removeEventListener('storage', callback)
  }
}

export function saveUserSession(session: UserSession) {
  if (typeof window === 'undefined') return
  const raw = JSON.stringify(session)
  window.localStorage.setItem(KEY, raw)
  window.sessionStorage.setItem(KEY, raw)
  window.dispatchEvent(new Event(EVENT))
}

export function clearUserSession() {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(KEY)
  window.sessionStorage.removeItem(KEY)
  window.dispatchEvent(new Event(EVENT))
}

export function getAuthToken(): string | null {
  const s = read()
  return s ? s.token : null
}

/** Returns `undefined` during SSR/hydration, then the authenticated user session or null. */
export function useUserSession(): UserSession | null | undefined {
  return useSyncExternalStore(subscribe, read, () => undefined)
}

// Backwards-compatible aliases for existing components
export type DemoSession = UserSession
export const useDemoSession = useUserSession
export const endDemoSession = clearUserSession
export function startDemoSession(input: { name: string; email: string }) {
  saveUserSession({
    id: 'local-session',
    name: input.name,
    email: input.email,
    token: '',
    createdAt: Date.now()
  })
}
