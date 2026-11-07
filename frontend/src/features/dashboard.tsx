import { formatDate, shortId } from '../lib/format'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Boxes, Package, Plus, ShoppingCart, Warehouse } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, allPages } from '../api/endpoints'
import { useTenant } from '../components/layout'
import { Empty, ErrorNotice, Loading, PageHeader, StatusBadge } from '../components/ui'
import { canWrite } from '../lib/permissions'
import { tenantKey, useProducts, useWarehouses } from '../lib/queries'

export function DashboardPage() {
  const org = useTenant()
  const products = useProducts(org.id)
  const warehouses = useWarehouses(org.id)
  const orders = useQuery({
    queryKey: [...tenantKey(org.id), 'orders', 'all'],
    queryFn: ({ signal }) => allPages((page, s) => api.orders.list(org.id, page, s), signal),
  })
  const health = useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => api.health(signal),
    staleTime: 60_000,
    retry: false,
  })
  const base = `/app/${org.id}`
  const cards = [
    {
      label: 'Products',
      count: products.data?.length,
      Icon: Package,
      path: 'products',
      description: 'In your product catalog',
      error: products.error,
    },
    {
      label: 'Warehouses',
      count: warehouses.data?.length,
      Icon: Warehouse,
      path: 'warehouses',
      description: 'Locations in this workspace',
      error: warehouses.error,
    },
    {
      label: 'Orders',
      count: orders.data?.length,
      Icon: ShoppingCart,
      path: 'orders',
      description: 'Across all order statuses',
      error: orders.error,
    },
  ]
  return (
    <>
      <PageHeader
        eyebrow="WORKSPACE OVERVIEW"
        title="Everything in its place."
        description={`Here's the latest from ${org.name}. Let's keep things moving.`}
        action={
          canWrite(org.role) && (
            <Link to={`${base}/orders/new`} className="btn btn-primary">
              <Plus size={17} />
              Create order
            </Link>
          )
        }
      />
      <div className="metrics-grid">
        {cards.map(({ label, count, Icon, path, description, error }) => (
          <Link to={`${base}/${path}`} className="metric-card" key={path}>
            <div className="metric-card-top">
              <span>{label}</span>
              <Icon size={20} />
            </div>
            <strong>{error ? 'Unavailable' : (count?.toLocaleString() ?? '...')}</strong>
            <div className="metric-card-bottom">
              <span>{description}</span>
              <ArrowRight size={16} />
            </div>
          </Link>
        ))}
      </div>
      {(products.error || warehouses.error) && (
        <ErrorNotice error={products.error || warehouses.error} />
      )}
      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Recent orders</h2>
              <p>Your latest activity, at a glance.</p>
            </div>
            <Link className="text-link" to={`${base}/orders`}>
              View all <ArrowRight size={15} />
            </Link>
          </div>
          {orders.isPending ? (
            <Loading label="Loading recent orders..." />
          ) : orders.isError ? (
            <div className="panel-body">
              <ErrorNotice error={orders.error} />
              <button
                className="text-link"
                onClick={() => {
                  void orders.refetch()
                }}
              >
                Try again
              </button>
            </div>
          ) : orders.data.length === 0 ? (
            <Empty
              title="A fresh start"
              description="Your orders will appear here once you create them."
              action={
                canWrite(org.role) && (
                  <Link className="btn btn-secondary" to={`${base}/orders/new`}>
                    Create your first order
                  </Link>
                )
              }
            />
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.data.slice(0, 5).map((order) => (
                    <tr key={order.id}>
                      <td>
                        <Link className="order-link" to={`${base}/orders/${order.id}`}>
                          #{shortId(order.id)}
                        </Link>
                      </td>
                      <td>
                        <StatusBadge status={order.status} />
                      </td>
                      <td>{formatDate(order.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        <aside className="panel getting-started">
          <div className="getting-started-icon">
            <Boxes size={27} />
          </div>
          <h2>
            A simple flow.
            <br />A stronger operation.
          </h2>
          <p>Build your catalog, put stock in place, and move orders from pending to fulfilled.</p>
          <ol>
            <li>
              <span>01</span>
              <div>
                <strong>Add your products</strong>
                <p>A clear catalog is a good foundation.</p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <strong>Set up your warehouses</strong>
                <p>Add inventory to each location.</p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <strong>Bring orders to life</strong>
                <p>Create, allocate and fulfill.</p>
              </div>
            </li>
          </ol>
          <Link className="text-link" to={`${base}/products`}>
            Explore your catalog <ArrowRight size={15} />
          </Link>
        </aside>
      </div>
      <div className="workspace-status">
        <span className={`health-dot ${health.isSuccess ? 'health-online' : ''}`} />
        <span>
          {health.isPending
            ? 'Checking API availability'
            : health.isSuccess
              ? 'API reachable'
              : 'API availability unknown'}
        </span>
        <span className="status-divider">/</span>
        <span>
          Your role: <strong>{org.role}</strong>
        </span>
        <span className="ml-auto hidden sm:inline">Built for a clearer working day.</span>
      </div>
    </>
  )
}
