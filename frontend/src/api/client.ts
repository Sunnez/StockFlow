export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export function readCsrfCookie(): string | undefined {
  const raw = document.cookie.split('; ').find((part) => part.startsWith('csrf_token='))
  if (!raw) return undefined
  try {
    return decodeURIComponent(raw.slice('csrf_token='.length))
  } catch {
    return undefined
  }
}

type AuthEvent = 'login' | 'logout' | 'expired'
type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  signal?: AbortSignal
  auth?: boolean
}
type LockRunner = <T>(task: () => Promise<T>) => Promise<T>

export function browserSessionLock(name: string): LockRunner {
  return async (task) => {
    if (typeof navigator !== 'undefined' && navigator.locks) {
      return navigator.locks.request(name, { signal: AbortSignal.timeout(30_000) }, task)
    }
    // The client still coalesces refreshes within a tab on older browsers.
    return task()
  }
}

function detailMessage(body: unknown, status: number): string {
  if (status >= 500) return 'The server could not complete this request. Please try again.'
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail: unknown = body.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((item: unknown) => {
          if (!item || typeof item !== 'object' || !('msg' in item)) return 'Invalid input'
          const loc: unknown = 'loc' in item ? item.loc : []
          const field = Array.isArray(loc) ? loc.filter((v) => v !== 'body').join('.') : ''
          return `${field ? `${field}: ` : ''}${String(item.msg)}`
        })
        .join('; ')
    }
  }
  return (
    (
      {
        401: 'Your session has expired. Sign in again.',
        403: 'You do not have permission, or the security token is invalid. Reload and try again.',
        404: 'This resource is unavailable or you no longer have access.',
        409: 'This operation conflicts with the current state.',
        422: 'Please check the form fields.',
      } as Record<number, string>
    )[status] ?? 'The request failed. Please try again.'
  )
}

export class ApiClient {
  private refreshing: Promise<void> | null = null
  private generation = 0
  private listeners = new Set<(event: AuthEvent) => void>()
  private lock: LockRunner

  constructor(
    private baseUrl: string,
    private transport: typeof fetch = (input, init) => fetch(input, init),
    private csrf = readCsrfCookie,
    lock?: LockRunner,
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, '')
    this.lock = lock ?? browserSessionLock(`stockflow-auth:${this.baseUrl}`)
  }

  subscribe(listener: (event: AuthEvent) => void) {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  sessionChanged(event: AuthEvent) {
    this.generation++
    this.listeners.forEach((listener) => listener(event))
  }

  private async send<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const controller = new AbortController()
    const abort = () => controller.abort(options.signal?.reason)
    if (options.signal?.aborted) abort()
    options.signal?.addEventListener('abort', abort, { once: true })
    const timer = setTimeout(() => controller.abort(), 20_000)
    const method = options.method ?? 'GET'
    const headers = new Headers({ Accept: 'application/json' })
    if (options.body !== undefined) headers.set('Content-Type', 'application/json')
    if (method !== 'GET') {
      const csrf = this.csrf()
      if (csrf) headers.set('X-CSRF-Token', csrf)
    }
    try {
      const response = await this.transport(`${this.baseUrl}${path}`, {
        method,
        headers,
        credentials: 'include',
        cache: 'no-store',
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: controller.signal,
      })
      if (!response.ok) {
        const body: unknown = await response.json().catch(() => null)
        throw new ApiError(response.status, detailMessage(body, response.status))
      }
      if (response.status === 204) return undefined as T
      return (await response.json()) as T
    } catch (error) {
      if (error instanceof ApiError) throw error
      if (options.signal?.aborted) throw error
      throw new ApiError(
        0,
        'Cannot reach StockFlow. Check your connection and API configuration, then try again.',
      )
    } finally {
      clearTimeout(timer)
      options.signal?.removeEventListener('abort', abort)
    }
  }

  private async refresh(generation: number): Promise<void> {
    if (!this.refreshing) {
      this.refreshing = this.lock(async () => {
        if (generation !== this.generation)
          throw new ApiError(401, 'Session changed. Please sign in again.')
        // Another tab may have rotated while this one waited for the lock.
        // Probe the shared HttpOnly access cookie; never read or persist tokens.
        try {
          await this.send('/users/me')
          return
        } catch (error) {
          if (!(error instanceof ApiError) || error.status !== 401) throw error
        }
        if (!this.csrf()) throw new ApiError(401, 'Sign in to continue.')
        await this.send('/auth/refresh', { method: 'POST' })
      })
        .catch((error) => {
          if (
            generation === this.generation &&
            error instanceof ApiError &&
            (error.status === 401 || error.status === 403)
          ) {
            this.sessionChanged('expired')
            throw new ApiError(401, 'Your session has expired. Sign in again.')
          }
          throw error
        })
        .finally(() => {
          this.refreshing = null
        })
    }
    return this.refreshing
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const generation = this.generation
    const authenticated = options.auth !== false
    let result: T
    try {
      result = await this.send<T>(path, options)
    } catch (error) {
      if (
        !authenticated ||
        !(error instanceof ApiError) ||
        error.status !== 401 ||
        options.signal?.aborted
      )
        throw error
      await this.refresh(generation)
      if (generation !== this.generation)
        throw new ApiError(401, 'Session changed. Please sign in again.')
      try {
        result = await this.send<T>(path, options)
      } catch (retryError) {
        if (
          generation === this.generation &&
          retryError instanceof ApiError &&
          retryError.status === 401
        )
          this.sessionChanged('expired')
        throw retryError
      }
    }
    if (authenticated && generation !== this.generation)
      throw new ApiError(401, 'Session changed. Please sign in again.')
    return result
  }

  async authAction<T>(path: '/auth/login' | '/auth/logout', body?: unknown): Promise<T> {
    return this.lock(() => this.send<T>(path, { method: 'POST', body, auth: false }))
  }
}

export const apiClient = new ApiClient(import.meta.env.VITE_API_URL || 'http://localhost:8000')
