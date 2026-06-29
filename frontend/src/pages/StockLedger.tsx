import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Badge, TableSkeleton, EmptyState } from "@/components/ui";
import type { LedgerRow, Warehouse, Paginated } from "@/types";
import { Scroll } from "@phosphor-icons/react";

const TXN_TYPES = [
  "INWARD", "OUTWARD", "BLOCK", "BLOCK_RELEASE", "ORDER_COMMIT",
  "ORDER_CANCEL_RELEASE", "TRANSFER_IN", "TRANSFER_OUT", "ADJUSTMENT_IN",
  "ADJUSTMENT_OUT", "DAMAGE", "RETURN_IN",
];

const IN_TYPES = ["INWARD", "TRANSFER_IN", "ADJUSTMENT_IN", "RETURN_IN", "BLOCK_RELEASE", "ORDER_CANCEL_RELEASE"];

function tone(t: string): "success" | "danger" | "warning" | "neutral" {
  if (IN_TYPES.includes(t)) return "success";
  if (["OUTWARD", "TRANSFER_OUT", "ADJUSTMENT_OUT", "DAMAGE", "ORDER_COMMIT"].includes(t)) return "danger";
  if (t.startsWith("BLOCK")) return "warning";
  return "neutral";
}

export default function StockLedger() {
  const { push } = useToast();
  const [data, setData] = useState<Paginated<LedgerRow> | null>(null);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [wh, setWh] = useState("");
  const [txn, setTxn] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.get("/warehouses").then(setWarehouses).catch(() => {}); }, []);

  const load = async () => {
    setLoading(true);
    const qs = new URLSearchParams({ page: String(page), page_size: "50" });
    if (wh) qs.set("warehouse_id", wh);
    if (txn) qs.set("txn_type", txn);
    try { setData(await api.get(`/stock/ledger?${qs}`)); }
    catch (e: any) { push(e.message, "error"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [wh, txn, page]);

  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div>
      <PageHeader icon={Scroll} title="Stock Ledger" subtitle="Append-only record of every stock movement" />

      <Card className="mb-4 flex flex-wrap gap-3 p-3">
        <select className="input max-w-xs" value={wh} onChange={(e) => { setPage(1); setWh(e.target.value); }}>
          <option value="">All warehouses</option>
          {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
        </select>
        <select className="input max-w-xs" value={txn} onChange={(e) => { setPage(1); setTxn(e.target.value); }}>
          <option value="">All transaction types</option>
          {TXN_TYPES.map((t) => <option key={t}>{t}</option>)}
        </select>
      </Card>

      <Card className="overflow-hidden">
        {loading ? <TableSkeleton /> : !data?.items.length ? (
          <EmptyState icon={<Scroll size={22} weight="duotone" />} title="No ledger entries" hint="Stock movements will appear here." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">#</th><th className="px-4 py-3">Product</th>
                  <th className="px-4 py-3">Warehouse</th><th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3 text-right">Qty</th>
                  <th className="px-4 py-3 text-right">Before</th>
                  <th className="px-4 py-3 text-right">After</th>
                  <th className="px-4 py-3">When</th><th className="px-4 py-3">Remarks</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((l) => (
                  <tr key={l.id} className="border-t border-line">
                    <td className="px-4 py-3 text-muted">{l.id}</td>
                    <td className="px-4 py-3 font-medium text-ink">{l.product_code}</td>
                    <td className="px-4 py-3 text-muted">{l.warehouse_name}</td>
                    <td className="px-4 py-3"><Badge tone={tone(l.txn_type)}>{l.txn_type}</Badge></td>
                    <td className="px-4 py-3 text-right font-semibold text-ink">{l.qty}</td>
                    <td className="px-4 py-3 text-right text-muted">{l.before_qty}</td>
                    <td className="px-4 py-3 text-right text-muted">{l.after_qty}</td>
                    <td className="px-4 py-3 text-muted">{l.created_at ? new Date(l.created_at).toLocaleString() : "-"}</td>
                    <td className="px-4 py-3 text-muted">{l.remarks || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && pages > 1 && (
          <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm">
            <span className="text-muted">{data.total} entries · page {page}/{pages}</span>
            <div className="flex gap-2">
              <button className="btn-outline !py-1" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
              <button className="btn-outline !py-1" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
