import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, NavLink, Outlet, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeftRight,
  Box,
  Building2,
  ChevronDown,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  Settings,
  ShoppingCart,
  Users,
  Warehouse,
  X,
} from 'lucide-react'
import { api } from '../api/endpoints'
import type { OrganizationWithRole } from '../api/types'
import { useAuth } from '../lib/auth'
import { tenantKey, useOrganizations } from '../lib/queries'
import { UUID_PATTERN } from '../lib/permissions'
import { Button, ErrorNotice, ErrorState, Loading } from './ui'

const TenantContext = createContext<OrganizationWithRole | null>(null)
export function useTenant() {
  const org = useContext(TenantContext)
  if (!org) throw new Error('Tenant context is required')
  return org
}

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="brand">
      <span className="brand-icon">
        <Box size={23} strokeWidth={1.8} />
      </span>
      {!compact && (
        <span>
          Stock<span className="font-normal">Flow</span>
          <span className="brand-dot">.</span>
        </span>
      )}
    </div>
  )
}

export function LogoutButton({ compact = false }: { compact?: boolean }) {
  const { logout, pending } = useAuth()
  const [error, setError] = useState<unknown>(null)
  const navigate = useNavigate()
  return (
    <div>
      <Button
        variant="ghost"
        disabled={pending}
        aria-label="Log out"
        onClick={() => {
          setError(null)
          void logout()
            .then(() => navigate('/login', { replace: true }))
            .catch(setError)
        }}
      >
        <LogOut size={17} />
        {!compact && 'Log out'}
      </Button>
      <ErrorNotice error={error} />
    </div>
  )
}

export function TenantLayout() {
  const { organizationId = '' } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const sidebar = useRef<HTMLElement>(null)
  useEffect(() => {
    const media = window.matchMedia('(min-width: 761px)')
    const resize = () => {
      if (media.matches) setMobileOpen(false)
    }
    media.addEventListener('change', resize)
    return () => media.removeEventListener('change', resize)
  }, [])
  useEffect(() => {
    if (!mobileOpen) return
    const previous = document.activeElement as HTMLElement | null
    sidebar.current?.querySelector<HTMLButtonElement>('button')?.focus()
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        setMobileOpen(false)
      }
      if (event.key !== 'Tab') return
      const controls = sidebar.current?.querySelectorAll<HTMLElement>(
        'a[href], button:not(:disabled)',
      )
      const first = controls?.[0]
      const last = controls?.[controls.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last?.focus()
      }
      if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }
    document.addEventListener('keydown', keyboard)
    return () => {
      document.removeEventListener('keydown', keyboard)
      previous?.focus()
    }
  }, [mobileOpen])
  const organizations = useOrganizations()
  const org = useQuery({
    queryKey: [...tenantKey(organizationId), 'organization'],
    queryFn: ({ signal }) => api.organizations.get(organizationId, signal),
    enabled: UUID_PATTERN.test(organizationId),
  })
  if (!UUID_PATTERN.test(organizationId))
    return (
      <ErrorState
        error={new Error('Invalid workspace address. Choose an organization to continue.')}
      />
    )
  if (org.isPending) return <Loading />
  if (org.isError)
    return (
      <ErrorState
        error={org.error}
        retry={() => {
          void org.refetch()
        }}
      />
    )
  const base = `/app/${org.data.id}`
  const nav = [
    { to: 'dashboard', label: 'Overview', Icon: LayoutDashboard },
    { to: 'products', label: 'Products', Icon: Package },
    { to: 'warehouses', label: 'Warehouses', Icon: Warehouse },
    { to: 'orders', label: 'Orders', Icon: ShoppingCart },
    ...(org.data.role === 'viewer' ? [] : [{ to: 'members', label: 'Members', Icon: Users }]),
    { to: 'settings', label: 'Organization', Icon: Settings },
  ]
  const switchOrg = (value: string) => {
    const target = organizations.data?.find((item) => item.id === value)
    if (!target) return
    if (user) {
      try {
        localStorage.setItem(`stockflow-organization:${user.id}`, target.id)
      } catch {
        /* selection persistence is optional */
      }
    }
    setMobileOpen(false)
    navigate(`/app/${target.id}/dashboard`)
  }
  return (
    <TenantContext.Provider value={org.data}>
      <div className="app-shell">
        {mobileOpen && (
          <button
            className="sidebar-backdrop"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          />
        )}
        <aside
          ref={sidebar}
          id="workspace-navigation"
          className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}
        >
          <Link to="/organizations" aria-label="StockFlow workspaces">
            <Brand />
          </Link>
          <Button
            className="mobile-close"
            variant="ghost"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          >
            <X size={20} />
          </Button>
          <div className="sidebar-section-label">WORKSPACE</div>
          <div className="sidebar-workspace">
            <span className="org-avatar">{org.data.name.slice(0, 1).toUpperCase()}</span>
            <div>
              <strong>{org.data.name}</strong>
              <span>{org.data.role} access</span>
            </div>
            <ChevronDown size={15} />
          </div>
          <nav aria-label="Workspace navigation">
            {nav.map(({ to, label, Icon }) => (
              <NavLink
                key={to}
                to={`${base}/${to}`}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) => `nav-item ${isActive ? 'nav-active' : ''}`}
              >
                <Icon size={19} strokeWidth={1.8} />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="sidebar-help">
              <Building2 size={20} />
              <strong>Your workspace, in sync.</strong>
              <p>Products, stock and fulfillment. One place to keep things moving.</p>
            </div>
            <Link className="nav-item" to="/organizations">
              <ArrowLeftRight size={17} />
              All workspaces
            </Link>
            <div className="sidebar-footer">
              STOCKFLOW <span>Inventory management</span>
            </div>
          </div>
        </aside>
        <div className="app-main" inert={mobileOpen}>
          <header className="topbar">
            <div className="flex min-w-0 items-center gap-3">
              <Button
                variant="ghost"
                className="mobile-menu"
                aria-label="Open navigation"
                aria-expanded={mobileOpen}
                aria-controls="workspace-navigation"
                onClick={() => setMobileOpen(true)}
              >
                <Menu size={21} />
              </Button>
              <span className="topbar-label">Workspace</span>
              <label className="org-select">
                <span className="sr-only">Switch workspace</span>
                <select
                  value={org.data.id}
                  onChange={(event) => switchOrg(event.target.value)}
                  disabled={organizations.isPending || organizations.isError}
                >
                  {(organizations.data ?? [org.data]).map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="topbar-user">
              <span className="user-avatar">{user?.email.slice(0, 1).toUpperCase()}</span>
              <div className="user-info">
                <strong>{user?.email}</strong>
                <span>{org.data.role}</span>
              </div>
              <LogoutButton compact />
            </div>
          </header>
          <main className="page-content" key={org.data.id}>
            <Outlet />
          </main>
          <footer className="page-footer">
            <span>StockFlow</span>
            <span>One workspace. Every operation.</span>
          </footer>
        </div>
      </div>
    </TenantContext.Provider>
  )
}
