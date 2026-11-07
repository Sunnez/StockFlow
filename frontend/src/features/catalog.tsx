import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  ArrowUpRight,
  MapPin,
  Package,
  Pencil,
  Plus,
  Trash2,
  Warehouse as WarehouseIcon,
} from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import type { Product, Warehouse } from '../api/types'
import { useTenant } from '../components/layout'
import {
  BackLink,
  Button,
  ConfirmDialog,
  Dialog,
  Empty,
  ErrorNotice,
  ErrorState,
  Field,
  Loading,
  PageHeader,
  Pagination,
  useNotice,
} from '../components/ui'
import { canWrite, UUID_PATTERN } from '../lib/permissions'
import { tenantKey, useRefreshTenant } from '../lib/queries'
import { InventorySection } from './inventory'

type Kind = 'products' | 'warehouses'
type Resource = Product | Warehouse

function ResourceForm({
  kind,
  initial,
  onClose,
  onSaved,
}: {
  kind: Kind
  initial?: Resource
  onClose: () => void
  onSaved: () => void
}) {
  const org = useTenant()
  const notice = useNotice()
  const [name, setName] = useState(initial?.name ?? '')
  const [secondary, setSecondary] = useState(
    initial ? ('sku' in initial ? initial.sku : initial.location) : '',
  )
  const refresh = useRefreshTenant(org.id)
  const isProduct = kind === 'products'
  const mutation = useMutation<Resource, Error>({
    mutationFn: () => {
      if (isProduct) {
        const body = { name: name.trim(), sku: secondary.trim() }
        return initial
          ? api.products.update(org.id, initial.id, body)
          : api.products.create(org.id, body)
      }
      const body = { name: name.trim(), location: secondary.trim() }
      return initial
        ? api.warehouses.update(org.id, initial.id, body)
        : api.warehouses.create(org.id, body)
    },
    onSuccess: async () => {
      await refresh()
      onSaved()
      notice(`${isProduct ? 'Product' : 'Warehouse'} ${initial ? 'updated' : 'created'}.`)
    },
  })
  return (
    <Dialog
      title={`${initial ? 'Edit' : 'New'} ${isProduct ? 'product' : 'warehouse'}`}
      description={
        isProduct
          ? 'Keep your catalog easy to identify and organize.'
          : 'Give your stock a place to call home.'
      }
      onClose={onClose}
      busy={mutation.isPending}
    >
      <form
        className="form-stack"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <Field label={isProduct ? 'Product name' : 'Warehouse name'}>
          <input
            required
            maxLength={255}
            pattern=".*\S.*"
            placeholder={isProduct ? 'e.g. Wireless keyboard' : 'e.g. Central warehouse'}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </Field>
        <Field
          label={isProduct ? 'SKU' : 'Location'}
          hint={
            isProduct
              ? 'Unique within this organization.'
              : 'City, address or a useful location description.'
          }
        >
          <input
            required
            maxLength={isProduct ? 100 : 255}
            pattern=".*\S.*"
            value={secondary}
            onChange={(event) => setSecondary(event.target.value)}
            placeholder={isProduct ? 'e.g. KEY-001' : 'e.g. Riga, Latvia'}
          />
        </Field>
        <ErrorNotice error={mutation.error} />
        <div className="form-actions">
          <Button variant="secondary" disabled={mutation.isPending} onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending
              ? 'Saving...'
              : initial
                ? 'Save changes'
                : `Create ${isProduct ? 'product' : 'warehouse'}`}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}

export function CatalogPage({ kind }: { kind: Kind }) {
  const org = useTenant()
  const [offset, setOffset] = useState(0)
  const [creating, setCreating] = useState(false)
  const isProduct = kind === 'products'
  const Icon = isProduct ? Package : WarehouseIcon
  const query = useQuery<Resource[]>({
    queryKey: [...tenantKey(org.id), kind, { limit: 20, offset }],
    queryFn: ({ signal }) =>
      isProduct
        ? api.products.list(org.id, { limit: 20, offset }, signal)
        : api.warehouses.list(org.id, { limit: 20, offset }, signal),
  })
  const createButton = canWrite(org.role) && (
    <Button onClick={() => setCreating(true)}>
      <Plus size={17} />
      New {isProduct ? 'product' : 'warehouse'}
    </Button>
  )
  return (
    <>
      <PageHeader
        eyebrow="WORKSPACE RESOURCES"
        title={isProduct ? 'Products' : 'Warehouses'}
        description={
          isProduct
            ? 'Your catalog, clearly organized. Everything starts with a product.'
            : 'Every location, connected. Manage where your inventory lives.'
        }
        action={createButton}
      />
      <section className="panel">
        <div className="panel-heading">
          <div className="flex items-center gap-2">
            <Icon size={18} />
            <h2>{isProduct ? 'Product catalog' : 'Warehouse directory'}</h2>
          </div>
          {org.role === 'viewer' && <span className="subtle-badge">Read-only access</span>}
        </div>
        {query.isPending ? (
          <Loading label={`Loading ${kind}...`} />
        ) : query.isError ? (
          <ErrorState
            error={query.error}
            retry={() => {
              void query.refetch()
            }}
          />
        ) : (
          <>
            {query.data.length === 0 ? (
              <Empty
                title={
                  offset
                    ? 'No more results'
                    : isProduct
                      ? 'Your next product starts here'
                      : 'A place for every product'
                }
                description={
                  offset
                    ? 'Return to the previous page to see more.'
                    : isProduct
                      ? 'Add products to start tracking inventory and creating orders.'
                      : 'Add a warehouse, then bring its inventory into view.'
                }
                action={!offset && createButton}
              />
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>{isProduct ? 'Product' : 'Warehouse'}</th>
                      <th>{isProduct ? 'SKU' : 'Location'}</th>
                      <th>ID</th>
                      <th>
                        <span className="sr-only">View details</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {query.data.map((record) => (
                      <tr key={record.id}>
                        <td>
                          <Link className="resource-link" to={record.id}>
                            <span className="resource-icon">
                              <Icon size={18} />
                            </span>
                            <strong>{record.name}</strong>
                          </Link>
                        </td>
                        <td>
                          {'sku' in record ? (
                            <span className="sku">{record.sku}</span>
                          ) : (
                            <span className="flex items-center gap-2">
                              <MapPin size={14} className="text-slate-400" />
                              {record.location}
                            </span>
                          )}
                        </td>
                        <td className="mono text-slate-500">{record.id.slice(0, 8)}</td>
                        <td className="text-right">
                          <Link
                            to={record.id}
                            className="table-open"
                            aria-label={`View ${record.name}`}
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
              count={query.data.length}
              onChange={setOffset}
              busy={query.isFetching}
            />
          </>
        )}
      </section>
      {creating && (
        <ResourceForm
          kind={kind}
          onClose={() => setCreating(false)}
          onSaved={() => setCreating(false)}
        />
      )}
    </>
  )
}

export function CatalogDetail({ kind }: { kind: Kind }) {
  const org = useTenant()
  const params = useParams()
  const resourceId = params.productId ?? params.warehouseId ?? ''
  const navigate = useNavigate()
  const notice = useNotice()
  const refresh = useRefreshTenant(org.id)
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const isProduct = kind === 'products'
  const query = useQuery<Resource>({
    queryKey: [...tenantKey(org.id), kind, resourceId],
    queryFn: ({ signal }) =>
      isProduct
        ? api.products.get(org.id, resourceId, signal)
        : api.warehouses.get(org.id, resourceId, signal),
    enabled: UUID_PATTERN.test(resourceId),
  })
  const remove = useMutation({
    mutationFn: () =>
      isProduct
        ? api.products.remove(org.id, resourceId)
        : api.warehouses.remove(org.id, resourceId),
    onSuccess: async () => {
      navigate(`/app/${org.id}/${kind}`, { replace: true })
      await refresh()
      notice(`${isProduct ? 'Product' : 'Warehouse'} deleted.`)
    },
  })
  if (!UUID_PATTERN.test(resourceId))
    return <ErrorState error={new Error('This resource address is invalid.')} />
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
  const record = query.data
  return (
    <>
      <BackLink to={`/app/${org.id}/${kind}`}>Back to {kind}</BackLink>
      <PageHeader
        eyebrow={isProduct ? 'PRODUCT DETAILS' : 'WAREHOUSE DETAILS'}
        title={record.name}
        description={'sku' in record ? `SKU: ${record.sku}` : record.location}
        action={
          canWrite(org.role) && (
            <>
              <Button variant="secondary" onClick={() => setEditing(true)}>
                <Pencil size={16} />
                Edit
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  remove.reset()
                  setDeleting(true)
                }}
              >
                <Trash2 size={16} />
                Delete
              </Button>
            </>
          )
        }
      />
      <section className="panel resource-details">
        <div>
          <span>Name</span>
          <strong>{record.name}</strong>
        </div>
        <div>
          <span>{'sku' in record ? 'SKU' : 'Location'}</span>
          <strong>{'sku' in record ? record.sku : record.location}</strong>
        </div>
        <div>
          <span>Resource ID</span>
          <code>{record.id}</code>
        </div>
      </section>
      {!isProduct && <InventorySection warehouseId={record.id} />}
      {isProduct && (
        <div className="info-note mt-5">
          Manage this product's physical stock from a warehouse's inventory page. Order reservations
          and availability are maintained by StockFlow.
        </div>
      )}
      {editing && (
        <ResourceForm
          kind={kind}
          initial={record}
          onClose={() => setEditing(false)}
          onSaved={() => setEditing(false)}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title={`Delete this ${isProduct ? 'product' : 'warehouse'}?`}
          description={
            isProduct
              ? 'This permanently removes the product. Products with stock or order references cannot be deleted.'
              : 'This permanently removes the warehouse. Remove its inventory entries first; warehouses with inventory cannot be deleted.'
          }
          confirmLabel="Delete permanently"
          onClose={() => setDeleting(false)}
          onConfirm={() => remove.mutate()}
          busy={remove.isPending}
          error={remove.error}
          danger
        />
      )}
    </>
  )
}
