import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Badge, TableSkeleton, EmptyState } from "@/components/ui";
import { Wallet } from "@phosphor-icons/react";

export default function AccountsDashboard() {
  const { push } = useToast();
  const [d, setD] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/accounts/dashboard").then(setD).catch((e) => push(e.message, "error")).finally(() => setLoading(false));
  }, []); // eslint-disable-line

  if (loading) return <Card><TableSkeleton rows={6} /></Card>;
  if (!d) return <EmptyState icon={<Wallet size={22} weight="duotone" />} title="No data" />;

  return (
    <div>
      <PageHeader icon={Wallet} title="Accounts Dashboard" subtitle="Dealer dues, payments and outstanding" />

      <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card className="p-4"><div className="text-xs uppercase text-muted">Total outstanding</div>
          <div className="mt-1 text-2xl font-extrabold text-danger">₹{d.total_outstanding.toLocaleString()}</div></Card>
        <Card className="p-4"><div className="text-xs uppercase text-muted">Dealers with dues</div>
          <div className="mt-1 text-2xl font-extrabold text-warning">{d.dealers_with_dues}</div></Card>
      </div>

      <Card className="overflow-hidden">
        {d.rows.length === 0 ? <EmptyState icon={<Wallet size={22} weight="duotone" />} title="No dealer balances" /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-xs uppercase text-muted">
                <tr><th className="px-4 py-3">Dealer</th><th className="px-4 py-3 text-right">Dues</th>
                  <th className="px-4 py-3 text-right">Paid</th><th className="px-4 py-3 text-right">Outstanding</th>
                  <th className="px-4 py-3 text-right">Credit</th><th className="px-4 py-3">Alert</th></tr>
              </thead>
              <tbody>
                {d.rows.map((r: any) => (
                  <tr key={r.dealer_id} className="border-t border-line">
                    <td className="px-4 py-3 font-medium text-ink">{r.firm_name}</td>
                    <td className="px-4 py-3 text-right text-muted">₹{r.total_dues.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-muted">₹{r.total_paid.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right font-semibold text-ink">₹{r.outstanding.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-muted">{r.credit_period_days}d</td>
                    <td className="px-4 py-3">{r.alert ? <Badge tone="danger">due</Badge> : <Badge tone="success">clear</Badge>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
