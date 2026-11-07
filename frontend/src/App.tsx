import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, ProtectedRoute } from './lib/auth'
import { NoticeProvider, Empty } from './components/ui'
import { TenantLayout } from './components/layout'
import { AuthPage } from './features/auth-pages'
import { MembersPage, OrganizationSettings, OrganizationsPage } from './features/organizations'
import { DashboardPage } from './features/dashboard'
import { CatalogDetail, CatalogPage } from './features/catalog'
import { OrderDetail, OrderEditor, OrdersPage } from './features/orders'

export function AppRoutes() {
  return (
    <AuthProvider>
      <NoticeProvider>
        <Routes>
          <Route path="/login" element={<AuthPage key="login" />} />
          <Route path="/register" element={<AuthPage key="register" register />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Navigate to="/organizations" replace />} />
            <Route path="/organizations" element={<OrganizationsPage />} />
            <Route path="/app/:organizationId" element={<TenantLayout />}>
              <Route index element={<Navigate to="dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="products" element={<CatalogPage key="products" kind="products" />} />
              <Route
                path="products/:productId"
                element={<CatalogDetail key="products" kind="products" />}
              />
              <Route
                path="warehouses"
                element={<CatalogPage key="warehouses" kind="warehouses" />}
              />
              <Route
                path="warehouses/:warehouseId"
                element={<CatalogDetail key="warehouses" kind="warehouses" />}
              />
              <Route path="orders" element={<OrdersPage />} />
              <Route path="orders/new" element={<OrderEditor />} />
              <Route path="orders/:orderId" element={<OrderDetail />} />
              <Route path="orders/:orderId/edit" element={<OrderEditor editing />} />
              <Route path="members" element={<MembersPage />} />
              <Route path="settings" element={<OrganizationSettings />} />
            </Route>
          </Route>
          <Route
            path="*"
            element={
              <Empty
                title="This page is off the map"
                description="Choose a workspace to find your way back."
                action={
                  <Link className="btn btn-primary" to="/organizations">
                    Go to workspaces
                  </Link>
                }
              />
            }
          />
        </Routes>
      </NoticeProvider>
    </AuthProvider>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
