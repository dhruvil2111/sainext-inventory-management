import { useEffect, useState } from "react";
import {
  Tag, Package, Warehouse, Handshake, Receipt, Hourglass, LockKey, UsersThree,
  type Icon,
} from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Badge, TableSkeleton } from "@/components/ui";

interface Stats {
  users: number; warehouses: number; products: number; dealers: number;
  stock_items: number; orders_total: number; orders_pending: number;
  blocks_pending: number; blocks_approved: number;
}
interface BlockSummary {
  pending_approval: number; approved: number; expiring_today: number; expired: number;
}

const TILES: { key: keyof Stats; label: string; icon: Icon; alert?: boolean }[] = [
  { key: "products", label: "Products", icon: Tag },
  { key: "stock_items", label: "Stock items", icon: Package },
  { key: "warehouses", label: "Warehouses", icon: Warehouse },
  { key: "dealers", label: "Dealers", icon: Handshake },
  { key: "orders_total", label: "Total orders", icon: Receipt },
  { key: "orders_pending", label: "Orders pending", icon: Hourglass, alert: true },
  { key: "blocks_pending", label: "Blocks pending", icon: LockKey, alert: true },
  { key: "users", label: "Users", icon: UsersThree },
];

export default function Dashboard() {
  const { user, can } = useAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [blocks, setBlocks] = useState<BlockSummary | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/dashboard/stats").then(setStats).catch((e) => setErr(e.message));
    if (can("Stock Blocking:view")) api.get("/blocks/summary").then(setBlocks).catch(() => {});
  }, []); // eslint-disable-line

  return (
    <div>
      <PageHeader
        title={`Welcome back, ${user?.name?.split(" ")[0]}`}
        subtitle="Live snapshot of inventory and order activity"
        actions={<Badge tone="accent" dot>{user?.role_name}</Badge>}
      />

      {err && <Card className="mb-4 p-4 text-sm text-danger">{err}</Card>}

      {!stats ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => <Card key={i}><TableSkeleton rows={1} /></Card>)}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {TILES.map((t) => {
            const val = stats[t.key];
            const flag = t.alert && val > 0;
            return (
              <Card key={t.key} className="p-4 transition hover:shadow-pop">
                <div className="flex items-center justify-between">
                  <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${flag ? "bg-warning/15 text-warning" : "bg-surface-2 text-muted"}`}>
                    <t.icon size={18} weight="duotone" />
                  </span>
                  {flag && <Badge tone="warning">action</Badge>}
                </div>
                <div className="mt-3 font-mono text-3xl font-semibold tracking-tight text-ink tabular">{val}</div>
                <div className="text-sm text-muted">{t.label}</div>
              </Card>
            );
          })}
        </div>
      )}

      {blocks && (
        <div className="mt-7">
          <h3 className="mb-3 text-sm font-semibold text-ink">Material blocking alerts</h3>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[
              { label: "Pending approval", val: blocks.pending_approval, tone: "text-warning" },
              { label: "Approved (active)", val: blocks.approved, tone: "text-success" },
              { label: "Expiring today", val: blocks.expiring_today, tone: "text-warning" },
              { label: "Expired", val: blocks.expired, tone: "text-danger" },
            ].map((c) => (
              <Card key={c.label} className="p-4">
                <div className="text-2xs font-medium uppercase tracking-wider text-muted">{c.label}</div>
                <div className={`mt-1 font-mono text-2xl font-semibold tabular ${c.tone}`}>{c.val}</div>
              </Card>
            ))}
          </div>
        </div>
      )}

      <div className="mt-7 grid gap-3 lg:grid-cols-3">
        <Card className="p-5">
          <h3 className="mb-3 text-sm font-semibold text-ink">Availability legend</h3>
          <div className="space-y-2.5 text-sm text-muted">
            <div className="flex items-center gap-2.5"><span className="h-2.5 w-2.5 rounded-full bg-success" /> Available</div>
            <div className="flex items-center gap-2.5"><span className="h-2.5 w-2.5 rounded-full bg-warning" /> Partial / blocked / warning</div>
            <div className="flex items-center gap-2.5"><span className="h-2.5 w-2.5 rounded-full bg-danger" /> Not available</div>
          </div>
        </Card>
        <Card className="p-5 lg:col-span-2">
          <h3 className="mb-2 text-sm font-semibold text-ink">Your modules</h3>
          <p className="text-sm leading-relaxed text-muted">
            Stock check with the old-stock-first recommendation engine, inward and
            ledger, material blocking, orders and dispatch, dealer, salesman and
            accounts dashboards, and reports with export are all available from the
            sidebar. Configure your company and brand under Settings.
          </p>
        </Card>
      </div>
    </div>
  );
}
