import type { OrderStatus, Role } from '../api/types'

const levels: Record<Role, number> = { owner: 4, admin: 3, manager: 2, viewer: 1 }
export const canWrite = (role: Role) => role !== 'viewer'
export const canManage = (role: Role) => role === 'owner' || role === 'admin'
export const canRemove = (actor: Role, target: Role, actorId: string, targetId: string) =>
  actorId !== targetId && levels[actor] > levels[target]
export const assignableRoles = (role: Role): Role[] =>
  role === 'owner' ? ['admin', 'manager', 'viewer'] : role === 'admin' ? ['manager', 'viewer'] : []
export function orderActions(status: OrderStatus): ('allocate' | 'fulfill' | 'cancel')[] {
  if (status === 'pending') return ['allocate', 'cancel']
  if (status === 'allocated') return ['fulfill', 'cancel']
  return []
}
export const INT_MAX = 2147483647
export const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
export function validQuantity(value: string, min = 0): number | null {
  if (!/^\d+$/.test(value)) return null
  const quantity = Number(value)
  return Number.isSafeInteger(quantity) && quantity >= min && quantity <= INT_MAX ? quantity : null
}
