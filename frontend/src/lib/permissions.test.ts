import { describe, expect, it } from 'vitest'
import {
  assignableRoles,
  canManage,
  canRemove,
  canWrite,
  INT_MAX,
  orderActions,
  validQuantity,
} from './permissions'
import type { Role } from '../api/types'

describe('backend role policy reflected in the UI', () => {
  it.each(['owner', 'admin', 'manager'] satisfies Role[])(
    '%s can write business resources',
    (role) => expect(canWrite(role)).toBe(true),
  )
  it('keeps viewer read-only and limits organization administration', () => {
    expect(canWrite('viewer')).toBe(false)
    expect(canManage('manager')).toBe(false)
    expect(assignableRoles('owner')).toEqual(['admin', 'manager', 'viewer'])
    expect(assignableRoles('admin')).toEqual(['manager', 'viewer'])
    expect(assignableRoles('manager')).toEqual([])
  })
  it('preserves manager removal of viewers, with no self/peer/higher removal', () => {
    expect(canRemove('manager', 'viewer', 'actor', 'target')).toBe(true)
    expect(canRemove('admin', 'owner', 'actor', 'target')).toBe(false)
    expect(canRemove('admin', 'admin', 'actor', 'target')).toBe(false)
    expect(canRemove('owner', 'viewer', 'same', 'same')).toBe(false)
    expect(canRemove('viewer', 'viewer', 'actor', 'target')).toBe(false)
  })
  it('offers exactly the supported order transitions', () => {
    expect(orderActions('pending')).toEqual(['allocate', 'cancel'])
    expect(orderActions('allocated')).toEqual(['fulfill', 'cancel'])
    expect(orderActions('fulfilled')).toEqual([])
    expect(orderActions('cancelled')).toEqual([])
  })
})
describe('frontend quantity validation (backend I1 unchanged)', () => {
  it.each(['-1', '1.5', '1e3', '', 'NaN', '2147483648'])('rejects %s', (value) =>
    expect(validQuantity(value)).toBeNull(),
  )
  it('accepts database-supported integer bounds and respects reserved minimum', () => {
    expect(validQuantity('0')).toBe(0)
    expect(validQuantity(String(INT_MAX), 1)).toBe(INT_MAX)
    expect(validQuantity('5', 6)).toBeNull()
  })
})
