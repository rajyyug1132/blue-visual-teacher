export type Language = {
  code: string
  name: string
  nativeName: string
}

/**
 * Primary languages from the product brief. Used as a fallback when
 * GET /api/languages is unreachable; the UI labels that situation.
 */
export const DEFAULT_LANGUAGES: Language[] = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिंदी' },
  { code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ' },
]

export function languageLabel(code: string | null | undefined, list: Language[] = DEFAULT_LANGUAGES) {
  if (!code) return 'Unknown'
  const match = list.find((l) => l.code.toLowerCase() === code.toLowerCase())
  if (!match) return code
  return match.name === match.nativeName ? match.name : `${match.name} · ${match.nativeName}`
}

export const EXAMPLE_TOPICS = [
  'Photosynthesis',
  'Binary search',
  'The water cycle',
  "Newton's laws of motion",
  'Database normalization',
]
