'use client'

import { useCallback, useEffect, useState } from 'react'
import useSWR from 'swr'
import { getHealth, getJobStatus, getLanguages, type Job } from '@/lib/api'

const POLL_MS = 2500

export function useLanguages() {
  return useSWR('languages', getLanguages, { revalidateOnFocus: false, shouldRetryOnError: false })
}

export function useHealth() {
  return useSWR('health', getHealth, { refreshInterval: 30000, revalidateOnFocus: true, shouldRetryOnError: false })
}

/**
 * Polls GET /api/status/{id} reliably on the client while the job is active.
 * Stops automatically when status is 'completed' or 'failed'.
 */
export function useJob(id: string) {
  const [data, setData] = useState<Job | undefined>(undefined)
  const [error, setError] = useState<Error | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isValidating, setIsValidating] = useState<boolean>(false)

  const fetchStatus = useCallback(async () => {
    if (!id) return
    setIsValidating(true)
    try {
      const res = await getJobStatus(id)
      setData(res)
      setError(null)
      setIsLoading(false)
      return res
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)))
      setIsLoading(false)
    } finally {
      setIsValidating(false)
    }
  }, [id])

  useEffect(() => {
    let active = true
    let timer: any

    async function poll() {
      const job = await fetchStatus()
      if (!active) return
      if (job && (job.status === 'completed' || job.status === 'failed')) {
        return
      }
      timer = setTimeout(poll, POLL_MS)
    }

    poll()

    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [fetchStatus])

  return { data, error, isLoading, isValidating, mutate: fetchStatus }
}
