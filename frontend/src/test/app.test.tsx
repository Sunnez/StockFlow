import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AppRoutes } from '../App'
import type { Member, Order, Product, Role } from '../api/types'
import { apiClient } from '../api/client'

const orgId = '11111111-1111-1111-1111-111111111111'
const productId = '22222222-2222-2222-2222-222222222222'
const warehouseId = '33333333-3333-3333-3333-333333333333'
const orderId = '44444444-4444-4444-4444-444444444444'
const viewerId = '55555555-5555-5555-5555-555555555555'
const T = `/organizations/${orgId}`
const user = {
  id: '66666666-6666-6666-6666-666666666666',
  email: 'operator@example.com',
  is_active: true,
  created_at: '2026-11-07T12:00:00Z',
}
const response = (status: number, body?: unknown) =>
  new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

function setup(
  path: string,
  role: Role = 'owner',
  options: { conflict?: boolean; status?: Order['status']; anonymous?: boolean } = {},
) {
  let authenticated = !options.anonymous
  let name = 'Acme Operations'
  let products: Product[] = [
    { id: productId, organization_id: orgId, name: 'Wireless keyboard', sku: 'KEY-001' },
  ]
  let order: Order = {
    id: orderId,
    organization_id: orgId,
    status: options.status ?? 'pending',
    created_at: '2026-11-07T12:00:00Z',
    items: [{ id: 'line-1', product_id: productId, quantity: 4, allocations: [] }],
  }
  const members: Member[] = [
    { user_id: user.id, email: user.email, role, joined_at: user.created_at },
    { user_id: viewerId, email: 'viewer@example.com', role: 'viewer', joined_at: user.created_at },
  ]
  const requests: { method: string; path: string; body: unknown }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const pathname = url.pathname
      const method = init?.method ?? 'GET'
      const body: unknown = init?.body ? (JSON.parse(String(init.body)) as unknown) : undefined
      requests.push({ method, path: pathname, body })
      const org = { id: orgId, name, slug: 'acme-operations', role, created_at: user.created_at }
      if (pathname === '/users/me')
        return response(
          authenticated ? 200 : 401,
          authenticated ? user : { detail: 'Not authenticated' },
        )
      if (pathname === '/auth/login') {
        authenticated = true
        document.cookie = 'csrf_token=unit-signed; Path=/'
        return response(200, user)
      }
      if (pathname === '/auth/register') return response(201, user)
      if (pathname === '/auth/logout') {
        authenticated = false
        return response(204)
      }
      if (pathname === '/organizations') return response(200, [org])
      if (pathname === T && method === 'PATCH') {
        name = (body as { name: string }).name
        return response(200, { ...org, name })
      }
      if (pathname === T) return response(200, org)
      if (pathname === `${T}/members` && method === 'GET') return response(200, members)
      if (pathname === `${T}/members` && method === 'POST') {
        const value = body as { email: string; role: Role }
        const member = { ...value, user_id: 'new-member', joined_at: user.created_at }
        members.push(member)
        return response(201, member)
      }
      if (pathname.startsWith(`${T}/members/`) && method === 'DELETE') return response(204)
      if (pathname === `${T}/products` && method === 'GET') return response(200, products)
      if (pathname === `${T}/products` && method === 'POST') {
        const product = {
          id: viewerId,
          organization_id: orgId,
          ...(body as { name: string; sku: string }),
        }
        products.push(product)
        return response(201, product)
      }
      if (pathname === `${T}/products/${productId}` && method === 'DELETE') {
        products = []
        return response(204)
      }
      if (pathname === `${T}/products/${productId}`) return response(200, products[0])
      if (pathname === `${T}/warehouses`)
        return response(200, [
          { id: warehouseId, organization_id: orgId, name: 'Central', location: 'Riga' },
        ])
      if (pathname === `${T}/warehouses/${warehouseId}`)
        return response(200, {
          id: warehouseId,
          organization_id: orgId,
          name: 'Central',
          location: 'Riga',
        })
      if (pathname === `${T}/warehouses/${warehouseId}/inventory`)
        return response(200, [
          {
            id: 'stock-1',
            organization_id: orgId,
            warehouse_id: warehouseId,
            product_id: productId,
            quantity: 10,
            reserved_quantity: 4,
            available_quantity: 6,
          },
        ])
      if (
        pathname === `${T}/warehouses/${warehouseId}/inventory/${productId}` &&
        method === 'PATCH'
      )
        return response(200, {
          id: 'stock-1',
          product_id: productId,
          quantity: (body as { quantity: number }).quantity,
          reserved_quantity: 4,
          available_quantity: 6,
        })
      if (pathname === `${T}/orders` && method === 'GET') return response(200, [order])
      if (
        (pathname === `${T}/orders` && method === 'POST') ||
        (pathname === `${T}/orders/${orderId}` && method === 'PATCH')
      ) {
        order = {
          ...order,
          items: (body as { items: { product_id: string; quantity: number }[] }).items.map(
            (item, i) => ({ ...item, id: `line-${i}`, allocations: [] }),
          ),
        }
        return response(201, order)
      }
      if (pathname === `${T}/orders/${orderId}`) return response(200, order)
      if (pathname.startsWith(`${T}/orders/${orderId}/`) && method === 'POST') {
        if (options.conflict)
          return response(409, { detail: 'Insufficient inventory: requested=4, available=2' })
        order = {
          ...order,
          status: pathname.endsWith('/allocate')
            ? 'allocated'
            : pathname.endsWith('/fulfill')
              ? 'fulfilled'
              : 'cancelled',
        }
        return response(200, order)
      }
      if (pathname === '/health') return response(200, { status: 'ok' })
      throw new Error(`Unhandled mock: ${method} ${pathname}`)
    }),
  )
  document.cookie = 'csrf_token=unit-signed; Path=/'
  if (options.anonymous) document.cookie = 'csrf_token=; Max-Age=0; Path=/'
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={cache}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return { requests, cache }
}

describe('workspace screens with mocked HTTP only', () => {
  it('loads a real-data dashboard without invented statistics', async () => {
    setup(`/app/${orgId}/dashboard`)
    expect(await screen.findByRole('heading', { name: 'Everything in its place.' })).toBeVisible()
    expect(await screen.findByText(`#${orderId.slice(0, 8).toUpperCase()}`)).toBeVisible()
    expect(screen.queryByText(/revenue|sales trend/i)).not.toBeInTheDocument()
  })

  it('creates a product through its tenant endpoint and refreshes the catalog', async () => {
    const { requests } = setup(`/app/${orgId}/products`)
    const u = userEvent.setup()
    await u.click(await screen.findByRole('button', { name: 'New product' }))
    const dialog = await screen.findByRole('dialog', { name: 'New product' })
    await u.type(within(dialog).getByLabelText('Product name'), 'USB adapter')
    await u.type(within(dialog).getByLabelText(/^SKU/), 'USB-002')
    await u.click(within(dialog).getByRole('button', { name: 'Create product' }))
    expect(await screen.findByText('USB adapter')).toBeVisible()
    expect(
      requests.find((item) => item.method === 'POST' && item.path === `${T}/products`)?.body,
    ).toEqual({ name: 'USB adapter', sku: 'USB-002' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('keeps viewer business pages read-only, including a direct create-order URL', async () => {
    setup(`/app/${orgId}/orders/new`, 'viewer')
    expect(await screen.findByText('Your workspace is read-only')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Create order' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Members' })).not.toBeInTheDocument()
  })

  it('uses known-ID manager removal without making a forbidden directory request', async () => {
    const { requests } = setup(`/app/${orgId}/members`, 'manager')
    const u = userEvent.setup()
    await u.type(await screen.findByLabelText('Viewer user ID'), viewerId)
    await u.click(screen.getByRole('button', { name: 'Review removal' }))
    const dialog = await screen.findByRole('dialog', { name: 'Remove this member?' })
    await u.click(within(dialog).getByRole('button', { name: 'Remove member' }))
    await waitFor(() =>
      expect(
        requests.some(
          (item) => item.method === 'DELETE' && item.path === `${T}/members/${viewerId}`,
        ),
      ).toBe(true),
    )
    expect(requests.some((item) => item.method === 'GET' && item.path === `${T}/members`)).toBe(
      false,
    )
  })

  it('restricts admin member creation to manager/viewer and hides self removal', async () => {
    setup(`/app/${orgId}/members`, 'admin')
    const u = userEvent.setup()
    await u.click(await screen.findByRole('button', { name: 'Add member' }))
    const dialog = await screen.findByRole('dialog', { name: 'Add a team member' })
    expect(
      within(dialog)
        .getAllByRole('option')
        .map((option) => option.getAttribute('value')),
    ).toEqual(['manager', 'viewer'])
    expect(screen.queryByRole('button', { name: `Remove ${user.email}` })).not.toBeInTheDocument()
  })

  it('creates an order with product IDs and integer quantities only', async () => {
    const { requests } = setup(`/app/${orgId}/orders/new`)
    const u = userEvent.setup()
    await u.selectOptions(await screen.findByLabelText('Product 1'), productId)
    const quantity = screen.getByLabelText('Quantity 1')
    await u.clear(quantity)
    await u.type(quantity, '7')
    await u.click(screen.getByRole('button', { name: 'Create order' }))
    expect(
      await screen.findByRole('heading', { name: `Order #${orderId.slice(0, 8)}` }),
    ).toBeVisible()
    expect(
      requests.find((item) => item.method === 'POST' && item.path === `${T}/orders`)?.body,
    ).toEqual({ items: [{ product_id: productId, quantity: 7 }] })
  })

  it('requires confirmation and updates status after allocation succeeds', async () => {
    const { requests } = setup(`/app/${orgId}/orders/${orderId}`)
    const u = userEvent.setup()
    await u.click(await screen.findByRole('button', { name: 'Allocate stock' }))
    expect(requests.some((item) => item.path.endsWith('/allocate'))).toBe(false)
    const dialog = await screen.findByRole('dialog', { name: 'Allocate stock for this order?' })
    await u.click(within(dialog).getByRole('button', { name: 'Allocate stock' }))
    expect(await screen.findByRole('button', { name: 'Fulfill order' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument()
    expect(
      requests.some(
        (item) => item.method === 'POST' && item.path === `${T}/orders/${orderId}/allocate`,
      ),
    ).toBe(true)
  })

  it('shows a 409 without claiming a successful allocation', async () => {
    setup(`/app/${orgId}/orders/${orderId}`, 'owner', { conflict: true })
    const u = userEvent.setup()
    await u.click(await screen.findByRole('button', { name: 'Allocate stock' }))
    const dialog = await screen.findByRole('dialog')
    await u.click(within(dialog).getByRole('button', { name: 'Allocate stock' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Insufficient inventory')
    expect(screen.queryByRole('button', { name: 'Fulfill order' })).not.toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeVisible()
  })

  it.each(['fulfilled', 'cancelled'] as const)(
    'does not offer actions on %s orders',
    async (status) => {
      setup(`/app/${orgId}/orders/${orderId}`, 'owner', { status })
      await screen.findByRole('heading', { name: `Order #${orderId.slice(0, 8)}` })
      expect(
        screen.queryByRole('button', { name: /Allocate stock|Fulfill order|Cancel order|Delete/ }),
      ).not.toBeInTheDocument()
    },
  )

  it('displays server inventory fields and prevents removal of nonempty stock', async () => {
    setup(`/app/${orgId}/warehouses/${warehouseId}`)
    expect(await screen.findByText('Wireless keyboard')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Remove inventory entry' })).toBeDisabled()
    const table = screen.getByRole('table')
    expect(within(table).getByText('10')).toBeVisible()
    expect(within(table).getByText('4')).toBeVisible()
    expect(within(table).getByText('6')).toBeVisible()
  })

  it('logs out and removes tenant data from the query cache', async () => {
    const { cache } = setup(`/app/${orgId}/products`)
    const u = userEvent.setup()
    await screen.findByText('Wireless keyboard')
    await u.click(screen.getByRole('button', { name: 'Log out' }))
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible()
    expect(cache.getQueryCache().findAll({ queryKey: ['tenant'] })).toHaveLength(0)
    expect(cache.getQueryData(['me'])).toBeNull()
  })

  it('signs in using cookies and reaches the organization picker', async () => {
    setup('/login', 'owner', { anonymous: true })
    const u = userEvent.setup()
    await u.type(await screen.findByLabelText('Email address'), user.email)
    await u.type(screen.getByLabelText('Password'), 'test-password')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled())
    await u.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('heading', { name: 'Choose your workspace' })).toBeVisible()
    expect(await screen.findByRole('heading', { name: 'Acme Operations' })).toBeVisible()
  })

  it('drops an account cache on cross-tab logout metadata', async () => {
    const { cache } = setup(`/app/${orgId}/products`)
    await screen.findByText('Wireless keyboard')
    act(() => apiClient.sessionChanged('logout'))
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible()
    expect(cache.getQueryCache().findAll({ queryKey: ['tenant'] })).toHaveLength(0)
  })
})
