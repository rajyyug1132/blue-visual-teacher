'use client'

import { useEffect, useState } from 'react'
import { isShowcase } from '@/lib/showcase'

/** False on the server and on first paint (so hydration matches), then the real value. */
export function useShowcase(): boolean {
  const [showcase, setShowcase] = useState(false)
  useEffect(() => setShowcase(isShowcase()), [])
  return showcase
}
