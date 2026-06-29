import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Badge, Modal, TableSkeleton, EmptyState } from "@/components/ui";
import { ImportModal } from "@/components/ImportModal";
import type { Product, Paginated, Category } from "@/types";
import { Tag } from "@phosphor-icons/react";

const TYPES = ["ROLL", "BOX", "LOOSE", "BATCH"];
const UNITS = ["SQM", "SQFT", "MTR", "BOX", "PCS"];
const STATUS = ["CONTINUED", "DISCONTINUED"];

const empty = {
  pattern_no: "", product_code: "", name: "", collection_name: "", brand: "",
  category_id: "", product_type: "ROLL", unit: "SQM", unit_size: "", thickness: "",
  roll_size: "", standard_roll_qty: "", price: 0, status: "CONTINUED", remarks: "",
};

export default function Products() {
  const { can } = useAuth();
  const { push } = useToast();
  const [data, setData] = useState<Paginated<Product> | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState<any>(empty);
  const [showImport, setShowImport] = useState(false);
  const canPrice = can("Products:view_price");

  const loadCategories = () => api.get("/products/categories").then(setCategories).catch(() => {});
  const addCategory = async () => {
    const name = window.prompt("New category name");
    if (!name) return;
    try {
      const c = await api.post("/products/categories", { name });
      await loadCategories();
      setForm((f: any) => ({ ...f, category_id: c.id }));
      push("Category added", "success");
    } catch (e: any) { push(e.message, "error"); }
  };

  const load = async (search = q) => {
    setLoading(true);
    try { setData(await api.get(`/products?q=${encodeURIComponent(search)}`)); }
    catch (e: any) { push(e.message, "error"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(""); loadCategories(); /* eslint-disable-next-line */ }, []);

  const openCreate = () => { setEditing(null); setForm(empty); setOpen(true); };
  const openEdit = (p: Product) => {
    setEditing(p);
    setForm({ ...p, standard_roll_qty: p.standard_roll_qty ?? "", category_id: p.category_id ?? "" });
    setOpen(true);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const payload: any = {
      ...form,
      price: Number(form.price) || 0,
      category_id: form.category_id === "" ? null : Number(form.category_id),
      standard_roll_qty: form.standard_roll_qty === "" ? null : Number(form.standard_roll_qty),
    };
    try {
      if (editing) {
        delete payload.product_code; // immutable
        await api.put(`/products/${editing.id}`, payload);
        push("Product updated", "success");
      } else {
        await api.post("/products", payload);
        push("Product created", "success");
      }
      setOpen(false); load();
    } catch (err: any) { push(err.message, "error"); }
  };

  const set = (k: string) => (e: any) => setForm({ ...form, [k]: e.target.value });

  return (
    <div>
      <PageHeader icon={Tag} title="Product Master" subtitle="Pattern numbers, design codes & specifications"
        actions={can("Products:create") && <>
          <Button variant="outline" onClick={() => setShowImport(true)}>Import CSV</Button>
          <Button onClick={openCreate}>+ New Product</Button>
        </>} />

      <Card className="mb-4 p-3">
        <form onSubmit={(e) => { e.preventDefault(); load(); }} className="flex gap-2">
          <input className="input" placeholder="Search pattern, code, name, collection, brand…"
            value={q} onChange={(e) => setQ(e.target.value)} />
          <Button variant="outline" type="submit">Search</Button>
        </form>
      </Card>

      <Card className="overflow-hidden">
        {loading ? <TableSkeleton /> : !data?.items.length ? (
          <EmptyState icon={<Tag size={22} weight="duotone" />} title="No products found" hint="Add a product or adjust your search." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Pattern</th>
                  <th className="px-4 py-3">Code</th>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Collection</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Unit</th>
                  {canPrice && <th className="px-4 py-3 text-right">Price</th>}
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.id} className="border-t border-line">
                    <td className="px-4 py-3 font-semibold text-ink">{p.pattern_no}</td>
                    <td className="px-4 py-3 text-muted">{p.product_code}</td>
                    <td className="px-4 py-3 text-ink">{p.name}</td>
                    <td className="px-4 py-3 text-muted">{p.collection_name || "-"}</td>
                    <td className="px-4 py-3"><Badge tone="neutral">{p.product_type}</Badge></td>
                    <td className="px-4 py-3 text-muted">{p.unit}</td>
                    {canPrice && <td className="px-4 py-3 text-right text-ink">₹{p.price.toLocaleString()}</td>}
                    <td className="px-4 py-3">
                      <Badge tone={p.status === "CONTINUED" ? "success" : "warning"}>{p.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {can("Products:edit") && <Button variant="ghost" className="!py-1" onClick={() => openEdit(p)}>Edit</Button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)}
        title={editing ? "Edit Product" : "New Product"}
        footer={<>
          <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={submit as any}>{editing ? "Save" : "Create"}</Button>
        </>}>
        <form onSubmit={submit} className="grid grid-cols-2 gap-3">
          <div><label className="label">Pattern No.</label>
            <input className="input" value={form.pattern_no} onChange={set("pattern_no")} required /></div>
          <div><label className="label">Design / Product Code</label>
            <input className="input" value={form.product_code} onChange={set("product_code")} required disabled={!!editing} /></div>
          <div className="col-span-2"><label className="label">Name</label>
            <input className="input" value={form.name} onChange={set("name")} required /></div>
          <div><label className="label">Collection</label>
            <input className="input" value={form.collection_name || ""} onChange={set("collection_name")} /></div>
          <div><label className="label">Brand</label>
            <input className="input" value={form.brand || ""} onChange={set("brand")} /></div>
          <div className="col-span-2">
            <div className="flex items-center justify-between">
              <label className="label">Category</label>
              <button type="button" onClick={addCategory} className="mb-1.5 text-xs font-medium text-accent hover:underline">+ Add category</button>
            </div>
            <select className="input" value={form.category_id || ""} onChange={set("category_id")}>
              <option value="">- none -</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div><label className="label">Type</label>
            <select className="input" value={form.product_type} onChange={set("product_type")}>
              {TYPES.map((t) => <option key={t}>{t}</option>)}</select></div>
          <div><label className="label">Unit</label>
            <select className="input" value={form.unit} onChange={set("unit")}>
              {UNITS.map((u) => <option key={u}>{u}</option>)}</select></div>
          <div><label className="label">Unit size</label>
            <input className="input" value={form.unit_size || ""} onChange={set("unit_size")} /></div>
          <div><label className="label">Thickness</label>
            <input className="input" value={form.thickness || ""} onChange={set("thickness")} /></div>
          <div><label className="label">Roll size</label>
            <input className="input" value={form.roll_size || ""} onChange={set("roll_size")} /></div>
          <div><label className="label">Standard roll qty</label>
            <input className="input" type="number" value={form.standard_roll_qty} onChange={set("standard_roll_qty")} /></div>
          <div><label className="label">Price</label>
            <input className="input" type="number" value={form.price} onChange={set("price")} /></div>
          <div><label className="label">Status</label>
            <select className="input" value={form.status} onChange={set("status")}>
              {STATUS.map((s) => <option key={s}>{s}</option>)}</select></div>
          <div className="col-span-2"><label className="label">Remarks</label>
            <input className="input" value={form.remarks || ""} onChange={set("remarks")} /></div>
        </form>
      </Modal>

      {showImport && (
        <ImportModal title="Import products" templatePath="/products/import-template"
          importPath="/products/import" onClose={() => setShowImport(false)}
          onDone={() => load()} />
      )}
    </div>
  );
}
