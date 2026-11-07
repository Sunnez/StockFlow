// Frontend-only browser QA. Every API request is fulfilled locally, never sent
// to FastAPI. Requires the local Vite server and an already installed Edge/Chrome.
import assert from 'node:assert/strict'
import { existsSync, mkdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium } from 'playwright-core'

const frontend = 'http://localhost:5173'
const orgId = '11111111-1111-1111-1111-111111111111'
const secondId = '77777777-7777-7777-7777-777777777777'
const productId = '22222222-2222-2222-2222-222222222222'
const warehouseId = '33333333-3333-3333-3333-333333333333'
const orderId = '44444444-4444-4444-4444-444444444444'
const timestamp = '2026-11-07T12:00:00Z'
const user = {
  id: '66666666-6666-6666-6666-666666666666',
  email: 'operator@example.com',
  is_active: true,
  created_at: timestamp,
}
const executablePath =
  process.env.STOCKFLOW_TEST_BROWSER ||
  [
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
  ].find(existsSync)
assert(
  executablePath,
  'Set STOCKFLOW_TEST_BROWSER to an existing Chromium browser executable. No browser download is performed.',
)
const profile = resolve('.browser-profile', `smoke-${Date.now()}`)
const artifacts = resolve('artifacts')
mkdirSync(resolve(profile, 'tmp'), { recursive: true })
mkdirSync(artifacts, { recursive: true })
const context = await chromium.launchPersistentContext(profile, {
  executablePath,
  headless: true,
  viewport: { width: 1440, height: 1000 },
  env: { ...process.env, TEMP: resolve(profile, 'tmp'), TMP: resolve(profile, 'tmp') },
})
let authenticated = false
let fresh = false
let refreshCount = 0
const requests = []
const errors = []
const organizations = [
  {
    id: orgId,
    name: 'Acme Operations',
    slug: 'acme-operations',
    role: 'owner',
    created_at: timestamp,
  },
  {
    id: secondId,
    name: 'Second workspace',
    slug: 'second-workspace',
    role: 'viewer',
    created_at: timestamp,
  },
]
const products = [
  { id: productId, organization_id: orgId, name: 'Wireless keyboard', sku: 'KEY-001' },
]
const warehouses = [
  { id: warehouseId, organization_id: orgId, name: 'Central warehouse', location: 'Riga, Latvia' },
]
let inventory = []
let orders = []
const members = [{ user_id: user.id, email: user.email, role: 'owner', joined_at: timestamp }]
const newId = () => crypto.randomUUID()

await context.route('**/*', async (route) => {
  const request = route.request()
  const url = new URL(request.url())
  if (url.origin === frontend) return route.continue()
  if (url.origin !== 'http://localhost:8000') return route.abort()
  const method = request.method()
  const headers = {
    'access-control-allow-origin': frontend,
    'access-control-allow-credentials': 'true',
    'access-control-allow-methods': 'GET,POST,PATCH,DELETE,OPTIONS',
    'access-control-allow-headers': 'Content-Type,X-CSRF-Token',
    'content-type': 'application/json',
  }
  const answer = (status, body) =>
    route.fulfill({ status, headers, body: status === 204 ? '' : JSON.stringify(body) })
  if (method === 'OPTIONS') return answer(204)
  const body = request.postDataJSON()
  requests.push({ method, path: url.pathname, body })
  if (method !== 'GET' && !['/auth/register', '/auth/login'].includes(url.pathname)) {
    if (request.headers()['x-csrf-token'] !== 'smoke-csrf')
      return answer(403, { detail: 'Invalid CSRF token' })
  }
  if (url.pathname === '/users/me')
    return answer(
      authenticated && fresh ? 200 : 401,
      authenticated && fresh ? user : { detail: 'Not authenticated' },
    )
  if (url.pathname === '/auth/register') return answer(201, user)
  if (url.pathname === '/auth/login') {
    authenticated = true
    fresh = true
    await context.addCookies([
      { name: 'csrf_token', value: 'smoke-csrf', url: frontend, sameSite: 'Lax' },
    ])
    return answer(200, user)
  }
  if (url.pathname === '/auth/refresh') {
    if (!authenticated) return answer(401, { detail: 'Invalid refresh token' })
    refreshCount++
    fresh = true
    return answer(204)
  }
  if (url.pathname === '/auth/logout') {
    authenticated = false
    fresh = false
    await context.clearCookies()
    return answer(204)
  }
  if (url.pathname === '/health') return answer(200, { status: 'ok' })
  if (!authenticated || !fresh) return answer(401, { detail: 'Not authenticated' })
  if (url.pathname === '/organizations') {
    if (method === 'POST') {
      const organization = {
        id: newId(),
        name: body.name,
        slug: 'created-workspace',
        role: 'owner',
        created_at: timestamp,
      }
      organizations.push(organization)
      return answer(201, organization)
    }
    return answer(200, organizations)
  }
  const segments = url.pathname.split('/').filter(Boolean)
  const organization = organizations.find((item) => item.id === segments[1])
  if (!organization) return answer(404, { detail: 'Organization not found' })
  if (segments.length === 2) {
    if (method === 'PATCH') organization.name = body.name
    return answer(200, organization)
  }
  if (segments[2] === 'members') {
    if (method === 'POST') {
      const member = { user_id: newId(), email: body.email, role: body.role, joined_at: timestamp }
      members.push(member)
      return answer(201, member)
    }
    if (method === 'DELETE') {
      const index = members.findIndex((item) => item.user_id === segments[3])
      if (index >= 0) members.splice(index, 1)
      return answer(204)
    }
    return answer(200, members)
  }
  if (segments[2] === 'products') {
    if (method === 'POST') {
      const product = { id: newId(), organization_id: organization.id, ...body }
      products.push(product)
      return answer(201, product)
    }
    if (segments[3]) {
      const product = products.find((item) => item.id === segments[3])
      if (method === 'PATCH') Object.assign(product, body)
      if (method === 'DELETE') {
        products.splice(products.indexOf(product), 1)
        return answer(204)
      }
      return answer(200, product)
    }
    return answer(
      200,
      products.filter((item) => item.organization_id === organization.id),
    )
  }
  if (segments[2] === 'warehouses') {
    const warehouse = warehouses.find((item) => item.id === segments[3])
    if (segments[4] === 'inventory') {
      if (method === 'POST') {
        const row = {
          id: newId(),
          organization_id: organization.id,
          warehouse_id: segments[3],
          ...body,
          reserved_quantity: 0,
          available_quantity: body.quantity,
        }
        inventory.push(row)
        return answer(201, row)
      }
      if (method === 'PATCH') {
        const row = inventory.find((item) => item.product_id === segments[5])
        row.quantity = body.quantity
        row.available_quantity = row.quantity - row.reserved_quantity
        return answer(200, row)
      }
      if (method === 'DELETE') {
        inventory = inventory.filter((item) => item.product_id !== segments[5])
        return answer(204)
      }
      return answer(
        200,
        inventory.filter((item) => item.warehouse_id === warehouse.id),
      )
    }
    if (method === 'POST') {
      const created = { id: newId(), organization_id: organization.id, ...body }
      warehouses.push(created)
      return answer(201, created)
    }
    if (warehouse) {
      if (method === 'PATCH') Object.assign(warehouse, body)
      if (method === 'DELETE') {
        warehouses.splice(warehouses.indexOf(warehouse), 1)
        return answer(204)
      }
      return answer(200, warehouse)
    }
    return answer(
      200,
      warehouses.filter((item) => item.organization_id === organization.id),
    )
  }
  if (segments[2] === 'orders') {
    let order = orders.find((item) => item.id === segments[3])
    if (method === 'POST' && !segments[3]) {
      order = {
        id: orderId,
        organization_id: organization.id,
        status: 'pending',
        created_at: timestamp,
        items: body.items.map((item) => ({ id: newId(), ...item, allocations: [] })),
      }
      orders.push(order)
      return answer(201, order)
    }
    if (method === 'PATCH') {
      order.items = body.items.map((item) => ({ id: newId(), ...item, allocations: [] }))
      return answer(200, order)
    }
    if (method === 'DELETE') {
      orders = orders.filter((item) => item.id !== segments[3])
      return answer(204)
    }
    if (segments[4]) {
      order.status =
        segments[4] === 'allocate'
          ? 'allocated'
          : segments[4] === 'fulfill'
            ? 'fulfilled'
            : 'cancelled'
      if (segments[4] === 'allocate')
        order.items.forEach((item) => {
          const stock = inventory.find((row) => row.product_id === item.product_id)
          item.allocations = [{ id: newId(), inventory_id: stock.id, quantity: item.quantity }]
          stock.reserved_quantity += item.quantity
          stock.available_quantity = stock.quantity - stock.reserved_quantity
        })
      if (segments[4] === 'fulfill')
        inventory.forEach((stock) => {
          stock.quantity -= stock.reserved_quantity
          stock.reserved_quantity = 0
          stock.available_quantity = stock.quantity
        })
    }
    return answer(200, order || orders.filter((item) => item.organization_id === organization.id))
  }
  return answer(404, { detail: 'Unexpected mocked endpoint' })
})

let page
try {
  page = await context.newPage()
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto(`${frontend}/register`)
  await page.getByLabel('Email address').fill(user.email)
  await page.getByLabel('Password', { exact: true }).fill('SyntheticSmokePassword!')
  await page.getByLabel('Confirm password').fill('SyntheticSmokePassword!')
  await page.getByRole('button', { name: 'Create account', exact: true }).click()
  await page.getByRole('heading', { name: 'Welcome back' }).waitFor()
  await page.screenshot({ path: resolve(artifacts, 'login-desktop.png'), fullPage: true })
  await page.getByLabel('Email address').fill(user.email)
  await page.getByLabel('Password', { exact: true }).fill('SyntheticSmokePassword!')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('button', { name: /Acme Operations/ }).click()
  await page.getByRole('heading', { name: 'Everything in its place.' }).waitFor()
  await page.screenshot({ path: resolve(artifacts, 'dashboard-desktop.png'), fullPage: true })

  await page.getByRole('link', { name: 'Products', exact: true }).click()
  await page.getByRole('button', { name: 'New product', exact: true }).click()
  await page.keyboard.press('Escape')
  await page.getByRole('dialog').waitFor({ state: 'hidden' })
  await page.getByRole('button', { name: 'New product', exact: true }).click()
  let dialog = page.getByRole('dialog')
  await dialog.getByLabel('Product name').fill('USB adapter')
  await dialog.getByLabel('SKU', { exact: false }).fill('USB-002')
  await dialog.getByRole('button', { name: 'Create product' }).click()
  await page.getByRole('link', { name: 'USB adapter', exact: true }).waitFor()
  await page.screenshot({ path: resolve(artifacts, 'products-desktop.png'), fullPage: true })

  await page.getByRole('link', { name: 'Warehouses', exact: true }).click()
  await page.getByRole('link', { name: 'Central warehouse', exact: true }).click()
  await page.getByRole('button', { name: 'Add inventory', exact: true }).first().click()
  dialog = page.getByRole('dialog')
  await dialog.getByLabel('Product', { exact: true }).selectOption(productId)
  await dialog.getByLabel('Physical quantity', { exact: false }).fill('20')
  await dialog.getByRole('button', { name: 'Add inventory' }).click()
  await page.getByRole('table').getByRole('link', { name: 'Wireless keyboard' }).waitFor()

  await page.getByRole('link', { name: 'Orders', exact: true }).click()
  await page.getByRole('link', { name: 'New order', exact: true }).first().click()
  await page.getByLabel('Product 1').selectOption(productId)
  await page.getByLabel('Quantity 1').fill('4')
  await page.getByRole('button', { name: 'Create order', exact: true }).click()
  await page.getByRole('button', { name: 'Allocate stock', exact: true }).click()
  dialog = page.getByRole('dialog')
  assert.equal(await dialog.getByRole('button', { name: 'Allocate stock' }).count(), 1)
  await dialog.getByRole('button', { name: 'Allocate stock' }).click()
  await page.getByRole('button', { name: 'Fulfill order', exact: true }).waitFor()
  await page.screenshot({ path: resolve(artifacts, 'order-allocated.png'), fullPage: true })
  await page.getByRole('button', { name: 'Fulfill order', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Fulfill order' }).click()
  await page.getByText('Completed. Physical stock has been updated.').waitFor()

  await page.getByRole('link', { name: 'Overview', exact: true }).click()
  fresh = false
  const secondTab = await context.newPage()
  await Promise.all([page.reload(), secondTab.goto(`${frontend}/app/${orgId}/dashboard`)])
  await page.getByRole('heading', { name: 'Everything in its place.' }).waitFor()
  await secondTab.getByRole('heading', { name: 'Everything in its place.' }).waitFor()
  assert.equal(refreshCount, 1, 'Two tabs must share one refresh rotation')
  console.log('Cross-tab Web Locks refresh: 1 rotation for 2 tabs')

  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: resolve(artifacts, 'dashboard-mobile.png'), fullPage: true })
  assert(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    'Mobile page must not overflow horizontally',
  )
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await page.getByRole('link', { name: 'Products', exact: true }).click()
  await page.getByRole('link', { name: 'Wireless keyboard', exact: true }).waitFor()
  await page
    .waitForFunction(() => document.documentElement.scrollWidth <= innerWidth, undefined, {
      timeout: 2000,
    })
    .catch(() => {})
  assert(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    'Tables must scroll inside their container',
  )
  await page.screenshot({ path: resolve(artifacts, 'products-mobile.png'), fullPage: true })

  await secondTab.getByRole('button', { name: 'Log out' }).click()
  await secondTab.getByRole('heading', { name: 'Welcome back' }).waitFor()
  await page.getByRole('heading', { name: 'Welcome back' }).waitFor()
  console.log('Cross-tab logout: both tabs returned to login')
  assert.deepEqual(errors, [], 'No browser page errors')
  console.log(
    `PASS: mocked browser workflows, desktop/mobile layout, ${requests.length} intercepted API calls. No backend calls sent.`,
  )
  console.log('Screenshots: frontend/artifacts/*.png (synthetic test fixtures)')
} catch (error) {
  if (page) {
    await page.screenshot({ path: resolve(artifacts, 'failure.png'), fullPage: true })
    console.error('Failure location:', page.url())
    console.error(
      'Overflow:',
      await page.evaluate(() => ({
        width: innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        elements: [...document.querySelectorAll('body *')]
          .filter((el) => el.getBoundingClientRect().right > innerWidth + 1)
          .slice(0, 12)
          .map((el) => ({
            tag: el.tagName,
            class: el.className,
            right: el.getBoundingClientRect().right,
            position: getComputedStyle(el).position,
          })),
      })),
    )
    console.error('Dialog count:', await page.locator('dialog[open]').count())
    console.error(
      'Recent mocked paths:',
      requests.slice(-6).map(({ method, path }) => `${method} ${path}`),
    )
  }
  throw error
} finally {
  await context.close()
}
