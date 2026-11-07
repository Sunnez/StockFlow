import { formatDate, shortId } from '../lib/format'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, ArrowUpRight, Check, PackageCheck, Pencil, Plus, Trash2 } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { ApiError } from '../api/client'
import type { Order, OrderItemInput } from '../api/types'
import { useTenant } from '../components/layout'
import {
  BackLink,
  Button,
  ConfirmDialog,
  Empty,
  ErrorNotice,
  ErrorState,
  Field,
  Loading,
  PageHeader,
  Pagination,
  StatusBadge,
  useNotice,
} from '../components/ui'
import { canWrite, INT_MAX, orderActions, UUID_PATTERN, validQuantity } from '../lib/permissions'
import { tenantKey, useProducts, useRefreshTenant } from '../lib/queries'

export function OrdersPage() {
  const org = useTenant()
  const [offset, setOffset] = useState(0)
  const orders = useQuery({
    queryKey: [...tenantKey(org.id), 'orders', { limit: 20, offset }],
    queryFn: ({ signal }) => api.orders.list(org.id, { limit: 20, offset }, signal),
  })
  const action = canWrite(org.role) && (
    <Link className="btn btn-primary" to="new">
      <Plus size={17} />
      New order
    </Link>
  )
  return (
    <>
      <PageHeader
        eyebrow="ORDER MANAGEMENT"
        title="Orders"
        description="From the first item to the final delivery. Keep every order moving."
        action={action}
      />
      <section className="panel">
        <div className="panel-heading">
          <h2>All orders</h2>
          <span className="subtle-badge">Latest first</span>
        </div>
        {orders.isPending ? (
          <Loading label="Loading orders..." />
        ) : orders.isError ? (
          <ErrorState
            error={orders.error}
            retry={() => {
              void orders.refetch()
            }}
          />
        ) : (
          <>
            {orders.data.length === 0 ? (
              <Empty
                title={offset ? 'No orders on this page' : 'Your next order starts here'}
                description="Create an order from your product catalog, then allocate available stock."
                action={!offset && action}
              />
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Order</th>
                      <th>Status</th>
                      <th className="number-cell">Line items</th>
                      <th className="number-cell">Units</th>
                      <th>Created</th>
                      <th>
                        <span className="sr-only">Details</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.data.map((order) => (
                      <tr key={order.id}>
                        <td>
                          <Link className="order-link" to={order.id}>
                            #{shortId(order.id)}
                          </Link>
                        </td>
                        <td>
                          <StatusBadge status={order.status} />
                        </td>
                        <td className="number-cell">{order.items.length}</td>
                        <td className="number-cell">
                          {order.items
                            .reduce((sum, item) => sum + item.quantity, 0)
                            .toLocaleString()}
                        </td>
                        <td>{formatDate(order.created_at)}</td>
                        <td className="text-right">
                          <Link
                            className="table-open"
                            aria-label={`View order ${shortId(order.id)}`}
                            to={order.id}
                          >
                            <ArrowUpRight size={18} />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <Pagination
              offset={offset}
              count={orders.data.length}
              onChange={setOffset}
              busy={orders.isFetching}
            />
          </>
        )}
      </section>
    </>
  )
}

type EditorLine = { key: string; product_id: string; quantity: string }
function OrderForm({ initial }: { initial?: Order }) {
  const org = useTenant()
  const products = useProducts(org.id)
  const navigate = useNavigate()
  const cache = useQueryClient()
  const refresh = useRefreshTenant(org.id)
  const notice = useNotice()
  const [lines, setLines] = useState<EditorLine[]>(() =>
    initial
      ? initial.items.map((item) => ({
          key: item.id,
          product_id: item.product_id,
          quantity: String(item.quantity),
        }))
      : [{ key: crypto.randomUUID(), product_id: '', quantity: '1' }],
  )
  const [validationError, setValidationError] = useState<unknown>(null)
  const mutation = useMutation({
    mutationFn: (items: OrderItemInput[]) =>
      initial ? api.orders.update(org.id, initial.id, items) : api.orders.create(org.id, items),
    onSuccess: async (order) => {
      cache.setQueryData([...tenantKey(org.id), 'orders', order.id], order)
      await refresh()
      navigate(`/app/${org.id}/orders/${order.id}`, { replace: true })
      notice(initial ? 'Order updated.' : 'Order created. Ready to allocate stock.')
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) void refresh()
    },
  })
  function updateLine(key: string, field: 'product_id' | 'quantity', value: string) {
    setLines((current) =>
      current.map((line) => (line.key === key ? { ...line, [field]: value } : line)),
    )
  }
  function submit() {
    setValidationError(null)
    const items: OrderItemInput[] = []
    const seen = new Set<string>()
    for (const line of lines) {
      const quantity = validQuantity(line.quantity, 1)
      if (!line.product_id || seen.has(line.product_id) || quantity === null) {
        setValidationError(
          new Error(
            `Choose a unique product for each line and a whole quantity from 1 to ${INT_MAX}.`,
          ),
        )
        return
      }
      seen.add(line.product_id)
      items.push({ product_id: line.product_id, quantity })
    }
    if (!items.length) {
      setValidationError(new Error('Add at least one product.'))
      return
    }
    mutation.mutate(items)
  }
  if (products.isPending) return <Loading label="Loading product catalog..." />
  if (products.isError)
    return (
      <ErrorState
        error={products.error}
        retry={() => {
          void products.refetch()
        }}
      />
    )
  if (!products.data.length)
    return (
      <section className="panel">
        <Empty
          title="Start with a product"
          description="Add a catalog product before creating an order."
          action={
            <Link className="btn btn-primary" to={`/app/${org.id}/products`}>
              Go to products <ArrowRight size={16} />
            </Link>
          }
        />
      </section>
    )
  return (
    <section className="panel">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        <div className="panel-heading">
          <div>
            <h2>Order items</h2>
            <p>One product per line. Stock is reserved only after allocation.</p>
          </div>
          <span className="subtle-badge">
            {lines.length} {lines.length === 1 ? 'line' : 'lines'}
          </span>
        </div>
        <fieldset className="order-editor" disabled={mutation.isPending}>
          {lines.map((line, index) => (
            <div className="order-editor-line" key={line.key}>
              <span className="line-number">{String(index + 1).padStart(2, '0')}</span>
              <Field label={`Product ${index + 1}`}>
                <select
                  required
                  value={line.product_id}
                  onChange={(event) => updateLine(line.key, 'product_id', event.target.value)}
                >
                  <option value="">Select a product</option>
                  {products.data
                    .filter(
                      (product) =>
                        product.id === line.product_id ||
                        !lines.some((other) => other.product_id === product.id),
                    )
                    .map((product) => (
                      <option value={product.id} key={product.id}>
                        {product.name} - {product.sku}
                      </option>
                    ))}
                </select>
              </Field>
              <Field label={`Quantity ${index + 1}`}>
                <input
                  type="number"
                  required
                  min={1}
                  max={INT_MAX}
                  step={1}
                  value={line.quantity}
                  onChange={(event) => updateLine(line.key, 'quantity', event.target.value)}
                />
              </Field>
              <Button
                variant="ghost"
                className="remove-line"
                aria-label={`Remove line ${index + 1}`}
                disabled={lines.length === 1}
                onClick={() =>
                  setLines((current) => current.filter((other) => other.key !== line.key))
                }
              >
                <Trash2 size={17} />
              </Button>
            </div>
          ))}
          <Button
            variant="secondary"
            onClick={() =>
              setLines((current) => [
                ...current,
                { key: crypto.randomUUID(), product_id: '', quantity: '1' },
              ])
            }
            disabled={lines.length >= products.data.length}
          >
            <Plus size={16} />
            Add line item
          </Button>
        </fieldset>
        <div className="panel-body pt-0">
          <ErrorNotice error={validationError || mutation.error} />
        </div>
        <div className="editor-footer">
          <p>
            <PackageCheck size={17} />
            {initial ? 'Only pending orders can be edited.' : 'New orders start as pending.'}
          </p>
          <div className="flex gap-3">
            <Button
              variant="secondary"
              disabled={mutation.isPending}
              onClick={() =>
                navigate(initial ? `/app/${org.id}/orders/${initial.id}` : `/app/${org.id}/orders`)
              }
            >
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Saving...' : initial ? 'Save changes' : 'Create order'}
              <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      </form>
    </section>
  )
}

export function OrderEditor({ editing = false }: { editing?: boolean }) {
  const org = useTenant()
  const { orderId = '' } = useParams()
  const query = useQuery({
    queryKey: [...tenantKey(org.id), 'orders', orderId],
    queryFn: ({ signal }) => api.orders.get(org.id, orderId, signal),
    enabled: editing && UUID_PATTERN.test(orderId),
  })
  if (!canWrite(org.role))
    return (
      <div className="panel">
        <Empty
          title="Your workspace is read-only"
          description="An owner, admin or manager can create and update orders."
        />
      </div>
    )
  if (editing && !UUID_PATTERN.test(orderId))
    return <ErrorState error={new Error('Invalid order address.')} />
  if (editing && query.isPending) return <Loading />
  if (editing && query.isError)
    return (
      <ErrorState
        error={query.error}
        retry={() => {
          void query.refetch()
        }}
      />
    )
  if (editing && query.data?.status !== 'pending')
    return (
      <div className="panel">
        <Empty
          title="This order can no longer be edited"
          description="Only pending orders can be changed. Return to the order to see its latest status."
          action={
            <Link className="btn btn-secondary" to={`/app/${org.id}/orders/${orderId}`}>
              View order
            </Link>
          }
        />
      </div>
    )
  return (
    <>
      <BackLink to={editing ? `/app/${org.id}/orders/${orderId}` : `/app/${org.id}/orders`}>
        Back to {editing ? 'order' : 'orders'}
      </BackLink>
      <PageHeader
        eyebrow="ORDER MANAGEMENT"
        title={editing ? `Edit order #${shortId(orderId)}` : 'Create an order'}
        description="Choose your products and quantities. We'll take care of the next steps."
      />
      <OrderForm
        initial={editing ? query.data : undefined}
        key={editing ? query.data?.id : 'new'}
      />
    </>
  )
}

type Action = 'allocate' | 'fulfill' | 'cancel' | 'delete'
const actionCopy: Record<Action, { title: string; description: string; label: string }> = {
  allocate: {
    title: 'Allocate stock for this order?',
    description:
      'Available stock will be reserved across warehouses. If any product has insufficient stock, the entire allocation will be rolled back.',
    label: 'Allocate stock',
  },
  fulfill: {
    title: 'Fulfill this order?',
    description:
      'Reserved stock will be deducted from physical inventory. This completes the order and cannot be undone here.',
    label: 'Fulfill order',
  },
  cancel: {
    title: 'Cancel this order?',
    description:
      'The order will become cancelled. Any existing reservations will be released, while allocation history is preserved.',
    label: 'Cancel order',
  },
  delete: {
    title: 'Delete this order?',
    description:
      'This permanently removes a pending order and its items. This action cannot be undone.',
    label: 'Delete order',
  },
}

export function OrderDetail() {
  const org = useTenant()
  const { orderId = '' } = useParams()
  const navigate = useNavigate()
  const products = useProducts(org.id)
  const cache = useQueryClient()
  const notice = useNotice()
  const refresh = useRefreshTenant(org.id)
  const [action, setAction] = useState<Action | null>(null)
  const query = useQuery({
    queryKey: [...tenantKey(org.id), 'orders', orderId],
    queryFn: ({ signal }) => api.orders.get(org.id, orderId, signal),
    enabled: UUID_PATTERN.test(orderId),
  })
  const mutation = useMutation<Order | void, Error, Action>({
    mutationFn: (value: Action) =>
      value === 'delete'
        ? api.orders.remove(org.id, orderId)
        : api.orders.transition(org.id, orderId, value),
    onSuccess: async (updated, value) => {
      setAction(null)
      if (value === 'delete') navigate(`/app/${org.id}/orders`, { replace: true })
      else if (updated) cache.setQueryData([...tenantKey(org.id), 'orders', orderId], updated)
      await refresh()
      notice(
        value === 'delete'
          ? 'Order deleted.'
          : `Order ${value === 'allocate' ? 'allocated' : value === 'fulfill' ? 'fulfilled' : 'cancelled'}.`,
      )
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) void refresh()
    },
  })
  if (!UUID_PATTERN.test(orderId)) return <ErrorState error={new Error('Invalid order address.')} />
  if (query.isPending) return <Loading />
  if (query.isError)
    return (
      <ErrorState
        error={query.error}
        retry={() => {
          void query.refetch()
        }}
      />
    )
  const order = query.data
  const catalog = new Map(products.data?.map((product) => [product.id, product]))
  const choose = (value: Action) => {
    mutation.reset()
    setAction(value)
  }
  return (
    <>
      <BackLink to={`/app/${org.id}/orders`}>Back to orders</BackLink>
      <PageHeader
        eyebrow="ORDER DETAILS"
        title={`Order #${shortId(order.id)}`}
        description={`Created ${formatDate(order.created_at)} - ${order.items.length} line ${order.items.length === 1 ? 'item' : 'items'}`}
        action={
          canWrite(org.role) && (
            <>
              {order.status === 'pending' && (
                <>
                  <Link className="btn btn-secondary" to="edit">
                    <Pencil size={16} />
                    Edit
                  </Link>
                  <Button variant="ghost" onClick={() => choose('delete')}>
                    <Trash2 size={16} />
                    Delete
                  </Button>
                </>
              )}
              {orderActions(order.status).map((value) => (
                <Button
                  key={value}
                  variant={value === 'cancel' ? 'secondary' : 'primary'}
                  onClick={() => choose(value)}
                >
                  {value === 'fulfill' && <Check size={17} />}
                  {actionCopy[value].label}
                </Button>
              ))}
            </>
          )
        }
      />
      <div className="order-summary">
        <StatusBadge status={order.status} />
        <span>
          {order.status === 'pending'
            ? 'Ready for stock allocation'
            : order.status === 'allocated'
              ? 'Stock reserved. Ready to fulfill.'
              : order.status === 'fulfilled'
                ? 'Completed. Physical stock has been updated.'
                : 'Cancelled. No active reservation remains.'}
        </span>
        <code>{order.id}</code>
      </div>
      {products.isError && (
        <ErrorNotice
          error={new Error('Product names are unavailable. Product IDs are displayed instead.')}
        />
      )}
      <section className="panel">
        <div className="panel-heading">
          <h2>Products in this order</h2>
          <span className="subtle-badge">
            {order.items.reduce((sum, item) => sum + item.quantity, 0).toLocaleString()} units
          </span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>SKU</th>
                <th className="number-cell">Quantity</th>
                <th className="number-cell">Allocation history</th>
              </tr>
            </thead>
            <tbody>
              {order.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Link className="text-link" to={`/app/${org.id}/products/${item.product_id}`}>
                      {catalog.get(item.product_id)?.name ?? item.product_id}
                    </Link>
                  </td>
                  <td>
                    <span className="sku">
                      {catalog.get(item.product_id)?.sku ?? 'Unavailable'}
                    </span>
                  </td>
                  <td className="number-cell">{item.quantity.toLocaleString()}</td>
                  <td className="number-cell">
                    {item.allocations
                      .reduce((sum, allocation) => sum + allocation.quantity, 0)
                      .toLocaleString()}{' '}
                    units
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel mt-6">
        <div className="panel-heading">
          <div>
            <h2>Stock allocations</h2>
            <p>Inventory entries that supply this order.</p>
          </div>
        </div>
        {order.items.every((item) => item.allocations.length === 0) ? (
          <Empty
            title="No allocations yet"
            description="Allocate this pending order to reserve available stock. All products must have enough stock."
          />
        ) : (
          <div className="allocation-list">
            {order.items.map(
              (item) =>
                item.allocations.length > 0 && (
                  <div className="allocation-group" key={item.id}>
                    <h3>{catalog.get(item.product_id)?.name ?? item.product_id}</h3>
                    {item.allocations.map((allocation) => (
                      <div className="allocation-row" key={allocation.id}>
                        <div>
                          <span className="table-secondary">Inventory entry</span>
                          <code>{allocation.inventory_id}</code>
                        </div>
                        <span>{allocation.quantity.toLocaleString()} units</span>
                      </div>
                    ))}
                  </div>
                ),
            )}
            {(order.status === 'fulfilled' || order.status === 'cancelled') && (
              <p className="info-note">
                These are historical allocations. They do not represent current stock reservations.
              </p>
            )}
          </div>
        )}
      </section>
      {action && (
        <ConfirmDialog
          {...actionCopy[action]}
          confirmLabel={actionCopy[action].label}
          onClose={() => setAction(null)}
          onConfirm={() => mutation.mutate(action)}
          busy={mutation.isPending}
          error={mutation.error}
          danger={action === 'delete' || action === 'cancel'}
        />
      )}
    </>
  )
}
