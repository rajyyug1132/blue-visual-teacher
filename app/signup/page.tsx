import type { Metadata } from 'next'
import { AuthForm } from '@/components/auth/auth-form'
import { AuthShell, safeNext } from '@/components/auth/auth-shell'

export const metadata: Metadata = { title: 'Sign up' }

export default async function SignupPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams
  return (
    <AuthShell>
      <AuthForm mode="signup" next={safeNext(params.next)} />
    </AuthShell>
  )
}
