import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Badge, TableSkeleton, EmptyState } from "@/components/ui";
import { ChartLineUp, Handshake } from "@phosphor-icons/react";

export default function SalesmanDashboard() {
  const { push } = useToast();
  const [d, setD] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/salesman/dashboard").then(setD).catch((e) => push(e.message, "error")).finally(() => setLoading(false));
  }, []); // eslint-disable-line

  if (loading) return <Card><TableSkeleton rows={6} /></Card>;
  if (!d) return <EmptyState icon={<ChartLineUp size={22} weight="duotone" />} title="No data" />;

  const pct = Math.min(100, d.target_pct);
  const tiles = [
    ["Total orders", d.total_orders], ["Order amount", `₹${d.order_amount.toLocaleString()}`],
    ["Pending approvals", d.pending_approvals], ["Blocked material", d.blocked_material],
  ];

  return (
    <div>
      <PageHeader icon={ChartLineUp} title="Salesman Dashboard" subtitle={`Target vs achievement for ${d.salesman.name}`} />

      <Card className="mb-5 p-5">
        <div className="mb-2 flex items-end justify-between">
          <div>
            <div className="text-xs uppercase text-muted">Monthly target</div>
            <div className="text-2xl font-extrabold text-ink">₹{d.monthly_target.toLocaleString()}</div>
          </div>
          <div className="text-right">
            <div className="text-xs uppercase text-muted">Achieved</div>
            <div className="text-2xl font-extrabold text-success">₹{d.target_achieved.toLocaleString()}</div>
          </div>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-surface-2">
          <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
        </div>
        <div className="mt-1 text-right text-xs text-muted">{d.target_pct}% of target</div>
      </Card>

      <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {tiles.map(([k, v]) => (
          <Card key={k as string} className="p-4">
            <div className="text-xs uppercase text-muted">{k}</div>
            <div className="mt-1 text-2xl font-extrabold text-ink">{v}</div>
          </Card>
        ))}
      </div>

      <Card className="overflow-hidden">
        <div className="border-b border-line px-5 py-3 text-sm font-bold text-ink">My dealers ({d.dealers.length})</div>
        {d.dealers.length === 0 ? <EmptyState icon={<Handshake size={22} weight="duotone" />} title="No dealers assigned" /> : (
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-left text-xs uppercase text-muted">
              <tr><th className="px-4 py-2">Firm</th><th className="px-4 py-2">Category</th><th className="px-4 py-2 text-right">Credit</th><th className="px-4 py-2">Rating</th></tr>
            </thead>
            <tbody>
              {d.dealers.map((x: any) => (
                <tr key={x.id} className="border-t border-line">
                  <td className="px-4 py-2 font-medium text-ink">{x.firm_name}</td>
                  <td className="px-4 py-2">{x.category ? <Badge tone="neutral">{x.category}</Badge> : "-"}</td>
                  <td className="px-4 py-2 text-right text-muted">{x.credit_period_days}d</td>
                  <td className="px-4 py-2">{x.rating ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
