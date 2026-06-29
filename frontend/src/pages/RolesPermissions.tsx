import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Badge, TableSkeleton, EmptyState } from "@/components/ui";
import type { Role, Permission } from "@/types";
import { ShieldCheck } from "@phosphor-icons/react";

export default function RolesPermissions() {
  const { can } = useAuth();
  const { push } = useToast();
  const [roles, setRoles] = useState<Role[]>([]);
  const [perms, setPerms] = useState<Permission[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const [draft, setDraft] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const canManage = can("Roles & Permissions:manage_permissions");

  const load = async () => {
    setLoading(true);
    try {
      const [r, p] = await Promise.all([api.get("/roles"), api.get("/permissions")]);
      setRoles(r); setPerms(p);
      if (r.length && active === null) selectRole(r[0]);
    } catch (e: any) { push(e.message, "error"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const selectRole = (role: Role) => {
    setActive(role.id);
    setDraft(new Set(role.permission_codes));
  };

  const grouped = useMemo(() => {
    const map: Record<string, Permission[]> = {};
    for (const p of perms) (map[p.module] ||= []).push(p);
    return map;
  }, [perms]);

  const activeRole = roles.find((r) => r.id === active);
  const isOwner = activeRole?.name === "Owner";

  const toggle = (code: string) => {
    if (!canManage || isOwner) return;
    setDraft((d) => {
      const n = new Set(d);
      n.has(code) ? n.delete(code) : n.add(code);
      return n;
    });
  };

  const save = async () => {
    if (!activeRole) return;
    setSaving(true);
    try {
      await api.put(`/roles/${activeRole.id}/permissions`, {
        permission_codes: Array.from(draft),
      });
      push("Permissions updated", "success");
      await load();
    } catch (e: any) { push(e.message, "error"); }
    finally { setSaving(false); }
  };

  const createRole = async () => {
    const name = window.prompt("New role name");
    if (!name) return;
    try {
      const r = await api.post("/roles", { name });
      push("Role created", "success");
      await load();
      selectRole(r);
    } catch (e: any) { push(e.message, "error"); }
  };

  const deleteRole = async () => {
    if (!activeRole) return;
    if (!window.confirm(`Delete role "${activeRole.name}"? This cannot be undone.`)) return;
    try {
      await api.del(`/roles/${activeRole.id}`);
      push("Role deleted", "success");
      setActive(null);
      await load();
    } catch (e: any) { push(e.message, "error"); }
  };

  if (loading) return <Card><TableSkeleton rows={8} /></Card>;

  return (
    <div>
      <PageHeader icon={ShieldCheck} title="Roles & Permissions"
        subtitle="Enable or disable permissions per role and module"
        actions={can("Roles & Permissions:create") && <Button onClick={createRole}>+ New Role</Button>} />

      <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
        {/* Roles list */}
        <Card className="h-fit p-2">
          {roles.map((r) => (
            <button key={r.id} onClick={() => selectRole(r)}
              className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-sm transition ${
                active === r.id ? "bg-accent/20 font-semibold text-ink" : "text-muted hover:bg-surface-2"
              }`}>
              <span>{r.name}</span>
              {r.is_system && <Badge tone="neutral">system</Badge>}
            </button>
          ))}
        </Card>

        {/* Matrix */}
        <Card className="p-0">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <div>
              <h3 className="text-base font-bold text-ink">{activeRole?.name}</h3>
              <p className="text-xs text-muted">
                {isOwner ? "Owner always has every permission" : `${draft.size} permissions enabled`}
              </p>
            </div>
            <div className="flex gap-2">
              {can("Roles & Permissions:delete") && activeRole && !activeRole.is_system && (
                <Button variant="ghost" className="text-danger" onClick={deleteRole}>Delete</Button>
              )}
              {canManage && !isOwner && (
                <Button onClick={save} disabled={saving}>{saving ? "Saving…" : "Save changes"}</Button>
              )}
            </div>
          </div>

          {isOwner ? (
            <EmptyState icon={<ShieldCheck size={22} weight="duotone" />} title="Full access"
              hint="The Owner role implicitly holds all permissions and cannot be restricted." />
          ) : (
            <div className="max-h-[65vh] overflow-y-auto p-4">
              {Object.entries(grouped).map(([mod, list]) => (
                <div key={mod} className="mb-5">
                  <h4 className="mb-2 text-sm font-bold text-ink">{mod}</h4>
                  <div className="flex flex-wrap gap-2">
                    {list.map((p) => {
                      const on = draft.has(p.code);
                      return (
                        <button key={p.code} onClick={() => toggle(p.code)}
                          disabled={!canManage}
                          className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                            on
                              ? "border-accent bg-accent/15 text-accent"
                              : "border-line bg-surface text-muted hover:border-muted"
                          } ${!canManage ? "cursor-default opacity-80" : ""}`}>
                          {p.action}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
