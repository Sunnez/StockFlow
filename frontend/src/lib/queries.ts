import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, allPages } from '../api/endpoints'

export const tenantKey = (org: string) => ['tenant', org] as const
export function useOrganizations() {
  return useQuery({
    queryKey: ['organizations'],
    queryFn: ({ signal }) => allPages(api.organizations.list, signal),
  })
}
export function useProducts(org: string) {
  return useQuery({
    queryKey: [...tenantKey(org), 'products', 'all'],
    queryFn: ({ signal }) => allPages((page, s) => api.products.list(org, page, s), signal),
  })
}
export function useWarehouses(org: string) {
  return useQuery({
    queryKey: [...tenantKey(org), 'warehouses', 'all'],
    queryFn: ({ signal }) => allPages((page, s) => api.warehouses.list(org, page, s), signal),
  })
}
export function useRefreshTenant(org: string) {
  const cache = useQueryClient()
  return () => cache.invalidateQueries({ queryKey: tenantKey(org) })
}
