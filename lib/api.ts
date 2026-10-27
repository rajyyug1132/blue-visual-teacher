import { DEFAULT_LANGUAGES, type Language } from './languages'

/**
 * Central client for the Blue Visual Teacher exporter (FastAPI).
 *
 * The exporter source (exporter/app.py) was not present in this workspace,
 * so response parsing is deliberately tolerant of common field names.
 * Verify and tighten these mappings once the backend contract is confirmed.
 */

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/+$/, '')

export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'unknown'

export type Job = {
  id: string
  status: JobStatus
  rawStatus: string | null
  stage: string | null
  message: string | null
  error: string | null
  videoUrl: string | null
  topic: string | null
  language: string | null
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
  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      signal: controller.signal,
      headers: { Accept: 'application/json', ...(rest.body ? { 'Content-Type': 'application/json' } : {}), ...rest.headers },
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
  // FastAPI validation errors: { detail: [{ msg, loc }] }
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
  if (['processing', 'running', 'in_progress', 'in-progress', 'started', 'rendering', 'generating', 'exporting'].includes(s))
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
  const rawStatus = pickString(body, ['status', 'state'])
  const videoKeys = ['video_url', 'mp4_url', 'output_url', 'artifact_url', 'download_url', 'url', 'video', 'mp4', 'output_path']
  const videoUrl = pickString(body, videoKeys) ?? pickString(nested, videoKeys)

  return {
    id,
    rawStatus,
    status: normalizeStatus(rawStatus),
    stage: pickString(body, ['stage', 'current_stage', 'step', 'phase']),
    message: pickString(body, ['message', 'detail_message']),
    error: pickString(body, ['error', 'error_message', 'detail']),
    videoUrl: resolveArtifactUrl(videoUrl),
    topic: pickString(body, ['topic', 'title', 'prompt']),
    language: pickString(body, ['language', 'lang', 'language_code']),
  }
}

export async function createLesson(input: { topic: string; language: string }): Promise<Job> {
  const body = await request('/api/generate', {
    method: 'POST',
    body: JSON.stringify({ topic: input.topic, language: input.language }),
    timeoutMs: 30000,
  })
  return parseJob(body)
}

export async function getJobStatus(id: string): Promise<Job> {
  const body = await request(`/api/status/${encodeURIComponent(id)}`)
  return parseJob(body, id)
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
      // { en: "English", hi: "Hindi" }
      parsed = Object.entries(list).map(([code, name]) => {
        const known = DEFAULT_LANGUAGES.find((l) => l.code === code)
        return { code, name: String(name), nativeName: known?.nativeName ?? String(name) }
      })
    }
    if (parsed.length) return { languages: parsed, source: 'api' }
  } catch {
    // fall through to fallback
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
