import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Badge, Modal, TableSkeleton, EmptyState } from "@/components/ui";
import type { Dealer, Paginated } from "@/types";
import { Handshake } from "@phosphor-icons/react";

const empty = {
  firm_name: "", owner_name: "", concern_person: "", contact: "", alt_contact: "",
  address: "", gst_no: "", category: "", credit_period_days: 0, rating: "",
  price_list_access: false, offer_letter_access: false,
};

export default function Dealers() {
  const { can } = useAuth();
  const { push } = useToast();
  const [data, setData] = useState<Paginated<Dealer> | null>(null);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Dealer | null>(null);
  const [form, setForm] = useState<any>(empty);
  const [dash, setDash] = useState<any>(null);

  const load = async (search = q) => {
    setLoading(true);
    try { setData(await api.get(`/dealers?q=${encodeURIComponent(search)}`)); }
    catch (e: any) { push(e.message, "error"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(""); /* eslint-disable-next-line */ }, []);

  const openCreate = () => { setEditing(null); setForm(empty); setOpen(true); };
  const openEdit = (d: Dealer) => { setEditing(d); setForm({ ...d, rating: d.rating ?? "" }); setOpen(true); };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const payload = { ...form, rating: form.rating === "" ? null : Number(form.rating),
      credit_period_days: Number(form.credit_period_days) || 0 };
    try {
      if (editing) { await api.put(`/dealers/${editing.id}`, payload); push("Dealer updated", "success"); }
      else { await api.post("/dealers", payload); push("Dealer created", "success"); }
      setOpen(false); load();
    } catch (err: any) { push(err.message, "error"); }
  };

  const viewDash = async (d: Dealer) => {
    try { setDash(await api.get(`/dealers/${d.id}/dashboard`)); }
    catch (e: any) { push(e.message, "error"); }
  };

  const set = (k: string) => (e: any) =>
    setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  return (
    <div>
      <PageHeader icon={Handshake} title="Dealers / Vendors" subtitle="Manage dealer accounts and assignments"
        actions={can("Dealers:create") && <Button onClick={openCreate}>+ New Dealer</Button>} />

      <Card className="mb-4 p-3">
        <form onSubmit={(e) => { e.preventDefault(); load(); }} className="flex gap-2">
          <input className="input" placeholder="Search firm or owner…" value={q} onChange={(e) => setQ(e.target.value)} />
          <Button variant="outline" type="submit">Search</Button>
        </form>
      </Card>

      <Card className="overflow-hidden">
        {loading ? <TableSkeleton /> : !data?.items.length ? (
          <EmptyState icon={<Handshake size={22} weight="duotone" />} title="No dealers" hint="Add a dealer to get started." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Firm</th><th className="px-4 py-3">Owner</th>
                  <th className="px-4 py-3">Salesman</th><th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3 text-right">Credit</th><th className="px-4 py-3">Rating</th>
                  <th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((d) => (
                  <tr key={d.id} className="border-t border-line">
                    <td className="px-4 py-3 font-semibold text-ink">{d.firm_name}</td>
                    <td className="px-4 py-3 text-muted">{d.owner_name || "-"}</td>
                    <td className="px-4 py-3 text-muted">{d.salesman_name || "-"}</td>
                    <td className="px-4 py-3">{d.category ? <Badge tone="neutral">{d.category}</Badge> : "-"}</td>
                    <td className="px-4 py-3 text-right text-muted">{d.credit_period_days}d</td>
                    <td className="px-4 py-3">{d.rating ?? "-"}</td>
                    <td className="px-4 py-3"><Badge tone={d.status === "active" ? "success" : "neutral"}>{d.status}</Badge></td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" className="!py-1" onClick={() => viewDash(d)}>Dashboard</Button>
                        {can("Dealers:edit") && <Button variant="ghost" className="!py-1" onClick={() => openEdit(d)}>Edit</Button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title={editing ? "Edit Dealer" : "New Dealer"}
        footer={<><Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={submit as any}>{editing ? "Save" : "Create"}</Button></>}>
        <form onSubmit={submit} className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><label className="label">Firm name</label>
            <input className="input" value={form.firm_name} onChange={set("firm_name")} required /></div>
          <div><label className="label">Owner name</label><input className="input" value={form.owner_name || ""} onChange={set("owner_name")} /></div>
          <div><label className="label">Concern person</label><input className="input" value={form.concern_person || ""} onChange={set("concern_person")} /></div>
          <div><label className="label">Contact</label><input className="input" value={form.contact || ""} onChange={set("contact")} /></div>
          <div><label className="label">Alt contact</label><input className="input" value={form.alt_contact || ""} onChange={set("alt_contact")} /></div>
          <div><label className="label">GST no.</label><input className="input" value={form.gst_no || ""} onChange={set("gst_no")} /></div>
          <div><label className="label">Category</label><input className="input" value={form.category || ""} onChange={set("category")} /></div>
          <div><label className="label">Credit period (days)</label><input className="input" type="number" value={form.credit_period_days} onChange={set("credit_period_days")} /></div>
          <div><label className="label">Rating</label><input className="input" type="number" step="0.1" value={form.rating} onChange={set("rating")} /></div>
          <div className="col-span-2"><label className="label">Address</label><textarea className="input" rows={2} value={form.address || ""} onChange={set("address")} /></div>
          <label className="flex items-center gap-2 text-sm text-ink"><input type="checkbox" checked={form.price_list_access} onChange={set("price_list_access")} /> Price list access</label>
          <label className="flex items-center gap-2 text-sm text-ink"><input type="checkbox" checked={form.offer_letter_access} onChange={set("offer_letter_access")} /> Offer letter access</label>
        </form>
      </Modal>

      {dash && (
        <Modal open onClose={() => setDash(null)} title={`Dashboard · ${dash.dealer.firm_name}`}>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {[
              ["Orders", dash.total_orders], ["Order amount", `₹${dash.order_amount.toLocaleString()}`],
              ["Pending", dash.pending_approvals], ["Blocked", dash.blocked_material],
              ["Outstanding", `₹${dash.outstanding.toLocaleString()}`], ["Rating", dash.rating ?? "-"],
            ].map(([k, v]) => (
              <div key={k as string} className="rounded-xl border border-line p-3">
                <div className="text-xs uppercase text-muted">{k}</div>
                <div className="text-lg font-bold text-ink">{v}</div>
              </div>
            ))}
          </div>
          <h4 className="mb-2 mt-4 text-sm font-bold text-ink">Payment history</h4>
          {dash.payment_history.length === 0 ? <p className="text-sm text-muted">No payments recorded.</p> : (
            <table className="w-full text-xs">
              <thead className="text-left uppercase text-muted"><tr><th className="py-1">Type</th><th className="text-right">Amount</th><th>Remarks</th></tr></thead>
              <tbody>
                {dash.payment_history.map((p: any) => (
                  <tr key={p.id} className="border-t border-line">
                    <td className="py-1"><Badge tone={p.type === "PAYMENT" ? "success" : "warning"}>{p.type}</Badge></td>
                    <td className="py-1 text-right text-ink">₹{p.amount.toLocaleString()}</td>
                    <td className="py-1 text-muted">{p.remarks || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Modal>
      )}
    </div>
  );
}
