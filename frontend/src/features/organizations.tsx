import { formatDate } from '../lib/format'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Building2, Plus, ShieldCheck, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/endpoints'
import type { Member, Role } from '../api/types'
import { useAuth } from '../lib/auth'
import { assignableRoles, canManage, canRemove, UUID_PATTERN } from '../lib/permissions'
import { tenantKey, useOrganizations, useRefreshTenant } from '../lib/queries'
import { Brand, LogoutButton, useTenant } from '../components/layout'
import {
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

export function OrganizationsPage() {
  const { user } = useAuth()
  const orgs = useOrganizations()
  const cache = useQueryClient()
  const navigate = useNavigate()
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const mutation = useMutation({
    mutationFn: () => api.organizations.create(name.trim()),
    onSuccess: async (org) => {
      await cache.invalidateQueries({ queryKey: ['organizations'] })
      choose(org.id)
    },
  })
  function choose(id: string) {
    if (!orgs.data?.some((org) => org.id === id) && !mutation.data && !creating) return
    try {
      if (user) localStorage.setItem(`stockflow-organization:${user.id}`, id)
    } catch {
      /* optional preference */
    }
    navigate(`/app/${id}/dashboard`)
  }
  let selected: string | null = null
  try {
    selected = user ? localStorage.getItem(`stockflow-organization:${user.id}`) : null
  } catch {
    /* optional preference */
  }
  return (
    <div className="onboarding">
      <header className="onboarding-top">
        <Brand />
        <div className="flex items-center gap-4">
          <span className="hidden text-sm text-slate-500 sm:inline">{user?.email}</span>
          <LogoutButton />
        </div>
      </header>
      <main className="onboarding-main">
        <PageHeader
          eyebrow="YOUR ORGANIZATIONS"
          title="Choose your workspace"
          description="Pick up where you left off, or create a space for your team."
          action={
            <Button
              onClick={() => {
                mutation.reset()
                setName('')
                setCreating(true)
              }}
            >
              <Plus size={17} />
              New organization
            </Button>
          }
        />
        {orgs.isPending ? (
          <Loading />
        ) : orgs.isError ? (
          <ErrorState
            error={orgs.error}
            retry={() => {
              void orgs.refetch()
            }}
          />
        ) : orgs.data.length === 0 ? (
          <div className="panel">
            <Empty
              title="Make room for your business"
              description="Create your first organization to start adding products, warehouses and orders."
              action={
                <Button onClick={() => setCreating(true)}>
                  <Plus size={17} />
                  Create organization
                </Button>
              }
            />
          </div>
        ) : (
          <div className="organization-grid">
            {orgs.data.map((org) => (
              <button key={org.id} className="organization-card" onClick={() => choose(org.id)}>
                <div className="flex items-center justify-between">
                  <span className="organization-card-icon">
                    <Building2 size={24} />
                  </span>
                  {selected === org.id && <span className="subtle-badge">Last opened</span>}
                </div>
                <h2>{org.name}</h2>
                <p>{org.slug}</p>
                <div className="organization-card-footer">
                  <span className="role-badge">{org.role}</span>
                  <ArrowRight size={19} />
                </div>
              </button>
            ))}
          </div>
        )}
        <p className="workspace-hint">
          <ShieldCheck size={16} />
          Each organization has its own products, stock and team permissions.
        </p>
      </main>
      {creating && (
        <Dialog
          title="Create an organization"
          description="A workspace for your team's inventory and orders. You'll be its owner."
          onClose={() => setCreating(false)}
          busy={mutation.isPending}
        >
          <form
            className="form-stack"
            onSubmit={(event) => {
              event.preventDefault()
              mutation.mutate()
            }}
          >
            <Field label="Organization name">
              <input
                required
                maxLength={255}
                value={name}
                onChange={(event) => setName(event.target.value)}
                pattern=".*\S.*"
                placeholder="e.g. Acme Operations"
              />
            </Field>
            <ErrorNotice error={mutation.error} />
            <div className="form-actions">
              <Button
                variant="secondary"
                disabled={mutation.isPending}
                onClick={() => setCreating(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? 'Creating...' : 'Create workspace'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}
    </div>
  )
}

export function OrganizationSettings() {
  const org = useTenant()
  const [name, setName] = useState(org.name)
  const refresh = useRefreshTenant(org.id)
  const cache = useQueryClient()
  const notice = useNotice()
  const mutation = useMutation({
    mutationFn: () => api.organizations.rename(org.id, name.trim()),
    onSuccess: async () => {
      await Promise.all([refresh(), cache.invalidateQueries({ queryKey: ['organizations'] })])
      notice('Organization name updated.')
    },
  })
  return (
    <>
      <PageHeader
        eyebrow="WORKSPACE SETTINGS"
        title="Organization"
        description="Your workspace details and your place on the team."
      />
      <div className="settings-grid">
        <section className="panel">
          <div className="panel-heading">
            <h2>Organization details</h2>
            <span className="role-badge">{org.role}</span>
          </div>
          <form
            className="panel-body form-stack"
            onSubmit={(event) => {
              event.preventDefault()
              mutation.mutate()
            }}
          >
            <Field label="Organization name">
              <input
                required
                maxLength={255}
                pattern=".*\S.*"
                value={name}
                onChange={(event) => setName(event.target.value)}
                disabled={!canManage(org.role)}
              />
            </Field>
            <Field
              label="Workspace slug"
              hint="This address stays the same when you rename your organization."
            >
              <input readOnly value={org.slug} />
            </Field>
            <Field label="Organization ID">
              <input readOnly value={org.id} className="mono" />
            </Field>
            <p className="text-sm text-slate-500">Created {formatDate(org.created_at)}</p>
            <ErrorNotice error={mutation.error} />
            {canManage(org.role) ? (
              <div>
                <Button type="submit" disabled={mutation.isPending || name.trim() === org.name}>
                  {mutation.isPending ? 'Saving...' : 'Save changes'}
                </Button>
              </div>
            ) : (
              <p className="info-note">Only owners and admins can change organization details.</p>
            )}
          </form>
        </section>
        <aside className="panel permission-panel">
          <ShieldCheck size={26} />
          <h2>Access that fits your role</h2>
          <p>
            Owners, admins and managers can manage business resources. Viewers have read-only
            access.
          </p>
          <p>
            Member management follows a separate role hierarchy. Permissions are always checked by
            the server.
          </p>
          {org.role !== 'viewer' && (
            <Link className="text-link" to={`../members`}>
              Manage membership <ArrowRight size={15} />
            </Link>
          )}
        </aside>
      </div>
    </>
  )
}

export function MembersPage() {
  const org = useTenant()
  const { user } = useAuth()
  const notice = useNotice()
  const refresh = useRefreshTenant(org.id)
  const [offset, setOffset] = useState(0)
  const [adding, setAdding] = useState(false)
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<Role>('viewer')
  const [target, setTarget] = useState<{ id: string; label: string } | null>(null)
  const [manualId, setManualId] = useState('')
  const members = useQuery({
    queryKey: [...tenantKey(org.id), 'members', { limit: 20, offset }],
    queryFn: ({ signal }) => api.organizations.members(org.id, { limit: 20, offset }, signal),
    enabled: canManage(org.role),
  })
  const add = useMutation({
    mutationFn: () => api.organizations.addMember(org.id, email.trim(), role),
    onSuccess: async () => {
      await refresh()
      setAdding(false)
      notice('Member added to your organization.')
    },
  })
  const remove = useMutation({
    mutationFn: (id: string) => api.organizations.removeMember(org.id, id),
    onSuccess: async () => {
      setTarget(null)
      setManualId('')
      await refresh()
      notice('Member removed.')
      if (offset) setOffset(0)
    },
  })
  const selectRemoval = (member: Member) => {
    remove.reset()
    setTarget({ id: member.user_id, label: member.email })
  }
  if (org.role === 'viewer')
    return (
      <div className="panel">
        <Empty
          title="Member access is restricted"
          description="Your viewer role allows access to business resources. Member management is limited to other roles."
        />
      </div>
    )
  return (
    <>
      <PageHeader
        eyebrow="YOUR TEAM"
        title="Members"
        description={
          canManage(org.role)
            ? 'Give existing StockFlow users the right access to your workspace.'
            : 'Manage viewer access using a known user ID.'
        }
        action={
          canManage(org.role) && (
            <Button
              onClick={() => {
                add.reset()
                setEmail('')
                setRole('viewer')
                setAdding(true)
              }}
            >
              <Plus size={17} />
              Add member
            </Button>
          )
        }
      />
      {canManage(org.role) ? (
        <section className="panel">
          {members.isPending ? (
            <Loading label="Loading members..." />
          ) : members.isError ? (
            <ErrorState
              error={members.error}
              retry={() => {
                void members.refetch()
              }}
            />
          ) : (
            <>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Team member</th>
                      <th>Role</th>
                      <th>Joined</th>
                      <th>
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {members.data?.map((member) => (
                      <tr key={member.user_id}>
                        <td>
                          <div className="table-person">
                            <span className="person-avatar">
                              {member.email.slice(0, 1).toUpperCase()}
                            </span>
                            <div>
                              <strong>
                                {member.email}
                                {member.user_id === user?.id && (
                                  <span className="you-label">You</span>
                                )}
                              </strong>
                              <span className="table-secondary mono">{member.user_id}</span>
                            </div>
                          </div>
                        </td>
                        <td>
                          <span className="role-badge">{member.role}</span>
                        </td>
                        <td>{formatDate(member.joined_at)}</td>
                        <td className="text-right">
                          {user && canRemove(org.role, member.role, user.id, member.user_id) && (
                            <Button
                              variant="ghost"
                              aria-label={`Remove ${member.email}`}
                              onClick={() => selectRemoval(member)}
                            >
                              <Trash2 size={16} />
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {members.data?.length === 0 && (
                <Empty
                  title="No members on this page"
                  description="Go back to see earlier team members."
                />
              )}
              <Pagination
                offset={offset}
                count={members.data?.length ?? 0}
                onChange={setOffset}
                busy={members.isFetching}
              />
            </>
          )}
        </section>
      ) : (
        <section className="panel narrow-panel">
          <div className="panel-heading">
            <h2>Remove a viewer</h2>
          </div>
          <form
            className="panel-body form-stack"
            onSubmit={(event: FormEvent<HTMLFormElement>) => {
              event.preventDefault()
              remove.reset()
              setTarget({ id: manualId.trim(), label: `user ${manualId.trim()}` })
            }}
          >
            <p className="info-note">
              Managers can remove viewers, but cannot read the member directory. Enter a viewer's
              known user ID. The server checks the target's role before removal.
            </p>
            <Field label="Viewer user ID">
              <input
                required
                pattern={UUID_PATTERN.source}
                value={manualId}
                onChange={(event) => setManualId(event.target.value)}
                placeholder="00000000-0000-0000-0000-000000000000"
              />
            </Field>
            <Button type="submit" variant="danger" disabled={manualId.trim() === user?.id}>
              Review removal
            </Button>
          </form>
        </section>
      )}
      {adding && (
        <Dialog
          title="Add a team member"
          description="Enter the email of an existing StockFlow account. This does not send an invitation."
          onClose={() => setAdding(false)}
          busy={add.isPending}
        >
          <form
            className="form-stack"
            onSubmit={(event) => {
              event.preventDefault()
              add.mutate()
            }}
          >
            <Field label="Email address">
              <input
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="teammate@company.com"
              />
            </Field>
            <Field label="Organization role">
              <select value={role} onChange={(event) => setRole(event.target.value as Role)}>
                {assignableRoles(org.role).map((value) => (
                  <option key={value} value={value}>
                    {value[0]?.toUpperCase()}
                    {value.slice(1)}
                  </option>
                ))}
              </select>
            </Field>
            <ErrorNotice error={add.error} />
            <div className="form-actions">
              <Button variant="secondary" disabled={add.isPending} onClick={() => setAdding(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={add.isPending}>
                {add.isPending ? 'Adding...' : 'Add member'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}
      {target && (
        <ConfirmDialog
          title="Remove this member?"
          description={`${target.label} will lose access to this organization. Other workspaces are not affected.`}
          confirmLabel="Remove member"
          onClose={() => setTarget(null)}
          onConfirm={() => remove.mutate(target.id)}
          busy={remove.isPending}
          error={remove.error}
          danger
        />
      )}
    </>
  )
}
