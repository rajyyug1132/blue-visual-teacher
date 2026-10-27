import type { Metadata } from 'next'
import { AppShellClient } from '@/components/app/app-shell-client'

export const metadata: Metadata = { title: 'Dashboard' }

export default function DashboardPage() {
  return <AppShellClient view="dashboard" next="/dashboard" />
}
