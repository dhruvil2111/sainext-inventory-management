import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Badge, TableSkeleton, EmptyState } from "@/components/ui";
import { orderTone } from "./Orders";
import type { Order, Paginated } from "@/types";
import { Truck } from "@phosphor-icons/react";

const STAGES = ["APPROVED", "IN_PROCESS", "READY_FOR_DISPATCH", "DISPATCHED"];
const NEXT: Record<string, { action: string; label: string } | null> = {
  APPROVED: { action: "in-process", label: "Start processing" },
  IN_PROCESS: { action: "ready-for-dispatch", label: "Ready for dispatch" },
  READY_FOR_DISPATCH: { action: "dispatched", label: "Mark dispatched" },
  DISPATCHED: { action: "completed", label: "Mark completed" },
};

export default function Dispatch() {
  const { can } = useAuth();
  const { push } = useToast();
  const [rows, setRows] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [stage, setStage] = useState("");
  const canAct = can("Dispatch:edit") || can("Orders:edit");

  const load = async () => {
    setLoading(true);
    try {
      // pull active dispatch-stage orders
      const wanted = stage ? [stage] : STAGES;
      const results = await Promise.all(
        wanted.map((s) => api.get(`/orders?status=${s}&page_size=100`).then((d: Paginated<Order>) => d.items))
      );
      setRows(results.flat().sort((a, b) => b.id - a.id));
    } catch (e: any) { push(e.message, "error"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [stage]);

  const advance = async (o: Order) => {
    const n = NEXT[o.status];
    if (!n) return;
    try { await api.post(`/orders/${o.id}/${n.action}`); push(`Order ${o.order_no}: ${n.label}`, "success"); load(); }
    catch (e: any) { push(e.message, "error"); }
  };

  return (
    <div>
      <PageHeader icon={Truck} title="Dispatch" subtitle="Move approved orders through to dispatch and completion" />

      <Card className="mb-4 p-3">
        <select className="input max-w-xs" value={stage} onChange={(e) => setStage(e.target.value)}>
          <option value="">All active stages</option>
          {STAGES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
        </select>
      </Card>

      <Card className="overflow-hidden">
        {loading ? <TableSkeleton /> : !rows.length ? (
          <EmptyState icon={<Truck size={22} weight="duotone" />} title="Nothing to dispatch" hint="Approved orders awaiting dispatch will appear here." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Order</th><th className="px-4 py-3">Product</th>
                  <th className="px-4 py-3">Dealer</th><th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((o) => (
                  <tr key={o.id} className="border-t border-line">
                    <td className="px-4 py-3 font-semibold text-ink">{o.order_no}</td>
                    <td className="px-4 py-3">{o.items[0]?.product_snapshot?.product_code || "-"}</td>
                    <td className="px-4 py-3 text-muted">{o.dealer_name || "-"}</td>
                    <td className="px-4 py-3"><Badge tone={orderTone(o.status)}>{o.status.replace(/_/g, " ")}</Badge></td>
                    <td className="px-4 py-3 text-right">
                      {canAct && NEXT[o.status] &&
                        <Button variant="accent" className="!py-1.5" onClick={() => advance(o)}>{NEXT[o.status]!.label}</Button>}
                    </td>
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
