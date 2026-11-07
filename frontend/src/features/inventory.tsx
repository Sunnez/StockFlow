import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/endpoints'
import type { Inventory } from '../api/types'
import { useTenant } from '../components/layout'
import {
  Button,
  ConfirmDialog,
  Dialog,
  Empty,
  ErrorNotice,
  ErrorState,
  Field,
  Loading,
  Pagination,
  useNotice,
} from '../components/ui'
import { canWrite, INT_MAX, validQuantity } from '../lib/permissions'
import { tenantKey, useProducts, useRefreshTenant } from '../lib/queries'

function InventoryForm({
  warehouseId,
  initial,
  onClose,
}: {
  warehouseId: string
  initial?: Inventory
  onClose: () => void
}) {
  const org = useTenant()
  const products = useProducts(org.id)
  const refresh = useRefreshTenant(org.id)
  const notice = useNotice()
  const [productId, setProductId] = useState(initial?.product_id ?? '')
  const [quantity, setQuantity] = useState(String(initial?.quantity ?? 0))
  const [validationError, setValidationError] = useState<unknown>(null)
  const mutation = useMutation({
    mutationFn: () => {
      const number = validQuantity(quantity, initial?.reserved_quantity ?? 0)
      if (number === null)
        throw new Error(
          `Enter a whole quantity between ${initial?.reserved_quantity ?? 0} and ${INT_MAX}.`,
        )
      return initial
        ? api.inventory.update(org.id, warehouseId, initial.product_id, number)
        : api.inventory.create(org.id, warehouseId, productId, number)
    },
    onSuccess: async () => {
      await refresh()
      onClose()
      notice(initial ? 'Stock quantity updated.' : 'Product added to inventory.')
    },
  })
  return (
    <Dialog
      title={initial ? 'Update stock quantity' : 'Add inventory'}
      description="Physical stock cannot be lower than the quantity reserved for orders."
      onClose={onClose}
      busy={mutation.isPending}
    >
      <form
        className="form-stack"
        onSubmit={(event) => {
          event.preventDefault()
          setValidationError(null)
          if (validQuantity(quantity, initial?.reserved_quantity ?? 0) === null) {
            setValidationError(
              new Error('Enter a valid whole quantity within the permitted range.'),
            )
            return
          }
          mutation.mutate()
        }}
      >
        <Field label="Product">
          <select
            required
            value={productId}
            disabled={!!initial || products.isPending || products.isError}
            onChange={(event) => setProductId(event.target.value)}
          >
            <option value="">Choose a product</option>
            {products.data?.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name} - {product.sku}
              </option>
            ))}
          </select>
        </Field>
        {products.isPending && <p className="text-sm text-slate-500">Loading products...</p>}
        {products.isError && <ErrorNotice error={products.error} />}
        {products.data?.length === 0 && (
          <p className="info-note">Create a product in the catalog before adding inventory.</p>
        )}
        <Field
          label="Physical quantity"
          hint={
            initial
              ? `${initial.reserved_quantity} units are currently reserved.`
              : 'Enter 0 to create an empty inventory entry.'
          }
        >
          <input
            type="number"
            required
            min={initial?.reserved_quantity ?? 0}
            max={INT_MAX}
            step={1}
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
          />
        </Field>
        <ErrorNotice error={validationError || mutation.error} />
        <div className="form-actions">
          <Button variant="secondary" disabled={mutation.isPending} onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={mutation.isPending || products.isPending || products.isError || !productId}
          >
            {mutation.isPending ? 'Saving...' : initial ? 'Update quantity' : 'Add inventory'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}

export function InventorySection({ warehouseId }: { warehouseId: string }) {
  const org = useTenant()
  const products = useProducts(org.id)
  const refresh = useRefreshTenant(org.id)
  const notice = useNotice()
  const [offset, setOffset] = useState(0)
  const [editing, setEditing] = useState<Inventory | 'new' | null>(null)
  const [removing, setRemoving] = useState<Inventory | null>(null)
  const query = useQuery({
    queryKey: [...tenantKey(org.id), 'inventory', warehouseId, { limit: 20, offset }],
    queryFn: ({ signal }) => api.inventory.list(org.id, warehouseId, { limit: 20, offset }, signal),
  })
  const remove = useMutation({
    mutationFn: (product: string) => api.inventory.remove(org.id, warehouseId, product),
    onSuccess: async () => {
      await refresh()
      setRemoving(null)
      if (offset) setOffset(0)
      notice('Inventory entry removed.')
    },
  })
  const catalog = new Map(products.data?.map((product) => [product.id, product]))
  const addButton = canWrite(org.role) && (
    <Button onClick={() => setEditing('new')}>
      <Plus size={16} />
      Add inventory
    </Button>
  )
  return (
    <section className="panel mt-7">
      <div className="panel-heading">
        <div>
          <h2>Warehouse inventory</h2>
          <p>Physical stock, reservations and availability.</p>
        </div>
        {addButton}
      </div>
      {products.isError && (
        <div className="px-6 pt-4">
          <ErrorNotice
            error={new Error('Product names could not be loaded. Inventory IDs remain available.')}
          />
          <Button
            variant="ghost"
            onClick={() => {
              void products.refetch()
            }}
          >
            Retry product names
          </Button>
        </div>
      )}
      {query.isPending ? (
        <Loading label="Loading stock..." />
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
              title={offset ? 'No entries on this page' : 'Ready for your first stock'}
              description="Add a catalog product and its physical quantity to this warehouse."
              action={!offset && addButton}
            />
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th className="number-cell">Physical</th>
                    <th className="number-cell">Reserved</th>
                    <th className="number-cell">Available</th>
                    <th>
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.map((entry) => (
                    <tr key={entry.id}>
                      <td>
                        <Link
                          className="text-link"
                          to={`/app/${org.id}/products/${entry.product_id}`}
                        >
                          {catalog.get(entry.product_id)?.name ?? entry.product_id}
                        </Link>
                        <span className="table-secondary">
                          {catalog.get(entry.product_id)?.sku}
                        </span>
                      </td>
                      <td className="number-cell">{entry.quantity.toLocaleString()}</td>
                      <td className="number-cell text-slate-500">
                        {entry.reserved_quantity.toLocaleString()}
                      </td>
                      <td className="number-cell">
                        <span
                          className={`available-number ${entry.available_quantity === 0 ? 'available-zero' : ''}`}
                        >
                          {entry.available_quantity.toLocaleString()}
                        </span>
                      </td>
                      <td className="text-right">
                        {canWrite(org.role) && (
                          <div className="row-actions">
                            <Button
                              variant="ghost"
                              aria-label={`Edit quantity for ${catalog.get(entry.product_id)?.name ?? entry.product_id}`}
                              onClick={() => setEditing(entry)}
                            >
                              <Pencil size={15} />
                            </Button>
                            <Button
                              variant="ghost"
                              aria-label="Remove inventory entry"
                              disabled={entry.quantity > 0 || entry.reserved_quantity > 0}
                              title="Only empty, unreserved inventory can be removed. Historical allocations may also prevent deletion."
                              onClick={() => {
                                remove.reset()
                                setRemoving(entry)
                              }}
                            >
                              <Trash2 size={15} />
                            </Button>
                          </div>
                        )}
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
      {editing && (
        <InventoryForm
          warehouseId={warehouseId}
          initial={editing === 'new' ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {removing && (
        <ConfirmDialog
          title="Remove this inventory entry?"
          description="The entry must be empty and unreserved. Historical order allocations can prevent removal even when stock is zero."
          confirmLabel="Remove entry"
          onClose={() => setRemoving(null)}
          onConfirm={() => remove.mutate(removing.product_id)}
          busy={remove.isPending}
          error={remove.error}
          danger
        />
      )}
    </section>
  )
}
