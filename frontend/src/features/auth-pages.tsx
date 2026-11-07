import { useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowRight, Boxes, Check, LockKeyhole, ShoppingBag, Warehouse } from 'lucide-react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api/endpoints'
import { useAuth } from '../lib/auth'
import { Brand } from '../components/layout'
import { Button, ErrorNotice, Field } from '../components/ui'

export function AuthPage({ register = false }: { register?: boolean }) {
  const auth = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [saving, setSaving] = useState(false)
  if (auth.user) return <Navigate to="/organizations" replace />
  const registered = !!(location.state as { registered?: boolean } | null)?.registered
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    if (register && password !== confirmation) {
      setError(new Error('Passwords do not match.'))
      return
    }
    setSaving(true)
    try {
      const credentials = { email: email.trim(), password }
      if (register) {
        await api.register(credentials)
        navigate('/login', { replace: true, state: { registered: true } })
      } else {
        await auth.login(credentials)
        const from = (location.state as { from?: string } | null)?.from
        navigate(from?.startsWith('/app/') ? from : '/organizations', { replace: true })
      }
    } catch (reason) {
      setError(reason)
    } finally {
      setSaving(false)
    }
  }
  return (
    <div className="auth-layout">
      <aside className="auth-story">
        <Link to="/login" aria-label="StockFlow">
          <Brand />
        </Link>
        <div className="auth-story-content">
          <span className="auth-kicker">KEEP BUSINESS MOVING</span>
          <h1>
            A clearer view.
            <br />A smoother operation.
          </h1>
          <p>Bring your products, warehouses and orders together. Less guesswork. More flow.</p>
          <div className="workflow">
            <div>
              <Boxes size={21} />
              <span>Know your products</span>
              <Check size={16} />
            </div>
            <div>
              <Warehouse size={21} />
              <span>Keep stock in sight</span>
              <Check size={16} />
            </div>
            <div>
              <ShoppingBag size={21} />
              <span>Move orders forward</span>
              <Check size={16} />
            </div>
          </div>
        </div>
        <div className="auth-story-footer">
          <span>BUILT FOR EVERYDAY OPERATIONS</span>
          <span>StockFlow</span>
        </div>
      </aside>
      <main className="auth-main">
        <div className="auth-mobile-brand">
          <Brand />
        </div>
        <div className="auth-form-wrap">
          <div className="eyebrow">YOUR WORKSPACE STARTS HERE</div>
          <h2>{register ? 'Create your account' : 'Welcome back'}</h2>
          <p className="auth-subtitle">
            {register
              ? 'One account. All your organizations, in one place.'
              : 'Sign in to keep your inventory and orders on track.'}
          </p>
          {registered && (
            <div className="success-notice" role="status">
              Account created. Sign in to create or join a workspace.
            </div>
          )}
          <ErrorNotice error={error || auth.error} />
          <form
            onSubmit={(event) => {
              void submit(event)
            }}
            className="form-stack"
          >
            <Field label="Email address">
              <input
                type="email"
                required
                maxLength={255}
                autoComplete="email"
                placeholder="you@company.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </Field>
            <Field label="Password" hint={register ? 'Use 12-128 characters.' : undefined}>
              <input
                type="password"
                required
                minLength={register ? 12 : 1}
                maxLength={128}
                autoComplete={register ? 'new-password' : 'current-password'}
                placeholder={register ? 'Create a strong password' : 'Enter your password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>
            {register && (
              <Field label="Confirm password">
                <input
                  type="password"
                  required
                  maxLength={128}
                  autoComplete="new-password"
                  value={confirmation}
                  onChange={(event) => setConfirmation(event.target.value)}
                />
              </Field>
            )}
            <Button
              className="w-full"
              type="submit"
              disabled={saving || auth.pending || auth.checking}
            >
              {saving ? 'Please wait...' : register ? 'Create account' : 'Sign in'}
              {!saving && <ArrowRight size={17} />}
            </Button>
          </form>
          <p className="auth-switch">
            {register ? 'Already have an account?' : 'New to StockFlow?'}{' '}
            <Link to={register ? '/login' : '/register'}>
              {register ? 'Sign in' : 'Create an account'}
            </Link>
          </p>
          <div className="auth-security">
            <LockKeyhole size={15} />
            <span>Your session stays secure with protected cookies.</span>
          </div>
        </div>
        <footer className="auth-footer">StockFlow &middot; Inventory, organized.</footer>
      </main>
    </div>
  )
}
