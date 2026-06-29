import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Badge, Modal, Spinner, TableSkeleton, EmptyState, ConfirmModal } from "@/components/ui";
import { ProductPicker } from "@/components/ProductPicker";
import type { Order, Product, StockItem, Paginated } from "@/types";
import { Receipt } from "@phosphor-icons/react";

export const ORDER_STATUSES = [
  "DRAFT", "PENDING_APPROVAL", "APPROVED", "IN_PROCESS", "READY_FOR_DISPATCH",
  "DISPATCHED", "COMPLETED", "CANCELLED", "REJECTED",
];

export function orderTone(s: string): "success" | "danger" | "warning" | "neutral" | "accent" {
  if (["COMPLETED", "DISPATCHED"].includes(s)) return "success";
  if (["PENDING_APPROVAL"].includes(s)) return "warning";
  if (["CANCELLED", "REJECTED"].includes(s)) return "danger";
  if (["APPROVED", "IN_PROCESS", "READY_FOR_DISPATCH"].includes(s)) return "accent";
  return "neutral";
}

export default function Orders() {
  const { can } = useAuth();
  const { push } = useToast();
  const [data, setData] = useState<Paginated<Order> | null>(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [openCreate, setOpenCreate] = useState(false);
  const [detail, setDetail] = useState<Order | null>(null);

  const load = async () => {
    setLoading(true);
    try { setData(await api.get(`/orders${status ? `?status=${status}` : ""}`)); }
    catch (e: any) { push(e.message, "error"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status]);

  return (
    <div>
      <PageHeader icon={Receipt} title="Orders" subtitle="Place orders from saleable stock and track them to completion"
        actions={can("Orders:create") && <Button onClick={() => setOpenCreate(true)}>+ Place Order</Button>} />

      <Card className="mb-4 p-3">
        <select className="input max-w-xs" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {ORDER_STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
        </select>
      </Card>

      <Card className="overflow-hidden">
        {loading ? <TableSkeleton /> : !data?.items.length ? (
          <EmptyState icon={<Receipt size={22} weight="duotone" />} title="No orders" hint="Place an order to get started." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Order</th><th className="px-4 py-3">Product</th>
                  <th className="px-4 py-3">Dealer</th><th className="px-4 py-3 text-right">Amount</th>
                  <th className="px-4 py-3">Committed</th><th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((o) => (
                  <tr key={o.id} className="border-t border-line">
                    <td className="px-4 py-3 font-semibold text-ink">{o.order_no}</td>
                    <td className="px-4 py-3">{o.items[0]?.product_snapshot?.product_code || "-"}</td>
                    <td className="px-4 py-3 text-muted">{o.dealer_name || "-"}</td>
                    <td className="px-4 py-3 text-right text-ink">₹{o.total_amount.toLocaleString()}</td>
                    <td className="px-4 py-3">{o.stock_committed ? <Badge tone="success">yes</Badge> : <Badge tone="neutral">no</Badge>}</td>
                    <td className="px-4 py-3"><Badge tone={orderTone(o.status)}>{o.status.replace(/_/g, " ")}</Badge></td>
                    <td className="px-4 py-3 text-right">
                      <Button variant="ghost" className="!py-1" onClick={() => setDetail(o)}>View</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {openCreate && <PlaceOrderModal onClose={() => setOpenCreate(false)} onDone={() => { setOpenCreate(false); load(); }} push={push} />}
      {detail && <OrderDetailModal order={detail} onClose={() => setDetail(null)} onChanged={() => { setDetail(null); load(); }} push={push} can={can} />}
    </div>
  );
}

function PlaceOrderModal({ onClose, onDone, push }: any) {
  const [product, setProduct] = useState<Product | null>(null);
  const [items, setItems] = useState<StockItem[]>([]);
  const [qty, setQty] = useState<Record<number, string>>({});
  const [remarks, setRemarks] = useState("");
  const [submit, setSubmit] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadingItems, setLoadingItems] = useState(false);

  useEffect(() => {
    if (!product) { setItems([]); return; }
    setLoadingItems(true);
    api.get(`/stock/items?product_id=${product.id}&only_available=true`)
      .then((d) => setItems(d.items)).catch(() => {}).finally(() => setLoadingItems(false));
  }, [product]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!product) return push("Select a product", "error");
    const allocations = Object.entries(qty).filter(([, v]) => Number(v) > 0)
      .map(([sid, v]) => ({ stock_item_id: Number(sid), qty: Number(v) }));
    if (!allocations.length) return push("Enter a quantity on at least one item", "error");
    setSaving(true);
    try {
      await api.post("/orders", {
        product_id: product.id, allocations, is_partial: allocations.length > 0,
        remarks: remarks || null, submit,
      });
      push(submit ? "Order placed for approval" : "Order saved as draft", "success");
      onDone();
    } catch (err: any) { push(err.message, "error"); }
    finally { setSaving(false); }
  };

  return (
    <Modal open onClose={onClose} title="Place order"
      footer={<>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button onClick={save as any} disabled={saving}>{saving ? <Spinner /> : (submit ? "Place order" : "Save draft")}</Button>
      </>}>
      <form onSubmit={save} className="space-y-4">
        <div><label className="label">Product</label>
          <ProductPicker value={product} onChange={setProduct} /></div>
        {product && (
          <div>
            <label className="label">Allocate from stock (partial cuts allowed)</label>
            {loadingItems ? <div className="py-4 text-center text-accent"><Spinner className="h-5 w-5" /></div>
              : items.length === 0 ? <p className="text-sm text-muted">No available stock.</p>
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
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={submit} onChange={(e) => setSubmit(e.target.checked)} />
          Submit for approval
        </label>
        <div><label className="label">Remarks</label>
          <input className="input" value={remarks} onChange={(e) => setRemarks(e.target.value)} /></div>
      </form>
    </Modal>
  );
}

function OrderDetailModal({ order, onClose, onChanged, push, can }: any) {
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<{ action: string; label: string } | null>(null);
  const o: Order = order;

  const act = async (action: string) => {
    setBusy(true);
    try {
      await api.post(`/orders/${o.id}/${action}`);
      push(`Order ${action.replace(/-/g, " ")}`, "success");
      onChanged();
    } catch (e: any) { push(e.message, "error"); }
    finally { setBusy(false); setConfirm(null); }
  };

  const actions: { action: string; label: string; perm: boolean; confirm?: boolean }[] = [];
  if (o.status === "PENDING_APPROVAL") {
    actions.push({ action: "approve", label: "Approve", perm: can("Orders:approve") });
    actions.push({ action: "reject", label: "Reject", perm: can("Orders:reject"), confirm: true });
  }
  if (["DRAFT", "PENDING_APPROVAL", "APPROVED", "IN_PROCESS", "READY_FOR_DISPATCH"].includes(o.status))
    actions.push({ action: "cancel", label: "Cancel", perm: can("Orders:edit"), confirm: true });
  if (o.status === "APPROVED") actions.push({ action: "in-process", label: "Mark In Process", perm: can("Orders:edit") || can("Dispatch:edit") });
  if (o.status === "IN_PROCESS") actions.push({ action: "ready-for-dispatch", label: "Ready for Dispatch", perm: can("Orders:edit") || can("Dispatch:edit") });
  if (o.status === "READY_FOR_DISPATCH") actions.push({ action: "dispatched", label: "Mark Dispatched", perm: can("Orders:edit") || can("Dispatch:edit") });
  if (o.status === "DISPATCHED") actions.push({ action: "completed", label: "Mark Completed", perm: can("Orders:edit") || can("Dispatch:edit") });

  return (
    <Modal open onClose={onClose} title={`Order ${o.order_no}`}
      footer={
        <div className="flex flex-wrap justify-end gap-2">
          {actions.filter((a) => a.perm).map((a) => (
            <Button key={a.action} variant={a.action === "reject" || a.action === "cancel" ? "danger" : "accent"}
              disabled={busy}
              onClick={() => a.confirm ? setConfirm(a) : act(a.action)}>{a.label}</Button>
          ))}
          <Button variant="ghost" onClick={onClose}>Close</Button>
        </div>
      }>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2 text-sm">
          <Badge tone={orderTone(o.status)}>{o.status.replace(/_/g, " ")}</Badge>
          <Badge tone={o.stock_committed ? "success" : "neutral"}>{o.stock_committed ? "stock committed" : "not committed"}</Badge>
          {o.dealer_name && <span className="text-muted">Dealer: {o.dealer_name}</span>}
          <span className="text-muted">Total: ₹{o.total_amount.toLocaleString()}</span>
        </div>
        {o.items.map((it) => (
          <div key={it.id} className="rounded-xl border border-line p-3">
            <div className="mb-2 text-sm font-semibold text-ink">
              {it.product_snapshot?.product_code} · {it.product_snapshot?.name} - {it.qty} {it.unit}
            </div>
            <table className="w-full text-xs">
              <thead className="text-left uppercase text-muted">
                <tr><th className="py-1">WH</th><th>Roll</th><th>Type</th><th className="text-right">Alloc</th><th className="text-right">Wastage</th></tr>
              </thead>
              <tbody>
                {it.allocations.map((a) => (
                  <tr key={a.id} className="border-t border-line">
                    <td className="py-1 text-muted">{a.warehouse_id}</td>
                    <td>{a.roll_no || "-"}</td>
                    <td>{a.is_full_roll ? "full" : "cut"}</td>
                    <td className="text-right font-medium text-ink">{a.alloc_qty}</td>
                    <td className="text-right text-muted">{a.wastage_qty}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
        {o.remarks && <p className="text-sm text-muted">Remarks: {o.remarks}</p>}
      </div>
      {confirm && (
        <ConfirmModal open onClose={() => setConfirm(null)} onConfirm={() => act(confirm.action)}
          danger title={`${confirm.label} order ${o.order_no}?`}
          message={confirm.action === "cancel"
            ? "Committed stock (if any) will be released back to saleable."
            : "This will reject the order."} />
      )}
    </Modal>
  );
}
