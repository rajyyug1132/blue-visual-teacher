import { DEFAULT_LANGUAGES, type Language } from './languages'
import { getAuthToken } from './demo-session'

export const API_BASE_URL = typeof window !== 'undefined'
  ? (process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.protocol}//${window.location.hostname}:8000`).replace(/\/+$/, '')
  : (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/+$/, '')

export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'unknown'

export type Job = {
  id: string
  status: JobStatus
  rawStatus: string | null
  stage: string | null
  message: string | null
  error: string | null
  videoUrl: string | null
  manifestUrl?: string | null
  topic: string | null
  language: string | null
  pct?: number
}

export type LessonRecord = {
  id: string
  userId: string
  topic: string
  lang: string
  status: string
  pct: number
  stage: string
  mp4Url: string | null
  manifestUrl: string | null
  audioUrl: string | null
  error: string | null
  createdAt: number
  updatedAt: number
}

export type AuthUser = {
  id: string
  name: string
  email: string
  createdAt: number
}

export class ApiError extends Error {
  constructor(
    message: string,
    public kind: 'network' | 'timeout' | 'http' | 'malformed',
    public status?: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

type Json = Record<string, unknown>

function isObject(v: unknown): v is Json {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function pickString(obj: Json | undefined, keys: string[]): string | null {
  if (!obj) return null
  for (const key of keys) {
    const value = obj[key]
    if (typeof value === 'string' && value.trim()) return value
    if (typeof value === 'number') return String(value)
  }
  return null
}

async function request<T = unknown>(path: string, init: RequestInit & { timeoutMs?: number } = {}): Promise<T> {
  const { timeoutMs = 15000, ...rest } = init
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(rest.body ? { 'Content-Type': 'application/json' } : {}),
  }

  // Attach Authorization token if available
  const token = getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      signal: controller.signal,
      credentials: 'include',
      headers: { ...headers, ...rest.headers },
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError('The server took too long to respond.', 'timeout')
    }
    throw new ApiError(`Couldn't reach the lesson server at ${API_BASE_URL}.`, 'network')
  } finally {
    clearTimeout(timer)
  }

  let body: unknown = null
  const text = await res.text()
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      if (res.ok) throw new ApiError('The server sent a response we could not read.', 'malformed', res.status)
    }
  }

  if (!res.ok) {
    throw new ApiError(extractErrorMessage(body) ?? `Request failed (HTTP ${res.status}).`, 'http', res.status)
  }
  return body as T
}

function extractErrorMessage(body: unknown): string | null {
  if (!isObject(body)) return null
  const detail = body.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length && isObject(detail[0])) {
    const first = detail[0]
    const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : null
    const msg = typeof first.msg === 'string' ? first.msg : 'Invalid input'
    return field ? `${String(field)}: ${msg}` : msg
  }
  return pickString(body, ['error', 'message'])
}

export function normalizeStatus(raw: string | null): JobStatus {
  if (!raw) return 'unknown'
  const s = raw.toLowerCase()
  if (['queued', 'pending', 'waiting', 'created', 'submitted'].includes(s)) return 'queued'
  if (['processing', 'running', 'in_progress', 'in-progress', 'started', 'rendering', 'generating', 'exporting', 'plan', 'tts', 'render'].includes(s))
    return 'processing'
  if (['completed', 'complete', 'done', 'success', 'succeeded', 'finished', 'ready'].includes(s)) return 'completed'
  if (['failed', 'failure', 'error', 'errored', 'cancelled', 'canceled'].includes(s)) return 'failed'
  return 'unknown'
}

/** Resolve a possibly-relative artifact path against the backend origin. */
export function resolveArtifactUrl(url: string | null): string | null {
  if (!url) return null
  try {
    return new URL(url, `${API_BASE_URL}/`).toString()
  } catch {
    return null
  }
}

function parseJob(body: unknown, fallbackId?: string): Job {
  if (!isObject(body)) throw new ApiError('The server sent an unexpected job response.', 'malformed')
  const nested = [body.result, body.output, body.artifact, body.data].find(isObject) as Json | undefined
  const id = pickString(body, ['job_id', 'id', 'jobId', 'task_id']) ?? fallbackId
  if (!id) throw new ApiError('The server did not return a job id.', 'malformed')
  const rawStatus = pickString(body, ['status', 'state', 'stage'])
  const videoKeys = ['video_url', 'mp4_url', 'output_url', 'artifact_url', 'download_url', 'url', 'video', 'mp4', 'output_path']
  const manifestKeys = ['manifest_url', 'manifestUrl', 'manifest']
  const videoUrl = pickString(body, videoKeys) ?? pickString(nested, videoKeys)
  const manifestUrl = pickString(body, manifestKeys) ?? pickString(nested, manifestKeys)

  return {
    id,
    rawStatus,
    status: normalizeStatus(rawStatus),
    stage: pickString(body, ['stage', 'current_stage', 'step', 'phase']),
    message: pickString(body, ['message', 'detail_message']),
    error: pickString(body, ['error', 'error_message', 'detail']),
    videoUrl: resolveArtifactUrl(videoUrl),
    manifestUrl: resolveArtifactUrl(manifestUrl),
    topic: pickString(body, ['topic', 'title', 'prompt']),
    language: pickString(body, ['language', 'lang', 'language_code']),
    pct: typeof body.pct === 'number' ? body.pct : undefined,
  }
}

// --- AUTHENTICATION API ---
export async function registerUser(name: string, email: string, password: string): Promise<{ user: AuthUser; token: string }> {
  const res = await request<{ user: { id: string; name: string; email: string; created_at: number }; token: string }>('/api/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  })
  return {
    user: { id: res.user.id, name: res.user.name, email: res.user.email, createdAt: res.user.created_at },
    token: res.token,
  }
}

export async function loginUser(email: string, password: string): Promise<{ user: AuthUser; token: string }> {
  const res = await request<{ user: { id: string; name: string; email: string; created_at: number }; token: string }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  return {
    user: { id: res.user.id, name: res.user.name, email: res.user.email, createdAt: res.user.created_at },
    token: res.token,
  }
}

export async function logoutUser(): Promise<void> {
  try {
    await request('/api/auth/logout', { method: 'POST' })
  } catch {
    // ignore network errors on logout
  }
}

export async function getAuthMe(): Promise<AuthUser | null> {
  try {
    const res = await request<{ user: { id: string; name: string; email: string; created_at: number } }>('/api/auth/me')
    return { id: res.user.id, name: res.user.name, email: res.user.email, createdAt: res.user.created_at }
  } catch {
    return null
  }
}

// --- LESSON API ---
export async function createLesson(input: { topic: string; language: string }): Promise<Job> {
  const body = await request('/api/generate', {
    method: 'POST',
    body: JSON.stringify({ topic: input.topic, lang: input.language, language: input.language }),
    timeoutMs: 30000,
  })
  return parseJob(body)
}

export async function getJobStatus(id: string): Promise<Job> {
  const body = await request(`/api/status/${encodeURIComponent(id)}`)
  return parseJob(body, id)
}

export async function getUserLessonHistory(): Promise<LessonRecord[]> {
  const body = await request<Array<any>>('/api/lessons/history')
  if (!Array.isArray(body)) return []
  return body.map((r) => ({
    id: r.id,
    userId: r.user_id,
    topic: r.topic,
    lang: r.lang,
    status: r.status,
    pct: r.pct ?? 0,
    stage: r.stage ?? 'queued',
    mp4Url: resolveArtifactUrl(r.mp4_url),
    manifestUrl: resolveArtifactUrl(r.manifest_url),
    audioUrl: resolveArtifactUrl(r.audio_url),
    error: r.error,
    createdAt: r.created_at * 1000,
    updatedAt: r.updated_at * 1000,
  }))
}

export type LanguagesResult = { languages: Language[]; source: 'api' | 'fallback' }

export async function getLanguages(): Promise<LanguagesResult> {
  try {
    const body = await request('/api/languages', { timeoutMs: 6000 })
    const list = Array.isArray(body) ? body : isObject(body) ? (body.languages ?? body.data) : null
    let parsed: Language[] = []
    if (Array.isArray(list)) {
      parsed = list
        .map((item): Language | null => {
          if (typeof item === 'string') {
            const known = DEFAULT_LANGUAGES.find((l) => l.code === item)
            return known ?? { code: item, name: item, nativeName: item }
          }
          if (isObject(item)) {
            const code = pickString(item, ['code', 'id', 'value', 'lang'])
            if (!code) return null
            const known = DEFAULT_LANGUAGES.find((l) => l.code === code)
            const name = pickString(item, ['name', 'label', 'english_name']) ?? known?.name ?? code
            const nativeName = pickString(item, ['native_name', 'nativeName', 'native']) ?? known?.nativeName ?? name
            return { code, name, nativeName }
          }
          return null
        })
        .filter((l): l is Language => l !== null)
    } else if (isObject(list)) {
      parsed = Object.entries(list).map(([code, name]) => {
        const known = DEFAULT_LANGUAGES.find((l) => l.code === code)
        return { code, name: String(name), nativeName: known?.nativeName ?? String(name) }
      })
    }
    if (parsed.length) return { languages: parsed, source: 'api' }
  } catch {
    // fall through
  }
  return { languages: DEFAULT_LANGUAGES, source: 'fallback' }
}

export type HealthResult = { ok: boolean; message: string }

export async function getHealth(): Promise<HealthResult> {
  try {
    const body = await request('/api/health', { timeoutMs: 5000 })
    const status = isObject(body) ? pickString(body, ['status', 'state']) : null
    return { ok: true, message: status ? `Connected · ${status}` : 'Connected' }
  } catch (err) {
    return { ok: false, message: err instanceof ApiError ? err.message : 'Lesson server unavailable.' }
  }
}
