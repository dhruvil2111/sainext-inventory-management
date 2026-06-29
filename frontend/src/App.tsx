import { Routes, Route, Navigate } from "react-router-dom";
import { RequireAuth, RequirePermission } from "@/components/layout/RouteGuards";
import { AppLayout } from "@/components/layout/AppLayout";
import Login from "@/pages/Login";
import ForgotPassword from "@/pages/ForgotPassword";
import Dashboard from "@/pages/Dashboard";
import Users from "@/pages/Users";
import RolesPermissions from "@/pages/RolesPermissions";
import Warehouses from "@/pages/Warehouses";
import Products from "@/pages/Products";
import StockInward from "@/pages/StockInward";
import StockLedger from "@/pages/StockLedger";
import StockCheck from "@/pages/StockCheck";
import MaterialBlocking from "@/pages/MaterialBlocking";
import Orders from "@/pages/Orders";
import Dispatch from "@/pages/Dispatch";
import Dealers from "@/pages/Dealers";
import SalesmanDashboard from "@/pages/SalesmanDashboard";
import AccountsDashboard from "@/pages/AccountsDashboard";
import Reports from "@/pages/Reports";
import Settings from "@/pages/Settings";
import AuditLog from "@/pages/AuditLog";
import ComingSoon from "@/pages/ComingSoon";

function P({ code, children }: { code: string; children: JSX.Element }) {
  return <RequirePermission code={code}>{children}</RequirePermission>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<P code="Dashboard:view"><Dashboard /></P>} />
        <Route path="users" element={<P code="Users:view"><Users /></P>} />
        <Route path="roles" element={<P code="Roles & Permissions:view"><RolesPermissions /></P>} />
        <Route path="warehouses" element={<P code="Warehouses:view"><Warehouses /></P>} />
        <Route path="products" element={<P code="Products:view"><Products /></P>} />
        <Route path="stock-inward" element={<P code="Stock Inward:view"><StockInward /></P>} />
        <Route path="stock-ledger" element={<P code="Stock Inward:view"><StockLedger /></P>} />

        <Route path="stock-check" element={<P code="Stock Check:view"><StockCheck /></P>} />

        <Route path="blocks" element={<P code="Stock Blocking:view"><MaterialBlocking /></P>} />
        <Route path="orders" element={<P code="Orders:view"><Orders /></P>} />
        <Route path="dispatch" element={<P code="Dispatch:view"><Dispatch /></P>} />
        <Route path="dealers" element={<P code="Dealers:view"><Dealers /></P>} />
        <Route path="salesman" element={<P code="Salesman Dashboard:view"><SalesmanDashboard /></P>} />
        <Route path="accounts" element={<P code="Accounts:view"><AccountsDashboard /></P>} />
        <Route path="reports" element={<P code="Reports:view"><Reports /></P>} />

        <Route path="settings" element={<P code="Settings:view"><Settings /></P>} />
        <Route path="audit-logs" element={<P code="Roles & Permissions:view"><AuditLog /></P>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
