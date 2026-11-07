import { apiClient } from './client'
import type {
  Credentials,
  Inventory,
  Member,
  Order,
  OrderItemInput,
  Organization,
  OrganizationWithRole,
  Page,
  Product,
  Role,
  User,
  Warehouse,
} from './types'

const id = encodeURIComponent
const tenant = (org: string) => `/organizations/${id(org)}`
const pageQuery = (page: Page) => `?limit=${page.limit}&offset=${page.offset}`

export const api = {
  health: (signal?: AbortSignal) =>
    apiClient.request<{ status: string }>('/health', { signal, auth: false }),
  me: (signal?: AbortSignal) => apiClient.request<User>('/users/me', { signal }),
  register: (body: Credentials) =>
    apiClient.request<User>('/auth/register', { method: 'POST', body, auth: false }),
  login: (body: Credentials) => apiClient.authAction<User>('/auth/login', body),
  logout: () => apiClient.authAction<void>('/auth/logout'),
  organizations: {
    list: (page: Page, signal?: AbortSignal) =>
      apiClient.request<OrganizationWithRole[]>(`/organizations${pageQuery(page)}`, { signal }),
    get: (org: string, signal?: AbortSignal) =>
      apiClient.request<OrganizationWithRole>(tenant(org), { signal }),
    create: (name: string) =>
      apiClient.request<Organization>('/organizations', { method: 'POST', body: { name } }),
    rename: (org: string, name: string) =>
      apiClient.request<Organization>(tenant(org), { method: 'PATCH', body: { name } }),
    members: (org: string, page: Page, signal?: AbortSignal) =>
      apiClient.request<Member[]>(`${tenant(org)}/members${pageQuery(page)}`, { signal }),
    addMember: (org: string, email: string, role: Role) =>
      apiClient.request<Member>(`${tenant(org)}/members`, {
        method: 'POST',
        body: { email, role },
      }),
    removeMember: (org: string, user: string) =>
      apiClient.request<void>(`${tenant(org)}/members/${id(user)}`, { method: 'DELETE' }),
  },
  products: {
    list: (org: string, page: Page, signal?: AbortSignal) =>
      apiClient.request<Product[]>(`${tenant(org)}/products${pageQuery(page)}`, { signal }),
    get: (org: string, product: string, signal?: AbortSignal) =>
      apiClient.request<Product>(`${tenant(org)}/products/${id(product)}`, { signal }),
    create: (org: string, body: Pick<Product, 'name' | 'sku'>) =>
      apiClient.request<Product>(`${tenant(org)}/products`, { method: 'POST', body }),
    update: (org: string, product: string, body: Pick<Product, 'name' | 'sku'>) =>
      apiClient.request<Product>(`${tenant(org)}/products/${id(product)}`, {
        method: 'PATCH',
        body,
      }),
    remove: (org: string, product: string) =>
      apiClient.request<void>(`${tenant(org)}/products/${id(product)}`, { method: 'DELETE' }),
  },
  warehouses: {
    list: (org: string, page: Page, signal?: AbortSignal) =>
      apiClient.request<Warehouse[]>(`${tenant(org)}/warehouses${pageQuery(page)}`, { signal }),
    get: (org: string, warehouse: string, signal?: AbortSignal) =>
      apiClient.request<Warehouse>(`${tenant(org)}/warehouses/${id(warehouse)}`, { signal }),
    create: (org: string, body: Pick<Warehouse, 'name' | 'location'>) =>
      apiClient.request<Warehouse>(`${tenant(org)}/warehouses`, { method: 'POST', body }),
    update: (org: string, warehouse: string, body: Pick<Warehouse, 'name' | 'location'>) =>
      apiClient.request<Warehouse>(`${tenant(org)}/warehouses/${id(warehouse)}`, {
        method: 'PATCH',
        body,
      }),
    remove: (org: string, warehouse: string) =>
      apiClient.request<void>(`${tenant(org)}/warehouses/${id(warehouse)}`, { method: 'DELETE' }),
  },
  inventory: {
    list: (org: string, warehouse: string, page: Page, signal?: AbortSignal) =>
      apiClient.request<Inventory[]>(
        `${tenant(org)}/warehouses/${id(warehouse)}/inventory${pageQuery(page)}`,
        { signal },
      ),
    create: (org: string, warehouse: string, product_id: string, quantity: number) =>
      apiClient.request<Inventory>(`${tenant(org)}/warehouses/${id(warehouse)}/inventory`, {
        method: 'POST',
        body: { product_id, quantity },
      }),
    update: (org: string, warehouse: string, product: string, quantity: number) =>
      apiClient.request<Inventory>(
        `${tenant(org)}/warehouses/${id(warehouse)}/inventory/${id(product)}`,
        { method: 'PATCH', body: { quantity } },
      ),
    remove: (org: string, warehouse: string, product: string) =>
      apiClient.request<void>(
        `${tenant(org)}/warehouses/${id(warehouse)}/inventory/${id(product)}`,
        { method: 'DELETE' },
      ),
  },
  orders: {
    list: (org: string, page: Page, signal?: AbortSignal) =>
      apiClient.request<Order[]>(`${tenant(org)}/orders${pageQuery(page)}`, { signal }),
    get: (org: string, order: string, signal?: AbortSignal) =>
      apiClient.request<Order>(`${tenant(org)}/orders/${id(order)}`, { signal }),
    create: (org: string, items: OrderItemInput[]) =>
      apiClient.request<Order>(`${tenant(org)}/orders`, { method: 'POST', body: { items } }),
    update: (org: string, order: string, items: OrderItemInput[]) =>
      apiClient.request<Order>(`${tenant(org)}/orders/${id(order)}`, {
        method: 'PATCH',
        body: { items },
      }),
    remove: (org: string, order: string) =>
      apiClient.request<void>(`${tenant(org)}/orders/${id(order)}`, { method: 'DELETE' }),
    transition: (org: string, order: string, action: 'allocate' | 'fulfill' | 'cancel') =>
      apiClient.request<Order>(`${tenant(org)}/orders/${id(order)}/${action}`, { method: 'POST' }),
  },
}

// The API has array pages, no total-count endpoint. Read all pages only for
// complete selectors and honest dashboard counts, with request cancellation.
export async function allPages<T>(
  load: (page: Page, signal?: AbortSignal) => Promise<T[]>,
  signal?: AbortSignal,
): Promise<T[]> {
  const result: T[] = []
  for (let offset = 0; ; offset += 100) {
    if (signal?.aborted) throw signal.reason
    const rows = await load({ limit: 100, offset }, signal)
    result.push(...rows)
    if (rows.length < 100) return result
  }
}
