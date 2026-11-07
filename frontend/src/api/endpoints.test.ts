import { describe, expect, it, vi } from 'vitest'
import { api, allPages } from './endpoints'

const org = '11111111-1111-1111-1111-111111111111'
const resource = '22222222-2222-2222-2222-222222222222'
const product = '33333333-3333-3333-3333-333333333333'
const T = `/organizations/${org}`

describe('typed endpoint contract', () => {
  const cases: [string, string, () => Promise<unknown>, unknown?][] = [
    ['GET', '/health', () => api.health()],
    ['GET', '/users/me', () => api.me()],
    [
      'POST',
      '/auth/register',
      () => api.register({ email: 'test@example.com', password: 'test-password' }),
      { email: 'test@example.com', password: 'test-password' },
    ],
    [
      'POST',
      '/auth/login',
      () => api.login({ email: 'test@example.com', password: 'test-password' }),
      { email: 'test@example.com', password: 'test-password' },
    ],
    ['POST', '/auth/logout', () => api.logout()],
    [
      'GET',
      '/organizations?limit=20&offset=40',
      () => api.organizations.list({ limit: 20, offset: 40 }),
    ],
    ['POST', '/organizations', () => api.organizations.create('Acme'), { name: 'Acme' }],
    ['GET', T, () => api.organizations.get(org)],
    ['PATCH', T, () => api.organizations.rename(org, 'Renamed'), { name: 'Renamed' }],
    [
      'GET',
      `${T}/members?limit=20&offset=0`,
      () => api.organizations.members(org, { limit: 20, offset: 0 }),
    ],
    [
      'POST',
      `${T}/members`,
      () => api.organizations.addMember(org, 'member@example.com', 'viewer'),
      { email: 'member@example.com', role: 'viewer' },
    ],
    ['DELETE', `${T}/members/${resource}`, () => api.organizations.removeMember(org, resource)],
    [
      'GET',
      `${T}/products?limit=20&offset=0`,
      () => api.products.list(org, { limit: 20, offset: 0 }),
    ],
    [
      'POST',
      `${T}/products`,
      () => api.products.create(org, { name: 'Item', sku: 'SKU' }),
      { name: 'Item', sku: 'SKU' },
    ],
    ['GET', `${T}/products/${product}`, () => api.products.get(org, product)],
    [
      'PATCH',
      `${T}/products/${product}`,
      () => api.products.update(org, product, { name: 'New', sku: 'NEW' }),
      { name: 'New', sku: 'NEW' },
    ],
    ['DELETE', `${T}/products/${product}`, () => api.products.remove(org, product)],
    [
      'GET',
      `${T}/warehouses?limit=20&offset=0`,
      () => api.warehouses.list(org, { limit: 20, offset: 0 }),
    ],
    [
      'POST',
      `${T}/warehouses`,
      () => api.warehouses.create(org, { name: 'Central', location: 'Riga' }),
      { name: 'Central', location: 'Riga' },
    ],
    ['GET', `${T}/warehouses/${resource}`, () => api.warehouses.get(org, resource)],
    [
      'PATCH',
      `${T}/warehouses/${resource}`,
      () => api.warehouses.update(org, resource, { name: 'Updated', location: 'Riga' }),
      { name: 'Updated', location: 'Riga' },
    ],
    ['DELETE', `${T}/warehouses/${resource}`, () => api.warehouses.remove(org, resource)],
    [
      'GET',
      `${T}/warehouses/${resource}/inventory?limit=20&offset=0`,
      () => api.inventory.list(org, resource, { limit: 20, offset: 0 }),
    ],
    [
      'POST',
      `${T}/warehouses/${resource}/inventory`,
      () => api.inventory.create(org, resource, product, 5),
      { product_id: product, quantity: 5 },
    ],
    [
      'PATCH',
      `${T}/warehouses/${resource}/inventory/${product}`,
      () => api.inventory.update(org, resource, product, 8),
      { quantity: 8 },
    ],
    [
      'DELETE',
      `${T}/warehouses/${resource}/inventory/${product}`,
      () => api.inventory.remove(org, resource, product),
    ],
    ['GET', `${T}/orders?limit=20&offset=0`, () => api.orders.list(org, { limit: 20, offset: 0 })],
    [
      'POST',
      `${T}/orders`,
      () => api.orders.create(org, [{ product_id: product, quantity: 2 }]),
      { items: [{ product_id: product, quantity: 2 }] },
    ],
    ['GET', `${T}/orders/${resource}`, () => api.orders.get(org, resource)],
    [
      'PATCH',
      `${T}/orders/${resource}`,
      () => api.orders.update(org, resource, [{ product_id: product, quantity: 3 }]),
      { items: [{ product_id: product, quantity: 3 }] },
    ],
    ['DELETE', `${T}/orders/${resource}`, () => api.orders.remove(org, resource)],
    [
      'POST',
      `${T}/orders/${resource}/allocate`,
      () => api.orders.transition(org, resource, 'allocate'),
    ],
    [
      'POST',
      `${T}/orders/${resource}/fulfill`,
      () => api.orders.transition(org, resource, 'fulfill'),
    ],
    [
      'POST',
      `${T}/orders/${resource}/cancel`,
      () => api.orders.transition(org, resource, 'cancel'),
    ],
  ]
  it.each(cases)('%s %s', async (method, path, execute, body) => {
    const transport = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(method === 'DELETE' || path === '/auth/logout' ? null : JSON.stringify({}), {
        status: method === 'DELETE' || path === '/auth/logout' ? 204 : 200,
      }),
    )
    vi.stubGlobal('fetch', transport)
    await execute()
    const call = transport.mock.calls[0]
    expect(call?.[0]).toBe(`http://localhost:8000${path}`)
    expect(call?.[1]?.method).toBe(method)
    expect(call?.[1]?.credentials).toBe('include')
    expect(call?.[1]?.body).toBe(body === undefined ? undefined : JSON.stringify(body))
    expect(transport).toHaveBeenCalledTimes(1)
  })

  it('loads complete catalogs beyond the first 100 records', async () => {
    const load = vi.fn(async ({ offset }: { offset: number }) =>
      Array.from({ length: offset === 0 ? 100 : 7 }, (_, i) => offset + i),
    )
    const rows = await allPages(load)
    expect(rows).toHaveLength(107)
    expect(load.mock.calls.map(([page]) => page.offset)).toEqual([0, 100])
  })
})
