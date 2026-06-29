import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Badge, StatusDot, Modal, Spinner, EmptyState } from "@/components/ui";
import { RecommendationModal } from "@/components/RecommendationModal";
import type { Warehouse, StockCheckResponse, StockCheckResult, StockItemDetail } from "@/types";
import { MagnifyingGlass, Package, WarningCircle } from "@phosphor-icons/react";

export default function StockCheck() {
  const { push } = useToast();
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [q, setQ] = useState("");
  const [wh, setWh] = useState("");
  const [req, setReq] = useState("");
  const [resp, setResp] = useState<StockCheckResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [batchFor, setBatchFor] = useState<StockCheckResult | null>(null);
  const [recoFor, setRecoFor] = useState<StockCheckResult | null>(null);
  const reqNum = Number(req) || 0;

  useEffect(() => { api.get("/warehouses").then(setWarehouses).catch(() => {}); }, []);

  const search = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!q.trim()) return push("Enter a pattern no., code or name", "error");
    setLoading(true); setSearched(true);
    const params = new URLSearchParams({ q: q.trim() });
    if (wh) params.set("warehouse_id", wh);
    if (req) params.set("required_qty", req);
    try { setResp(await api.get(`/stock/check?${params}`)); }
    catch (err: any) { push(err.message, "error"); setResp(null); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <PageHeader icon={MagnifyingGlass} title="Stock Check" subtitle="Search by pattern no., design code or name for live availability" />

      <Card className="mb-5 p-4">
        <form onSubmit={search} className="grid gap-3 md:grid-cols-[1fr_200px_160px_auto]">
          <input className="input" placeholder="Pattern No. / Code / Name…" value={q}
            onChange={(e) => setQ(e.target.value)} autoFocus />
          <select className="input" value={wh} onChange={(e) => setWh(e.target.value)}>
            <option value="">All warehouses</option>
            {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <input className="input" type="number" step="any" placeholder="Required qty" value={req}
            onChange={(e) => setReq(e.target.value)} />
          <Button type="submit" disabled={loading} className="md:w-32">
            {loading ? <Spinner /> : "Search"}
          </Button>
        </form>
      </Card>

      {loading && <div className="flex justify-center py-12 text-accent"><Spinner className="h-8 w-8" /></div>}

      {!loading && searched && resp && resp.count === 0 && (
        <Card><EmptyState icon={<MagnifyingGlass size={22} weight="duotone" />} title="No matching product" hint="Try a different pattern number, code, or name." /></Card>
      )}

      <div className="space-y-5">
        {resp?.results.map((r) => (
          <ResultCard key={r.product.id} r={r} canPrice={resp.can_view_price}
            canBatch={resp.can_view_batch_details} reqQty={reqNum}
            onViewBatch={() => setBatchFor(r)} onRecommend={() => setRecoFor(r)} />
        ))}
      </div>

      {batchFor && (
        <ViewBatchModal result={batchFor} onClose={() => setBatchFor(null)} />
      )}
      {recoFor && (
        <RecommendationModal productId={recoFor.product.id}
          productLabel={`${recoFor.product.pattern_no} · ${recoFor.product.name}`}
          requiredQty={reqNum} warehouseId={wh ? Number(wh) : null}
          onClose={() => setRecoFor(null)} />
      )}
    </div>
  );
}

const TONE = { green: "success", yellow: "warning", red: "danger" } as const;

function ResultCard({ r, canPrice, canBatch, reqQty, onViewBatch, onRecommend }: {
  r: StockCheckResult; canPrice: boolean; canBatch: boolean; reqQty: number;
  onViewBatch: () => void; onRecommend: () => void;
}) {
  const p = r.product;
  const fmt = (n: number) => `${(+n).toLocaleString()} ${p.unit}`;
  return (
    <Card className="overflow-hidden">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line p-5">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-ink">{p.pattern_no}</h3>
            <Badge tone="neutral">{p.product_code}</Badge>
            <Badge tone={p.status === "CONTINUED" ? "success" : "warning"}>{p.status}</Badge>
          </div>
          <p className="text-sm text-muted">{p.name}{p.collection_name ? ` · ${p.collection_name}` : ""}</p>
        </div>
        <div className="text-right">
          {canPrice && p.price != null && (
            <div className="text-lg font-bold text-ink">₹{(+p.price).toLocaleString()}</div>
          )}
          <div className="mt-1 flex justify-end gap-2">
            {reqQty > 0 && (
              <Button variant="outline" className="!py-1.5" onClick={onRecommend}>Suggest allocation</Button>
            )}
            {canBatch && (
              <Button variant="accent" className="!py-1.5" onClick={onViewBatch}>View Batch</Button>
            )}
          </div>
        </div>
      </div>

      {/* totals - explicit color classes so Tailwind keeps them */}
      <div className="grid grid-cols-2 gap-px bg-line sm:grid-cols-4">
        {[
          { label: "Total available", val: fmt(r.total_available), cls: "text-ink" },
          { label: "Blocked", val: fmt(r.total_blocked), cls: r.total_blocked > 0 ? "text-warning" : "text-muted" },
          { label: "Saleable", val: fmt(r.total_saleable), cls: r.negative_warning ? "text-danger" : "text-success" },
          { label: "Required", val: r.required_qty ? fmt(r.required_qty) : "-", cls: "text-muted" },
        ].map((t) => (
          <div key={t.label} className="bg-surface p-4">
            <div className="text-xs uppercase text-muted">{t.label}</div>
            <div className={`mt-1 text-lg font-bold ${t.cls}`}>{t.val}</div>
          </div>
        ))}
      </div>

      {r.required_qty > 0 && (
        <div className={`flex items-center gap-2 px-5 py-2.5 text-sm font-medium ${
          r.can_fulfill ? "bg-success/10 text-success" : "bg-warning/10 text-warning"}`}>
          <StatusDot tone={r.status === "green" ? "success" : r.status === "yellow" ? "warning" : "danger"} />
          {r.can_fulfill ? "Required quantity can be fulfilled" : "Insufficient saleable stock for required quantity"}
        </div>
      )}
      {r.negative_warning && (
        <div className="flex items-center gap-2 bg-danger/10 px-5 py-2.5 text-sm font-medium text-danger">
          <WarningCircle size={16} weight="fill" /> Negative saleable stock. Review adjustments and blocks.
        </div>
      )}

      {/* warehouse-wise availability */}
      <div className="p-5">
        <h4 className="mb-3 text-sm font-bold text-ink">Warehouse availability</h4>
        <div className="space-y-2">
          {r.warehouses.length === 0 && <p className="text-sm text-muted">No stock recorded for this product.</p>}
          {r.warehouses.map((w) => (
            <div key={w.warehouse_id} className="flex items-center justify-between rounded-xl border border-line bg-surface-2 px-4 py-3">
              <span className="font-medium text-ink">{w.warehouse_name}</span>
              <div className="flex items-center gap-3">
                <span className="font-semibold text-ink">{fmt(w.saleable)}</span>
                {w.blocked > 0 && <Badge tone="warning">{fmt(w.blocked)} blocked</Badge>}
                <StatusDot tone={TONE[w.status]} />
              </div>
            </div>
          ))}
        </div>

        {canBatch && r.batches && r.batches.length > 0 && (
          <>
            <h4 className="mb-3 mt-5 text-sm font-bold text-ink">Batch-wise (old stock first)</h4>
            <div className="flex flex-wrap gap-2">
              {r.batches.map((b) => (
                <div key={b.batch_id} className="rounded-xl border border-line px-3 py-2 text-sm">
                  <b className="text-ink">{b.batch_no}</b>
                  <span className="text-muted"> · {b.batch_date || "no date"} · </span>
                  <span className="font-semibold text-ink">{fmt(b.saleable)}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* product detail + refill placeholder */}
      <div className="grid gap-px border-t border-line bg-line sm:grid-cols-3">
        {[
          ["Unit", p.unit], ["Unit size", p.unit_size || "-"], ["Thickness", p.thickness || "-"],
          ["Roll size", p.roll_size || "-"], ["Brand", p.brand || "-"],
          ["Next refill", "Not in transit"],
        ].map(([k, v]) => (
          <div key={k} className="bg-surface p-3">
            <div className="text-xs uppercase text-muted">{k}</div>
            <div className="text-sm font-medium text-ink">{v}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function ViewBatchModal({ result, onClose }: { result: StockCheckResult; onClose: () => void }) {
  const items = result.items || [];
  return (
    <Modal open onClose={onClose} title={`Batch detail · ${result.product.pattern_no}`}>
      <div className="max-h-[65vh] overflow-auto">
        {items.length === 0 ? (
          <EmptyState icon={<Package size={22} weight="duotone" />} title="No stock items" />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-left text-xs uppercase text-muted">
              <tr>
                <th className="px-3 py-2">WH</th><th className="px-3 py-2">Batch</th>
                <th className="px-3 py-2">Roll/Box</th><th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Dates (batch/roll/inward)</th>
                <th className="px-3 py-2 text-right">Avail</th>
                <th className="px-3 py-2 text-right">Blocked</th>
                <th className="px-3 py-2 text-right">Saleable</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it: StockItemDetail) => (
                <tr key={it.stock_item_id} className="border-t border-line">
                  <td className="px-3 py-2 text-muted">{it.warehouse_name}</td>
                  <td className="px-3 py-2 font-medium text-ink">{it.batch_no || "-"}</td>
                  <td className="px-3 py-2">{it.roll_no || (it.box_count ? `${it.box_count} box` : "-")}</td>
                  <td className="px-3 py-2"><Badge tone="neutral">{it.item_type}</Badge></td>
                  <td className="px-3 py-2 text-xs text-muted">
                    {(it.batch_date || "-")} / {(it.roll_date || "-")} / {(it.inward_date || "-")}
                  </td>
                  <td className="px-3 py-2 text-right text-muted">{it.available_qty} {it.unit}</td>
                  <td className="px-3 py-2 text-right">{it.blocked_qty || 0}</td>
                  <td className="px-3 py-2 text-right font-semibold text-ink">{it.saleable_qty} {it.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Modal>
  );
}
