# StockFlow Frontend MVP

React + TypeScript + Vite, React Router, TanStack Query and Tailwind CSS. This is a
real API client for the existing FastAPI backend. Application source has no demo
data, fake statistics or alternative backend. Test fixtures exist only in tests.

## Run locally

Use Node.js 22.12+ (verified here with Node 24.13.0) and npm. From this directory:

```powershell
npm ci --ignore-scripts
npm run dev
```

Open **http://localhost:5173**. The dev server uses a strict port, so it will not
silently switch to an origin that is absent from the backend allowlist.

Default API URL: **http://localhost:8000**. To override without editing any .env:

```powershell
$env:VITE_API_URL = "http://localhost:8000"
npm run dev
```

VITE_API_URL is a public, build-time setting. Never put secrets in a VITE variable.
The application does not start the backend, PostgreSQL or Docker. Prepare those
separately under the project's existing operational rules.

## Browser authentication prerequisites

- Use one hostname consistently: localhost:5173 + localhost:8000. Mixing localhost
  with 127.0.0.1 prevents the UI reading the API's host-only CSRF cookie and changes
  same-site behavior. Open the exact URL printed by Vite.
- The backend's AUTH_ALLOWED_ORIGINS must contain the exact frontend origin, and
  credentialed CORS must allow Content-Type and X-CSRF-Token. The browser supplies
  Origin; this client does not spoof it.
- For local HTTP, backend AUTH_COOKIE_SECURE must be appropriate for that local
  environment. Production must use HTTPS and Secure cookies. The frontend does
  not change backend settings or weaken cookie flags.
- Fetch always uses credentials: include. Only the readable csrf_token cookie is
  accessed in JS and reflected into X-CSRF-Token on mutations/refresh/logout.
  JWT access and refresh tokens stay HttpOnly, never read by JS or stored in
  localStorage/sessionStorage. Register/login use the existing public contract.
- Registration creates an account, then asks the user to sign in. It does not
  pretend that registration already created a session.
- Expired access triggers a single shared refresh attempt and one request retry.
  Modern browsers share a Web Lock across tabs; a /users/me probe inside that
  lock observes cookies renewed by a previous tab before another rotation.
  Login/logout use the same lock. Without Web Locks the fallback coordinates
  within one tab only; use a current browser for cross-tab rotation safety.
- BroadcastChannel (storage-event fallback) clears caches across account changes
  and logout. Cache keys include organization UUID. Late old-session responses
  are discarded. Session events store no credentials. Only last organization
  selection is persisted, namespaced by the authenticated user's ID.
- Logout is treated as successful only after the backend succeeds. A network or
  CSRF failure remains visible; the UI does not claim the session was revoked.

## Pages and permissions

- /register, /login; protected /organizations list/create/select.
- /app/:organizationId/dashboard: counts from complete API pages, recent orders,
  non-blocking /health availability, no invented metrics.
- Products and warehouses: paginated lists, details, create/edit/delete dialogs.
- Warehouse details: server physical/reserved/available inventory, add/update/
  remove entries, product selection across all catalog pages.
- Orders: list, create, pending edit/delete, detail with real item/allocation IDs,
  confirmed allocate/fulfill/cancel actions for supported states.
- Organization: detail, current role and owner/admin rename.
- Members: owner/admin directory, add existing users by email with assignable
  roles, remove lower roles except self. No invitations or role-edit endpoint.
- Manager members page: known viewer user-ID removal form only. The backend does
  not permit managers to list members; the UI never issues that forbidden read.
- Viewer: read-only business screens, no mutation controls. Backend authorization
  remains authoritative even when cached UI permissions are stale.

Backend lists are arrays with limit/offset, not total-count responses. Tables
paginate in pages of 20. Complete dropdowns and dashboard counts read all pages of
100; this is accurate but can be expensive for very large organizations. A full
100-row final page needs one subsequent empty-page request to establish the end.
All list loaders support query cancellation.

Allocation responses contain inventory_id/quantity, not warehouse names. The
detail screen displays those real IDs and history; it does not invent joins or
inventory detail endpoints. Frontend integer form bounds are 0..2147483647 for
inventory and 1..2147483647 for orders. Backend I1 remains unchanged/deferred.

## Verification commands

```powershell
npm run typecheck
npm run lint
npm test
npm run build
npm run format:check
```

Vitest uses jsdom. Every HTTP request is mocked; unhandled fetches fail. Tests
cover client retry/CSRF/204/error behavior, role/state permissions, endpoint paths
and DTOs, paginated selectors and actual component form/navigation flows.

For a real Chromium rendering check against **mocked HTTP only**, first run Vite
on localhost:5173, then in a second terminal:

```powershell
npm run test:browser
```

The script uses an existing Edge or Chrome installation, without downloading a
browser. Override its executable with STOCKFLOW_TEST_BROWSER if needed. It stores
its synthetic profile inside .browser-profile/ and screenshots in artifacts/.
All API calls are fulfilled locally before reaching the network; other external
origins are blocked. The script covers registration/login, selection, products,
inventory, order creation/allocation/fulfillment, two-tab refresh/logout and
desktop/mobile rendering. Screenshots show synthetic test fixtures, not live data.
This is not proof of PostgreSQL, live cookie signing or production CORS behavior.

Some Windows sandboxes block esbuild/browser child processes with spawn EPERM.
Request the runtime permission for these frontend commands; do not disable
application security or alter backend code to work around it.

## Build and hosting

`npm run build` typechecks and writes dist/. VITE_API_URL must be set before build
when changing the API target. A static host must return index.html for frontend
deep links, including /organizations and /app/... routes.

Preserve backend cookie paths when choosing a reverse proxy. Refresh cookies are
Path=/auth; blindly adding an /api prefix would prevent that cookie matching
/api/auth/refresh. A prefix deployment needs an explicitly reviewed proxy cookie
path configuration, or an API origin with unchanged paths. Keep the CSRF cookie
readable on the frontend hostname. No deployment or proxy configuration was
performed in this task.

Use docs/codex/FRONTEND_PROGRESS.md for the final, actually executed results.
Live backend/database mutation tests require separate explicit authorization.
