export type Role = 'owner' | 'admin' | 'manager' | 'viewer'
export type OrderStatus = 'pending' | 'allocated' | 'fulfilled' | 'cancelled'

export interface User {
  id: string
  email: string
  is_active: boolean
  created_at: string
}
export interface Credentials {
  email: string
  password: string
}
export interface Organization {
  id: string
  name: string
  slug: string
  created_at: string
}
export interface OrganizationWithRole extends Organization {
  role: Role
}
export interface Member {
  user_id: string
  email: string
  role: Role
  joined_at: string
}
export interface Product {
  id: string
  organization_id: string
  name: string
  sku: string
}
export interface Warehouse {
  id: string
  organization_id: string
  name: string
  location: string
}
export interface Inventory {
  id: string
  organization_id: string
  product_id: string
  warehouse_id: string
  quantity: number
  reserved_quantity: number
  available_quantity: number
}
export interface OrderItemInput {
  product_id: string
  quantity: number
}
export interface Allocation {
  id: string
  inventory_id: string
  quantity: number
}
export interface OrderItem extends OrderItemInput {
  id: string
  allocations: Allocation[]
}
export interface Order {
  id: string
  organization_id: string
  status: OrderStatus
  created_at: string
  items: OrderItem[]
}
export interface Page {
  limit: number
  offset: number
}
