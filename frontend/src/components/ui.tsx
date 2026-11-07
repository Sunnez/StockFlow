import { cloneElement, createContext, useContext, useEffect, useId, useRef, useState } from 'react'
import type { ButtonHTMLAttributes, ReactElement, ReactNode } from 'react'
import { AlertCircle, ArrowLeft, CheckCircle2, LoaderCircle, PackageOpen, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { OrderStatus } from '../api/types'

export function Button({
  variant = 'primary',
  className = '',
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
}) {
  return (
    <button type="button" className={`btn btn-${variant} ${className}`} {...props}>
      {children}
    </button>
  )
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string
  children: ReactElement<{ 'aria-describedby'?: string; id?: string }>
  hint?: string
}) {
  const hintId = useId()
  const controlId = useId()
  return (
    <div className="field">
      <label className="field-label" htmlFor={controlId}>
        <span>{label}</span>
      </label>
      {cloneElement(children, { id: controlId, 'aria-describedby': hint ? hintId : undefined })}
      {hint && (
        <span className="field-hint" id={hintId}>
          {hint}
        </span>
      )}
    </div>
  )
}

export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null
  return (
    <div className="error-notice" role="alert">
      <AlertCircle size={18} aria-hidden="true" />
      <span>
        {error instanceof Error ? error.message : 'Something went wrong. Please try again.'}
      </span>
    </div>
  )
}

export function Loading({ label = 'Loading your workspace...' }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <LoaderCircle className="animate-spin" size={24} aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  return (
    <div className="panel state-panel">
      <div className="state-icon">
        <AlertCircle size={26} />
      </div>
      <h2>We couldn't load this page</h2>
      <ErrorNotice error={error} />
      <div className="flex flex-wrap justify-center gap-3">
        {retry && (
          <Button variant="secondary" onClick={retry}>
            Try again
          </Button>
        )}
        <Link className="btn btn-ghost" to="/organizations">
          Choose a workspace
        </Link>
      </div>
    </div>
  )
}

export function Empty({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="state-panel">
      <div className="state-icon">
        <PackageOpen size={26} aria-hidden="true" />
      </div>
      <h2>{title}</h2>
      <p>{description}</p>
      {action}
    </div>
  )
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action && <div className="header-actions">{action}</div>}
    </div>
  )
}

export function BackLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link className="back-link" to={to}>
      <ArrowLeft size={16} aria-hidden="true" />
      {children}
    </Link>
  )
}

export function Dialog({
  title,
  description,
  onClose,
  busy = false,
  children,
}: {
  title: string
  description?: string
  onClose: () => void
  busy?: boolean
  children: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const descId = useId()
  useEffect(() => {
    const dialog = ref.current
    dialog?.showModal()
    return () => {
      dialog?.close()
    }
  }, [])
  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby={titleId}
      aria-describedby={description ? descId : undefined}
      onCancel={(event) => {
        event.preventDefault()
        if (!busy) onClose()
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget && !busy) onClose()
      }}
    >
      <div className="modal-content">
        <div className="modal-heading">
          <div>
            <h2 id={titleId}>{title}</h2>
            {description && <p id={descId}>{description}</p>}
          </div>
          <Button variant="ghost" aria-label="Close dialog" disabled={busy} onClick={onClose}>
            <X size={20} />
          </Button>
        </div>
        {children}
      </div>
    </dialog>
  )
}

export function ConfirmDialog({
  title,
  description,
  confirmLabel,
  onClose,
  onConfirm,
  busy,
  error,
  danger = false,
}: {
  title: string
  description: string
  confirmLabel: string
  onClose: () => void
  onConfirm: () => void
  busy: boolean
  error: unknown
  danger?: boolean
}) {
  return (
    <Dialog title={title} description={description} onClose={onClose} busy={busy}>
      <ErrorNotice error={error} />
      <div className="form-actions">
        <Button variant="secondary" onClick={onClose} disabled={busy}>
          Keep it
        </Button>
        <Button variant={danger ? 'danger' : 'primary'} disabled={busy} onClick={onConfirm}>
          {busy && <LoaderCircle size={16} className="animate-spin" />}
          {confirmLabel}
        </Button>
      </div>
    </Dialog>
  )
}

export function Pagination({
  offset,
  count,
  onChange,
  size = 20,
  busy = false,
}: {
  offset: number
  count: number
  onChange: (offset: number) => void
  size?: number
  busy?: boolean
}) {
  return (
    <div className="pagination">
      <span>{count ? `Showing ${offset + 1}-${offset + count}` : 'No results on this page'}</span>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          disabled={busy || offset === 0}
          onClick={() => onChange(Math.max(0, offset - size))}
        >
          Previous
        </Button>
        <Button
          variant="secondary"
          disabled={busy || count < size}
          onClick={() => onChange(offset + size)}
        >
          Next
        </Button>
      </div>
    </div>
  )
}

export function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span className={`status-badge status-${status}`}>
      <span />
      {status}
    </span>
  )
}

const NoticeContext = createContext<(message: string) => void>(() => {})
export function NoticeProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('')
  useEffect(() => {
    if (!message) return
    const timer = setTimeout(() => setMessage(''), 6000)
    return () => clearTimeout(timer)
  }, [message])
  return (
    <NoticeContext.Provider value={setMessage}>
      {children}
      <div className="toast-region" aria-live="polite">
        {message && (
          <div className="toast">
            <CheckCircle2 size={20} />
            <span>{message}</span>
            <Button
              variant="ghost"
              aria-label="Dismiss notification"
              onClick={() => setMessage('')}
            >
              <X size={16} />
            </Button>
          </div>
        )}
      </div>
    </NoticeContext.Provider>
  )
}
export function useNotice() {
  return useContext(NoticeContext)
}
