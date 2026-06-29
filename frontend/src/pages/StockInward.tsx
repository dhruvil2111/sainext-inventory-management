import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Badge, Modal, TableSkeleton, EmptyState } from "@/components/ui";
import { ProductPicker } from "@/components/ProductPicker";
import type { Product, Warehouse, StockItem, Paginated } from "@/types";
import { Package, TrayArrowDown } from "@phosphor-icons/react";

const ITEM_TYPES = ["ROLL", "BOX", "LOOSE"];

export default function StockInward() {
  const { can } = useAuth();
  const { push } = useToast();
  const [tab, setTab] = useState<"new" | "items">("new");
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const canEdit = can("Stock Inward:edit");

  useEffect(() => { api.get("/warehouses").then(setWarehouses).catch(() => {}); }, []);

  return (
    <div>
      <PageHeader icon={TrayArrowDown} title="Stock Inward" subtitle="Record purchases, inward entries, adjustments & transfers" />
      <div className="mb-4 flex gap-2">
        <button className={`btn ${tab === "new" ? "btn-accent" : "btn-outline"}`} onClick={() => setTab("new")}>New Entry</button>
        <button className={`btn ${tab === "items" ? "btn-accent" : "btn-outline"}`} onClick={() => setTab("items")}>Stock Items</button>
      </div>
      {tab === "new"
        ? <NewInward warehouses={warehouses} onDone={() => setTab("items")} push={push} />
        : <StockItems warehouses={warehouses} canEdit={canEdit} push={push} />}
    </div>
  );
}

function NewInward({ warehouses, onDone, push }: any) {
  const blank = {
    entry_kind: "INWARD", item_type: "ROLL", quantity: "", unit: "SQM",
    warehouse_id: "", batch_no: "", batch_date: "", roll_no: "", roll_date: "",
    box_count: "", purchase_date: "", inward_date: "", remarks: "",
  };
  const [product, setProduct] = useState<Product | null>(null);
  const [form, setForm] = useState<any>(blank);
  const set = (k: string) => (e: any) => setForm({ ...form, [k]: e.target.value });

  useEffect(() => { if (product) setForm((f: any) => ({ ...f, unit: product.unit })); }, [product]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!product) return push("Select a product", "error");
    if (!form.warehouse_id) return push("Select a warehouse", "error");
    const payload: any = {
      product_id: product.id, warehouse_id: Number(form.warehouse_id),
      quantity: Number(form.quantity), unit: form.unit, item_type: form.item_type,
      entry_kind: form.entry_kind, remarks: form.remarks || null,
      batch_no: form.batch_no || null, batch_date: form.batch_date || null,
      roll_no: form.roll_no || null, roll_date: form.roll_date || null,
      box_count: form.box_count ? Number(form.box_count) : null,
      purchase_date: form.purchase_date || null, inward_date: form.inward_date || null,
    };
    try {
      await api.post("/stock/inward", payload);
      push("Stock inward recorded - ledger updated", "success");
      setForm(blank); setProduct(null); onDone();
    } catch (err: any) { push(err.message, "error"); }
  };

  return (
    <Card className="p-5">
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        <div className="md:col-span-2"><label className="label">Product</label>
          <ProductPicker value={product} onChange={setProduct} /></div>
        <div><label className="label">Entry type</label>
          <select className="input" value={form.entry_kind} onChange={set("entry_kind")}>
            <option value="INWARD">Purchase / Inward</option>
            <option value="RETURN_IN">Return In</option></select></div>
        <div><label className="label">Material type</label>
          <select className="input" value={form.item_type} onChange={set("item_type")}>
            {ITEM_TYPES.map((t) => <option key={t}>{t}</option>)}</select></div>
        <div><label className="label">Warehouse</label>
          <select className="input" value={form.warehouse_id} onChange={set("warehouse_id")} required>
            <option value="">- select -</option>
            {warehouses.map((w: Warehouse) => <option key={w.id} value={w.id}>{w.name}</option>)}</select></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Quantity</label>
            <input className="input" type="number" step="any" value={form.quantity} onChange={set("quantity")} required /></div>
          <div><label className="label">Unit</label>
            <input className="input" value={form.unit} onChange={set("unit")} /></div>
        </div>
        <div><label className="label">Batch no.</label>
          <input className="input" value={form.batch_no} onChange={set("batch_no")} /></div>
        <div><label className="label">Batch date</label>
          <input className="input" type="date" value={form.batch_date} onChange={set("batch_date")} /></div>
        <div><label className="label">Roll no.</label>
          <input className="input" value={form.roll_no} onChange={set("roll_no")} /></div>
        <div><label className="label">Roll date</label>
          <input className="input" type="date" value={form.roll_date} onChange={set("roll_date")} /></div>
        <div><label className="label">Box count</label>
          <input className="input" type="number" value={form.box_count} onChange={set("box_count")} /></div>
        <div><label className="label">Purchase date</label>
          <input className="input" type="date" value={form.purchase_date} onChange={set("purchase_date")} /></div>
        <div><label className="label">Inward date</label>
          <input className="input" type="date" value={form.inward_date} onChange={set("inward_date")} /></div>
        <div className="md:col-span-2"><label className="label">Remarks</label>
          <input className="input" value={form.remarks} onChange={set("remarks")} /></div>
        <div className="md:col-span-2">
          <Button type="submit" className="w-full md:w-auto">Record inward entry</Button>
        </div>
      </form>
    </Card>
  );
}

function StockItems({ warehouses, canEdit, push }: any) {
  const [data, setData] = useState<Paginated<StockItem> | null>(null);
  const [loading, setLoading] = useState(true);
  const [wh, setWh] = useState("");
  const [action, setAction] = useState<{ kind: string; item: StockItem } | null>(null);

  const load = async () => {
    setLoading(true);
    try { setData(await api.get(`/stock/items${wh ? `?warehouse_id=${wh}` : ""}`)); }
    catch (e: any) { push(e.message, "error"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [wh]);

  return (
    <>
      <Card className="mb-4 p-3">
        <select className="input max-w-xs" value={wh} onChange={(e) => setWh(e.target.value)}>
          <option value="">All warehouses</option>
          {warehouses.map((w: Warehouse) => <option key={w.id} value={w.id}>{w.name}</option>)}
        </select>
      </Card>
      <Card className="overflow-hidden">
        {loading ? <TableSkeleton /> : !data?.items.length ? (
          <EmptyState icon={<Package size={22} weight="duotone" />} title="No stock items" hint="Record an inward entry to create stock." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-xs uppercase text-muted">
                <tr>
                  <th className="px-3 py-3">Product</th><th className="px-3 py-3">WH</th>
                  <th className="px-3 py-3">Batch</th><th className="px-3 py-3">Roll</th>
                  <th className="px-3 py-3">Type</th><th className="px-3 py-3 text-right">Original</th>
                  <th className="px-3 py-3 text-right">Available</th><th className="px-3 py-3">Inward</th>
                  {canEdit && <th className="px-3 py-3 text-right">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {data.items.map((s) => (
                  <tr key={s.id} className="border-t border-line">
                    <td className="px-3 py-3"><b className="text-ink">{s.product_code}</b><div className="text-xs text-muted">{s.product_name}</div></td>
                    <td className="px-3 py-3 text-muted">{s.warehouse_name}</td>
                    <td className="px-3 py-3">{s.batch_no || "-"}</td>
                    <td className="px-3 py-3">{s.roll_no || "-"}</td>
                    <td className="px-3 py-3"><Badge tone="neutral">{s.item_type}</Badge></td>
                    <td className="px-3 py-3 text-right text-muted">{s.original_qty}</td>
                    <td className="px-3 py-3 text-right font-semibold text-ink">{s.available_qty} {s.unit}</td>
                    <td className="px-3 py-3 text-muted">{s.inward_date || "-"}</td>
                    {canEdit && (
                      <td className="px-3 py-3 text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" className="!py-1 !px-2" onClick={() => setAction({ kind: "adjust", item: s })}>Adjust</Button>
                          <Button variant="ghost" className="!py-1 !px-2" onClick={() => setAction({ kind: "transfer", item: s })}>Transfer</Button>
                          <Button variant="ghost" className="!py-1 !px-2 text-danger" onClick={() => setAction({ kind: "damage", item: s })}>Damage</Button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {action && (
        <ActionModal action={action} warehouses={warehouses}
          onClose={() => setAction(null)}
          onDone={() => { setAction(null); load(); }} push={push} />
      )}
    </>
  );
}

function ActionModal({ action, warehouses, onClose, onDone, push }: any) {
  const { kind, item } = action;
  const [val, setVal] = useState("");
  const [toWh, setToWh] = useState("");
  const [remarks, setRemarks] = useState("");

  const submit = async () => {
    try {
      if (kind === "adjust") {
        await api.post("/stock/adjustment", { stock_item_id: item.id, delta: Number(val), remarks });
        push("Adjustment posted to ledger", "success");
      } else if (kind === "damage") {
        await api.post("/stock/damage", { stock_item_id: item.id, quantity: Number(val), remarks });
        push("Damage recorded", "success");
      } else {
        await api.post("/stock/transfer", { stock_item_id: item.id, to_warehouse_id: Number(toWh), quantity: Number(val), remarks });
        push("Transfer completed", "success");
      }
      onDone();
    } catch (err: any) { push(err.message, "error"); }
  };

  const title = kind === "adjust" ? "Adjust stock" : kind === "transfer" ? "Transfer stock" : "Record damage";
  return (
    <Modal open onClose={onClose} title={title}
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button variant={kind === "damage" ? "danger" : "accent"} onClick={submit}>Confirm</Button></>}>
      <div className="space-y-3">
        <p className="text-sm text-muted">{item.product_code} · {item.warehouse_name} · available <b className="text-ink">{item.available_qty} {item.unit}</b></p>
        {kind === "transfer" && (
          <div><label className="label">Destination warehouse</label>
            <select className="input" value={toWh} onChange={(e) => setToWh(e.target.value)}>
              <option value="">- select -</option>
              {warehouses.filter((w: Warehouse) => w.id !== item.warehouse_id)
                .map((w: Warehouse) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select></div>
        )}
        <div>
          <label className="label">{kind === "adjust" ? "Delta (+ in / − out)" : "Quantity"}</label>
          <input className="input" type="number" step="any" value={val} onChange={(e) => setVal(e.target.value)} autoFocus />
        </div>
        <div><label className="label">Remarks</label>
          <input className="input" value={remarks} onChange={(e) => setRemarks(e.target.value)} /></div>
      </div>
    </Modal>
  );
}
