// Showcase mode: the UI is served from a public host (the Vercel preview) and no backend is configured.
// The lesson pipeline is offline-only by design (AGENTS.md [ENFORCE]), so there is nothing to call there.
// lib/api.ts short-circuits every request in this mode instead of letting it time out against <host>:8000.
//
// A few real, pre-made lessons ship as static files in public/demo/<slug>_<lang>/ so a visitor can still
// press play in the shop window. They are generated offline and committed once; nothing is computed in the cloud.

export const REPO_URL = 'https://github.com/rajyyug1132/blue-visual-teacher'

export const SHOWCASE_MESSAGE =
  'This is a preview of the interface. Lessons, accounts and history live on the lesson server, which runs offline on your own machine.'

/** Pre-made lessons available in the shop window. Keys are topic slugs (same rule as exporter.app.topic_slug). */
export const DEMO_LESSONS: Record<string, { topic: string; langs: string[] }> = {
  'ohm-s-law': { topic: "Ohm's Law", langs: ['en', 'hi', 'kn'] },
  'binary-search': { topic: 'Binary search', langs: ['en', 'hi', 'kn'] },
  photosynthesis: { topic: 'Photosynthesis', langs: ['en', 'hi', 'kn'] },
}

export const DEMO_SLUGS = Object.keys(DEMO_LESSONS)

/** Same slug rule as exporter.app.topic_slug / orchestrator.cache.topic_slug. */
export function slugify(topic: string): string {
  return topic.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'untitled'
}

/** The demo lesson for a topic, when one exists in the requested language. */
export function demoFor(topic: string, language?: string | null) {
  const slug = slugify(topic)
  const demo = DEMO_LESSONS[slug]
  if (!demo) return null
  if (language && !demo.langs.includes(language)) return null
  return { slug, ...demo }
}

/** Demo job ids look like `demo_<slug>_<lang>`; slugs contain only `-`, never `_`. */
export function isDemoId(id: string | null | undefined): boolean {
  return !!id && id.startsWith('demo_')
}

export function parseDemoId(id: string): { slug: string; lang: string } | null {
  if (!isDemoId(id)) return null
  const body = id.slice('demo_'.length)
  const i = body.lastIndexOf('_')
  if (i <= 0) return null
  const slug = body.slice(0, i)
  const lang = body.slice(i + 1)
  return DEMO_LESSONS[slug]?.langs.includes(lang) ? { slug, lang } : null
}

export function demoVideoUrl(slug: string, lang: string): string {
  return `/demo/${slug}_${lang}/lesson.mp4`
}

export function demoManifestUrl(slug: string, lang: string): string {
  return `/demo/${slug}_${lang}/manifest.json`
}


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
