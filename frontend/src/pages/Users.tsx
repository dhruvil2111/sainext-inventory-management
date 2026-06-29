import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Badge, Modal, TableSkeleton, EmptyState } from "@/components/ui";
import { UserPermissionsModal } from "@/components/UserPermissionsModal";
import type { User, Role, Warehouse, Paginated } from "@/types";
import { UsersThree } from "@phosphor-icons/react";

export default function Users() {
  const { can } = useAuth();
  const { push } = useToast();
  const [data, setData] = useState<Paginated<User> | null>(null);
  const [roles, setRoles] = useState<Role[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [form, setForm] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [permsUser, setPermsUser] = useState<User | null>(null);
  const canManagePerms = can("Roles & Permissions:manage_permissions");
  const salesmen = data?.items.filter((u) =>
    roles.find((r) => r.id === u.role_id)?.name === "Salesman") || [];

  const load = async (search = q) => {
    setLoading(true);
    try {
      const d = await api.get(`/users?q=${encodeURIComponent(search)}`);
      setData(d);
    } catch (e: any) { push(e.message, "error"); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    load("");
    api.get("/roles").then(setRoles).catch(() => {});
    api.get("/warehouses").then(setWarehouses).catch(() => {});
    // eslint-disable-next-line
  }, []);

  const roleName = (id: number) => roles.find((r) => r.id === id)?.name || id;

  const openCreate = () => {
    setEditing(null);
    setForm({ name: "", email: "", mobile: "", role_id: roles[0]?.id, password: "" });
    setOpen(true);
  };
  const openEdit = (u: User) => {
    setEditing(u);
    setForm({ name: u.name, mobile: u.mobile || "", role_id: u.role_id, status: u.status, password: "" });
    setOpen(true);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      if (editing) {
        await api.put(`/users/${editing.id}`, form);
        push("User updated", "success");
      } else {
        await api.post("/users", form);
        push("User created", "success");
      }
      setOpen(false);
      load();
    } catch (err: any) { push(err.message, "error"); }
  };

  const disable = async (u: User) => {
    try { await api.del(`/users/${u.id}`); push("User disabled", "success"); load(); }
    catch (err: any) { push(err.message, "error"); }
  };

  return (
    <div>
      <PageHeader icon={UsersThree} title="Users" subtitle="Manage system users and their roles"
        actions={can("Users:create") && <Button onClick={openCreate}>+ New User</Button>} />

      <Card className="mb-4 p-3">
        <form onSubmit={(e) => { e.preventDefault(); load(); }} className="flex gap-2">
          <input className="input" placeholder="Search by name or email…"
            value={q} onChange={(e) => setQ(e.target.value)} />
          <Button variant="outline" type="submit">Search</Button>
        </form>
      </Card>

      <Card className="overflow-hidden">
        {loading ? <TableSkeleton /> : !data?.items.length ? (
          <EmptyState icon={<UsersThree size={22} weight="duotone" />} title="No users found" hint="Try a different search or add a new user." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((u) => (
                  <tr key={u.id} className="border-t border-line">
                    <td className="px-4 py-3 font-medium text-ink">{u.name}</td>
                    <td className="px-4 py-3 text-muted">{u.email}</td>
                    <td className="px-4 py-3">{roleName(u.role_id)}</td>
                    <td className="px-4 py-3">
                      <Badge tone={u.status === "active" ? "success" : "neutral"}>{u.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        {canManagePerms && <Button variant="ghost" className="!py-1" onClick={() => setPermsUser(u)}>Permissions</Button>}
                        {can("Users:edit") && <Button variant="ghost" className="!py-1" onClick={() => openEdit(u)}>Edit</Button>}
                        {can("Users:delete") && u.status === "active" &&
                          <Button variant="ghost" className="!py-1 text-danger" onClick={() => disable(u)}>Disable</Button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)}
        title={editing ? "Edit User" : "New User"}
        footer={<>
          <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={submit as any}>{editing ? "Save" : "Create"}</Button>
        </>}>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="label">Name</label>
            <input className="input" value={form.name || ""}
              onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          {!editing && (
            <div>
              <label className="label">Email</label>
              <input className="input" type="email" value={form.email || ""}
                onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            </div>
          )}
          <div>
            <label className="label">Mobile</label>
            <input className="input" value={form.mobile || ""}
              onChange={(e) => setForm({ ...form, mobile: e.target.value })} />
          </div>
          <div>
            <label className="label">Role</label>
            <select className="input" value={form.role_id || ""}
              onChange={(e) => setForm({ ...form, role_id: Number(e.target.value) })}>
              {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Assigned warehouse (optional)</label>
            <select className="input" value={form.assigned_warehouse_id || ""}
              onChange={(e) => setForm({ ...form, assigned_warehouse_id: e.target.value ? Number(e.target.value) : null })}>
              <option value="">- none -</option>
              {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Assigned salesman (optional)</label>
            <select className="input" value={form.assigned_salesman_id || ""}
              onChange={(e) => setForm({ ...form, assigned_salesman_id: e.target.value ? Number(e.target.value) : null })}>
              <option value="">- none -</option>
              {salesmen.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          {editing && (
            <div>
              <label className="label">Status</label>
              <select className="input" value={form.status || "active"}
                onChange={(e) => setForm({ ...form, status: e.target.value })}>
                <option value="active">active</option>
                <option value="inactive">inactive</option>
                <option value="suspended">suspended</option>
              </select>
            </div>
          )}
          <div>
            <label className="label">{editing ? "New password (leave blank to keep)" : "Password"}</label>
            <input className="input" type="password" value={form.password || ""}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required={!editing} />
          </div>
        </form>
      </Modal>

      {permsUser && <UserPermissionsModal user={permsUser} onClose={() => setPermsUser(null)} />}
    </div>
  );
}
