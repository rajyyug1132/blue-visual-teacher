// Showcase mode: the UI is served from a public host (the Vercel preview) and no backend is configured.
// The lesson pipeline is offline-only by design (AGENTS.md [ENFORCE]), so there is nothing to call there.
// lib/api.ts short-circuits every request in this mode instead of letting it time out against <host>:8000.

export const REPO_URL = 'https://github.com/rajyyug1132/blue-visual-teacher'

export const SHOWCASE_MESSAGE =
  'This is a preview of the interface. Lessons, accounts and history live on the lesson server, which runs offline on your own machine.'

const FLAG = 'bvt-showcase'
const LOCAL_HOST =
  /^(localhost|127(\.\d{1,3}){3}|\[?::1\]?|10(\.\d{1,3}){3}|192\.168(\.\d{1,3}){2}|172\.(1[6-9]|2\d|3[01])(\.\d{1,3}){2})$/

/** True on a public host with no NEXT_PUBLIC_API_BASE_URL. `?showcase=1` forces it on a local host for testing; `?showcase=0` clears it. */
export function isShowcase(): boolean {
  if (typeof window === 'undefined') return false
  try {
    const q = new URLSearchParams(window.location.search).get('showcase')
    if (q === '1') window.sessionStorage.setItem(FLAG, '1')
    if (q === '0') window.sessionStorage.removeItem(FLAG)
    if (window.sessionStorage.getItem(FLAG) === '1') return true
  } catch {
    // storage can be unavailable (privacy mode); fall through to host detection
  }
  if (process.env.NEXT_PUBLIC_API_BASE_URL) return false
  const host = window.location.hostname
  return !(LOCAL_HOST.test(host) || host.endsWith('.localhost'))
}
