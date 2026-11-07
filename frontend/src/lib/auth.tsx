import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { api } from '../api/endpoints'
import { ApiError, apiClient } from '../api/client'
import type { Credentials, User } from '../api/types'
import { ErrorState, Loading } from '../components/ui'

type AuthContextValue = {
  user: User | null | undefined
  login: (credentials: Credentials) => Promise<void>
  logout: () => Promise<void>
  pending: boolean
  checking: boolean
  error: unknown
  retry: () => void
}
const AuthContext = createContext<AuthContextValue | null>(null)
const authChannelName = 'stockflow-session-events'

export function AuthProvider({ children }: { children: ReactNode }) {
  const cache = useQueryClient()
  const [pending, setPending] = useState(false)
  const me = useQuery<User | null>({
    queryKey: ['me'],
    queryFn: ({ signal }) => api.me(signal),
    retry: false,
    staleTime: 60_000,
  })

  useEffect(() => {
    const channel =
      typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel(authChannelName) : null
    const unsubscribe = apiClient.subscribe((event) => {
      void cache.cancelQueries()
      cache.removeQueries({ predicate: (query) => query.queryKey[0] !== 'me' })
      if (event === 'login') {
        cache.setQueryData(['me'], null)
        void cache.invalidateQueries({ queryKey: ['me'] })
      } else {
        cache.setQueryData(['me'], null)
      }
    })
    const remote = (data: unknown) => {
      if (!data || typeof data !== 'object' || !('type' in data)) return
      if (data.type === 'login' || data.type === 'logout' || data.type === 'expired')
        apiClient.sessionChanged(data.type)
    }
    if (channel) channel.onmessage = (event) => remote(event.data)
    const onStorage = (event: StorageEvent) => {
      if (event.key !== 'stockflow-session-event' || !event.newValue) return
      try {
        remote(JSON.parse(event.newValue) as unknown)
      } catch {
        /* malformed metadata is ignored */
      }
    }
    window.addEventListener('storage', onStorage)
    return () => {
      unsubscribe()
      channel?.close()
      window.removeEventListener('storage', onStorage)
    }
  }, [cache])

  function broadcast(type: 'login' | 'logout') {
    if (typeof BroadcastChannel !== 'undefined') {
      const channel = new BroadcastChannel(authChannelName)
      channel.postMessage({ type })
      channel.close()
    } else {
      try {
        localStorage.setItem('stockflow-session-event', JSON.stringify({ type, at: Date.now() }))
      } catch {
        /* no credential storage */
      }
    }
  }

  const login = async (credentials: Credentials) => {
    setPending(true)
    try {
      const user = await api.login(credentials)
      apiClient.sessionChanged('login')
      await cache.cancelQueries()
      cache.removeQueries({ predicate: (query) => query.queryKey[0] !== 'me' })
      cache.setQueryData(['me'], user)
      broadcast('login')
    } finally {
      setPending(false)
    }
  }
  const logout = async () => {
    setPending(true)
    try {
      await api.logout()
      apiClient.sessionChanged('logout')
      await cache.cancelQueries()
      cache.removeQueries({ predicate: (query) => query.queryKey[0] !== 'me' })
      cache.setQueryData(['me'], null)
      broadcast('logout')
    } finally {
      setPending(false)
    }
  }
  const unauthorized = me.error instanceof ApiError && me.error.status === 401
  return (
    <AuthContext.Provider
      value={{
        user: unauthorized ? null : me.data,
        login,
        logout,
        pending,
        checking: me.isPending,
        error: unauthorized ? null : me.error,
        retry: () => {
          void me.refetch()
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('Auth provider is required')
  return context
}
export function ProtectedRoute() {
  const { user, checking, error, retry } = useAuth()
  const location = useLocation()
  if (checking) return <Loading label="Checking your session..." />
  if (error && !user) return <ErrorState error={error} retry={retry} />
  return user ? <Outlet /> : <Navigate to="/login" replace state={{ from: location.pathname }} />
}
