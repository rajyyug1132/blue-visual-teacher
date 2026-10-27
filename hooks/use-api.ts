'use client'

import useSWR from 'swr'
import { getHealth, getJobStatus, getLanguages, type Job } from '@/lib/api'

const POLL_MS = 3000

export function useLanguages() {
  return useSWR('languages', getLanguages, { revalidateOnFocus: false, shouldRetryOnError: false })
}

export function useHealth() {
  return useSWR('health', getHealth, { refreshInterval: 30000, revalidateOnFocus: true, shouldRetryOnError: false })
}

function isTerminal(job: Job | undefined) {
  return job?.status === 'completed' || job?.status === 'failed'
}

/**
 * Polls GET /api/status/{id} every few seconds while the job is active.
 * SWR stops interval revalidation while an error is cached, so a network
 * failure halts polling until the user retries. Unmounting cleans up.
 */
export function useJob(id: string) {
  return useSWR(['job', id], () => getJobStatus(id), {
    refreshInterval: (latest) => (isTerminal(latest) ? 0 : POLL_MS),
    revalidateOnFocus: false,
    shouldRetryOnError: false,
    dedupingInterval: POLL_MS - 500,
  })
}
