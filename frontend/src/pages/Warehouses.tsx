import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Badge, Modal, TableSkeleton, EmptyState } from "@/components/ui";
import type { Warehouse } from "@/types";
import { Warehouse as WarehouseIcon } from "@phosphor-icons/react";

export default function Warehouses() {
  const { can } = useAuth();
  const { push } = useToast();
  const [items, setItems] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Warehouse | null>(null);
  const [form, setForm] = useState<any>({});

  const load = async () => {
    setLoading(true);
    try { setItems(await api.get("/warehouses")); }
    catch (e: any) { push(e.message, "error"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const openCreate = () => { setEditing(null); setForm({ name: "", code: "", location: "", address: "" }); setOpen(true); };
  const openEdit = (w: Warehouse) => { setEditing(w); setForm({ ...w }); setOpen(true); };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      if (editing) { await api.put(`/warehouses/${editing.id}`, form); push("Warehouse updated", "success"); }
      else { await api.post("/warehouses", form); push("Warehouse created", "success"); }
      setOpen(false); load();
    } catch (err: any) { push(err.message, "error"); }
  };

  const disable = async (w: Warehouse) => {
    try { await api.del(`/warehouses/${w.id}`); push("Warehouse disabled", "success"); load(); }
    catch (err: any) { push(err.message, "error"); }
  };

  return (
    <div>
      <PageHeader icon={WarehouseIcon} title="Warehouses" subtitle="Dynamically manage stock locations"
        actions={can("Warehouses:create") && <Button onClick={openCreate}>+ New Warehouse</Button>} />

      {loading ? <Card><TableSkeleton /></Card> : !items.length ? (
        <Card><EmptyState icon={<WarehouseIcon size={22} weight="duotone" />} title="No warehouses yet" hint="Add your first warehouse to start tracking stock." /></Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((w) => (
            <Card key={w.id} className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-base font-bold text-ink">{w.name}</h3>
                  <p className="text-xs text-muted">{w.code}</p>
                </div>
                <Badge tone={w.status === "active" ? "success" : "neutral"}>{w.status}</Badge>
              </div>
              <p className="mt-3 text-sm text-muted">{w.location || "-"}</p>
              <p className="text-xs text-muted">{w.address || ""}</p>
              <div className="mt-4 flex gap-2">
                {can("Warehouses:edit") && <Button variant="outline" className="!py-1.5" onClick={() => openEdit(w)}>Edit</Button>}
                {can("Warehouses:delete") && w.status === "active" &&
                  <Button variant="ghost" className="!py-1.5 text-danger" onClick={() => disable(w)}>Disable</Button>}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)}
        title={editing ? "Edit Warehouse" : "New Warehouse"}
        footer={<>
          <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={submit as any}>{editing ? "Save" : "Create"}</Button>
        </>}>
        <form onSubmit={submit} className="space-y-3">
          <div><label className="label">Name</label>
            <input className="input" value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></div>
          {!editing && <div><label className="label">Code</label>
            <input className="input" value={form.code || ""} onChange={(e) => setForm({ ...form, code: e.target.value })} required /></div>}
          <div><label className="label">Location</label>
            <input className="input" value={form.location || ""} onChange={(e) => setForm({ ...form, location: e.target.value })} /></div>
          <div><label className="label">Address</label>
            <textarea className="input" rows={2} value={form.address || ""} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
          {editing && <div><label className="label">Status</label>
            <select className="input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="active">active</option><option value="inactive">inactive</option>
            </select></div>}
        </form>
      </Modal>
    </div>
  );
}
