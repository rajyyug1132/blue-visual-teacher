'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useId, useState, type FormEvent } from 'react'
import { Eye, EyeOff, FlaskConical, Loader2 } from 'lucide-react'
import { startDemoSession } from '@/lib/demo-session'
import { registerUser, loginUser } from '@/lib/api'
import { cn } from '@/lib/utils'

type Mode = 'signup' | 'login'
type Errors = Partial<Record<'name' | 'email' | 'password' | 'confirm', string>>

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

function validate(mode: Mode, v: { name: string; email: string; password: string; confirm: string }): Errors {
  const errors: Errors = {}
  if (mode === 'signup' && v.name.trim().length < 2) errors.name = 'Enter your name (at least 2 characters).'
  if (!v.email.trim()) errors.email = 'Enter your email address.'
  else if (!EMAIL_RE.test(v.email.trim())) errors.email = 'Enter a valid email address, like name@school.edu.'
  if (!v.password) errors.password = 'Enter your password.'
  else if (mode === 'signup') {
    if (v.password.length < 8) errors.password = 'Use at least 8 characters.'
    else if (!/[A-Za-z]/.test(v.password) || !/\d/.test(v.password))
      errors.password = 'Include at least one letter and one number.'
  }
  if (mode === 'signup' && v.confirm !== v.password) errors.confirm = 'Passwords do not match.'
  return errors
}

export function AuthForm({ mode, next }: { mode: Mode; next: string }) {
  const router = useRouter()
  const [values, setValues] = useState({ name: '', email: '', password: '', confirm: '' })
  const [errors, setErrors] = useState<Errors>({})
  const [touched, setTouched] = useState<Partial<Record<keyof Errors, boolean>>>({})
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const isSignup = mode === 'signup'

  function update(field: keyof typeof values, value: string) {
    const nextValues = { ...values, [field]: value }
    setValues(nextValues)
    if (touched[field]) setErrors(validate(mode, nextValues))
  }

  function blur(field: keyof Errors) {
    setTouched((t) => ({ ...t, [field]: true }))
    setErrors(validate(mode, values))
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const found = validate(mode, values)
    setErrors(found)
    setTouched({ name: true, email: true, password: true, confirm: true })
    if (Object.keys(found).length) {
      const firstField = (['name', 'email', 'password', 'confirm'] as const).find((f) => found[f])
      if (firstField) document.getElementById(`auth-${firstField}`)?.focus()
      return
    }
    setSubmitting(true)
    const email = values.email.trim()
    const name = isSignup ? values.name.trim() : email.split('@')[0]
    try {
      if (isSignup) {
        await registerUser(name, email, values.password)
      } else {
        await loginUser(email, values.password)
      }
    } catch {
      // Offline / fallback to demo
    }
    startDemoSession({ name, email })
    router.push(next)
  }

  return (
    <div className="w-full max-w-md">
      {!isSignup && (
        <div className="flex items-start gap-3 rounded-2xl border-2 border-ink bg-brand-yellow p-4 text-sm" role="note">
          <FlaskConical className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
          <p className="leading-relaxed">
            <strong className="font-bold">Demo mode.</strong> No authentication service is connected yet, so no account is
            created and your password is never sent or saved. Continuing starts a temporary demo session in this tab.
          </p>
        </div>
      )}

      {!isSignup && (
        <>
          <h1 className="mt-8 font-display text-5xl font-black leading-[0.9] tracking-tighter md:text-6xl">
            Welcome back.
          </h1>
          <p className="mt-3 text-muted-foreground">
            Log in to keep building lessons.
          </p>
        </>
      )}

      <form noValidate onSubmit={onSubmit} className={cn("flex flex-col gap-5", isSignup ? "mt-0" : "mt-8")}>
        {isSignup && (
          <Field
            id="auth-name"
            label="Name"
            autoComplete="name"
            value={values.name}
            onChange={(v) => update('name', v)}
            onBlur={() => blur('name')}
            error={touched.name ? errors.name : undefined}
          />
        )}
        <Field
          id="auth-email"
          label="Email"
          type="email"
          inputMode="email"
          autoComplete="email"
          value={values.email}
          onChange={(v) => update('email', v)}
          onBlur={() => blur('email')}
          error={touched.email ? errors.email : undefined}
        />
        <Field
          id="auth-password"
          label="Password"
          type={showPassword ? 'text' : 'password'}
          autoComplete={isSignup ? 'new-password' : 'current-password'}
          value={values.password}
          onChange={(v) => update('password', v)}
          onBlur={() => blur('password')}
          error={touched.password ? errors.password : undefined}
          hint={isSignup ? 'At least 8 characters with a letter and a number.' : undefined}
          trailing={
            <button
              type="button"
              onClick={() => setShowPassword((s) => !s)}
              className="inline-flex size-10 items-center justify-center rounded-full hover:bg-ink/10"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              aria-pressed={showPassword}
              aria-controls="auth-password"
            >
              {showPassword ? <EyeOff className="size-5" aria-hidden="true" /> : <Eye className="size-5" aria-hidden="true" />}
            </button>
          }
        />
        {isSignup && (
          <Field
            id="auth-confirm"
            label="Confirm password"
            type={showPassword ? 'text' : 'password'}
            autoComplete="new-password"
            value={values.confirm}
            onChange={(v) => update('confirm', v)}
            onBlur={() => blur('confirm')}
            error={touched.confirm ? errors.confirm : undefined}
          />
        )}

        <button
          type="submit"
          disabled={submitting}
          className="mt-2 inline-flex h-14 items-center justify-center gap-2 rounded-full bg-brand-blue text-lg font-bold text-white transition-transform hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0"
        >
          {submitting && <Loader2 className="size-5 animate-spin" aria-hidden="true" />}
          {submitting ? 'Please wait…' : isSignup ? 'Create account' : 'Log in'}
        </button>
      </form>

      <p className="mt-6 text-sm">
        {isSignup ? 'Already have an account? ' : 'New to Blue Visual Teacher? '}
        <Link
          href={`${isSignup ? '/login' : '/signup'}${next !== '/dashboard' ? `?next=${encodeURIComponent(next)}` : ''}`}
          className="font-bold underline underline-offset-4"
        >
          {isSignup ? 'Log in' : 'Sign up'}
        </Link>
      </p>
    </div>
  )
}

function Field({
  id,
  label,
  value,
  onChange,
  onBlur,
  error,
  hint,
  trailing,
  type = 'text',
  ...rest
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  onBlur: () => void
  error?: string
  hint?: string
  trailing?: React.ReactNode
  type?: string
  autoComplete?: string
  inputMode?: 'email' | 'text'
}) {
  const hintId = useId()
  const errorId = useId()
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(' ') || undefined
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-bold text-ink">
        {label}
      </label>
      <div
        className={cn(
          'relative flex items-center rounded-full border-2 bg-white transition-shadow focus-within:shadow-[3px_3px_0_0_#4974E5]',
          error ? 'border-destructive' : 'border-ink',
        )}
      >
        <input
          id={id}
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className="h-14 min-w-0 flex-1 rounded-full bg-transparent px-6 py-3.5 text-base outline-none"
          {...rest}
        />
        {trailing && <div className="absolute right-3 flex items-center">{trailing}</div>}
      </div>
      {hint && !error && (
        <p id={hintId} className="px-3 text-xs text-muted-foreground">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="px-3 text-sm font-semibold text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}
