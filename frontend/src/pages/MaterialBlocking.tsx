import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Badge, Modal, Spinner, TableSkeleton, EmptyState, ConfirmModal } from "@/components/ui";
import { ProductPicker } from "@/components/ProductPicker";
import type { Block, BlockSummary, Product, StockItem, Paginated } from "@/types";
import { LockKey } from "@phosphor-icons/react";

const STATUSES = ["DRAFT", "PENDING_APPROVAL", "APPROVED", "REJECTED", "RELEASED", "EXPIRED", "CONVERTED"];

function statusTone(s: string): "success" | "danger" | "warning" | "neutral" | "accent" {
  if (s === "APPROVED") return "success";
  if (s === "PENDING_APPROVAL") return "warning";
  if (s === "REJECTED" || s === "EXPIRED") return "danger";
  if (s === "CONVERTED") return "accent";
  return "neutral";
}

export default function MaterialBlocking() {
  const { can } = useAuth();
  const { push } = useToast();
  const [data, setData] = useState<Paginated<Block> | null>(null);
  const [summary, setSummary] = useState<BlockSummary | null>(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [openCreate, setOpenCreate] = useState(false);
  const [confirm, setConfirm] = useState<{ block: Block; action: string } | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const qs = status ? `?status=${status}` : "";
      const [b, s] = await Promise.all([
        api.get(`/blocks${qs}`),
        api.get("/blocks/summary").catch(() => null),
      ]);
      setData(b); setSummary(s);
    } catch (e: any) { push(e.message, "error"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status]);

  const act = async (block: Block, action: string) => {
    try {
      if (action === "convert") {
        const r = await api.post(`/blocks/${block.id}/convert-to-order`);
        push(`Converted to order ${r.order_no}`, "success");
      } else {
        await api.post(`/blocks/${block.id}/${action}`);
        push(`Block ${action}d`, "success");
      }
      setConfirm(null); load();
    } catch (e: any) { push(e.message, "error"); }
  };

  const cards: { label: string; key: keyof BlockSummary; tone: string }[] = [
    { label: "Pending approval", key: "pending_approval", tone: "text-warning" },
    { label: "Approved (active)", key: "approved", tone: "text-success" },
    { label: "Expiring today", key: "expiring_today", tone: "text-warning" },
    { label: "Expired", key: "expired", tone: "text-danger" },
  ];

  return (
    <div>
      <PageHeader icon={LockKey} title="Material Blocking" subtitle="Reserve stock for dealers for a fixed period"
        actions={can("Stock Blocking:create") && <Button onClick={() => setOpenCreate(true)}>+ New Block</Button>} />

      {summary && (
        <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {cards.map((c) => (
            <Card key={c.key} className="p-4">
              <div className="text-xs uppercase text-muted">{c.label}</div>
              <div className={`mt-1 text-3xl font-extrabold ${c.tone}`}>{summary[c.key]}</div>
            </Card>
          ))}
        </div>
      )}

      <Card className="mb-4 p-3">
        <select className="input max-w-xs" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
        </select>
      </Card>

      <Card className="overflow-hidden">
        {loading ? <TableSkeleton /> : !data?.items.length ? (
          <EmptyState icon={<LockKey size={22} weight="duotone" />} title="No blocks" hint="Create a block to reserve stock for a dealer." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Block</th><th className="px-4 py-3">Product</th>
                  <th className="px-4 py-3">Dealer</th><th className="px-4 py-3 text-right">Qty</th>
                  <th className="px-4 py-3">Hold until</th><th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((b) => (
                  <tr key={b.id} className="border-t border-line">
                    <td className="px-4 py-3 font-semibold text-ink">{b.block_no}</td>
                    <td className="px-4 py-3">{b.product_code}<div className="text-xs text-muted">{b.product_name}</div></td>
                    <td className="px-4 py-3 text-muted">{b.dealer_name || "-"}</td>
                    <td className="px-4 py-3 text-right font-medium text-ink">{b.required_qty}</td>
                    <td className="px-4 py-3 text-muted">{b.hold_until ? new Date(b.hold_until).toLocaleDateString() : "-"}</td>
                    <td className="px-4 py-3"><Badge tone={statusTone(b.status)}>{b.status.replace(/_/g, " ")}</Badge></td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex flex-wrap justify-end gap-1">
                        {b.status === "PENDING_APPROVAL" && can("Stock Blocking:approve") &&
                          <Button variant="ghost" className="!py-1 !px-2 text-success" onClick={() => act(b, "approve")}>Approve</Button>}
                        {b.status === "PENDING_APPROVAL" && can("Stock Blocking:reject") &&
                          <Button variant="ghost" className="!py-1 !px-2 text-danger" onClick={() => setConfirm({ block: b, action: "reject" })}>Reject</Button>}
                        {b.status === "APPROVED" && can("Stock Blocking:convert_block_to_order") &&
                          <Button variant="ghost" className="!py-1 !px-2 text-accent" onClick={() => setConfirm({ block: b, action: "convert" })}>Convert</Button>}
                        {(b.status === "APPROVED" || b.status === "PENDING_APPROVAL") && can("Stock Blocking:release_stock") &&
                          <Button variant="ghost" className="!py-1 !px-2" onClick={() => setConfirm({ block: b, action: "release" })}>Release</Button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {openCreate && <CreateBlockModal onClose={() => setOpenCreate(false)} onDone={() => { setOpenCreate(false); load(); }} push={push} />}
      {confirm && (
        <ConfirmModal open onClose={() => setConfirm(null)}
          onConfirm={() => act(confirm.block, confirm.action)}
          danger={confirm.action === "reject"}
          title={`${confirm.action[0].toUpperCase()}${confirm.action.slice(1)} block ${confirm.block.block_no}?`}
          message={confirm.action === "convert"
            ? "This will create a stock-committed order from the blocked material."
            : `This will ${confirm.action} the block and update saleable stock accordingly.`} />
      )}
    </div>
  );
}

function CreateBlockModal({ onClose, onDone, push }: any) {
  const [product, setProduct] = useState<Product | null>(null);
  const [items, setItems] = useState<StockItem[]>([]);
  const [qty, setQty] = useState<Record<number, string>>({});
  const [holdUntil, setHoldUntil] = useState("");
  const [remarks, setRemarks] = useState("");
  const [submit, setSubmit] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadingItems, setLoadingItems] = useState(false);

  useEffect(() => {
    if (!product) { setItems([]); return; }
    setLoadingItems(true);
    api.get(`/stock/items?product_id=${product.id}&only_available=true`)
      .then((d) => setItems(d.items)).catch(() => {})
      .finally(() => setLoadingItems(false));
  }, [product]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!product) return push("Select a product", "error");
    const picked = Object.entries(qty)
      .filter(([, v]) => Number(v) > 0)
      .map(([sid, v]) => ({ stock_item_id: Number(sid), qty: Number(v) }));
    if (!picked.length) return push("Enter a quantity on at least one item", "error");
    setSaving(true);
    try {
      await api.post("/blocks", {
        product_id: product.id, items: picked,
        hold_until: holdUntil ? new Date(holdUntil).toISOString() : null,
        remarks: remarks || null, submit,
      });
      push(submit ? "Block submitted for approval" : "Block saved as draft", "success");
      onDone();
    } catch (err: any) { push(err.message, "error"); }
    finally { setSaving(false); }
  };

  return (
    <Modal open onClose={onClose} title="New material block"
      footer={<>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button onClick={save as any} disabled={saving}>{saving ? <Spinner /> : (submit ? "Submit for approval" : "Save draft")}</Button>
      </>}>
      <form onSubmit={save} className="space-y-4">
        <div><label className="label">Product</label>
          <ProductPicker value={product} onChange={setProduct} /></div>

        {product && (
          <div>
            <label className="label">Select stock & quantity to block</label>
            {loadingItems ? <div className="py-4 text-center text-accent"><Spinner className="h-5 w-5" /></div>
              : items.length === 0 ? <p className="text-sm text-muted">No available stock for this product.</p>
              : (
                <div className="max-h-56 space-y-2 overflow-y-auto">
                  {items.map((it) => (
                    <div key={it.id} className="flex items-center gap-2 rounded-lg border border-line p-2 text-sm">
                      <div className="flex-1">
                        <b className="text-ink">{it.warehouse_name}</b>
                        <span className="text-muted"> · {it.batch_no || "no batch"} · {it.roll_no || it.item_type} · avail {it.available_qty} {it.unit}</span>
                      </div>
                      <input className="input w-24 !py-1" type="number" step="any" min="0" max={it.available_qty}
                        placeholder="qty" value={qty[it.id] || ""}
                        onChange={(e) => setQty({ ...qty, [it.id]: e.target.value })} />
                    </div>
                  ))}
                </div>
              )}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Hold until</label>
            <input className="input" type="date" value={holdUntil} onChange={(e) => setHoldUntil(e.target.value)} /></div>
          <div className="flex items-end pb-1">
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="checkbox" checked={submit} onChange={(e) => setSubmit(e.target.checked)} />
              Submit for approval
            </label>
          </div>
        </div>
        <div><label className="label">Remarks</label>
          <input className="input" value={remarks} onChange={(e) => setRemarks(e.target.value)} /></div>
      </form>
    </Modal>
  );
}
