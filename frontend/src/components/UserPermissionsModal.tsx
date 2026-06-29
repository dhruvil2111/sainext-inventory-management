import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { Modal, Button, Spinner, Badge } from "@/components/ui";
import type { Permission, UserPermissions, User } from "@/types";

type State = "inherit" | "allow" | "deny";

export function UserPermissionsModal({ user, onClose }: { user: User; onClose: () => void }) {
  const { push } = useToast();
  const [perms, setPerms] = useState<Permission[]>([]);
  const [data, setData] = useState<UserPermissions | null>(null);
  const [state, setState] = useState<Record<string, State>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [p, up] = await Promise.all([
          api.get("/permissions"),
          api.get(`/users/${user.id}/permissions`),
        ]);
        setPerms(p); setData(up);
        const s: Record<string, State> = {};
        up.override_allow.forEach((c: string) => (s[c] = "allow"));
        up.override_deny.forEach((c: string) => (s[c] = "deny"));
        setState(s);
      } catch (e: any) { push(e.message, "error"); }
      finally { setLoading(false); }
    })();
  }, [user.id]); // eslint-disable-line

  const grouped = useMemo(() => {
    const m: Record<string, Permission[]> = {};
    for (const p of perms) (m[p.module] ||= []).push(p);
    return m;
  }, [perms]);

  const roleHas = (code: string) => data?.role_codes.includes(code);
  const cur = (code: string): State => state[code] || "inherit";
  const cycle = (code: string) =>
    setState((s) => {
      const order: State[] = ["inherit", "allow", "deny"];
      const next = order[(order.indexOf(cur(code)) + 1) % 3];
      const n = { ...s };
      if (next === "inherit") delete n[code]; else n[code] = next;
      return n;
    });

  const save = async () => {
    setSaving(true);
    const allow = Object.entries(state).filter(([, v]) => v === "allow").map(([c]) => c);
    const deny = Object.entries(state).filter(([, v]) => v === "deny").map(([c]) => c);
    try {
      await api.put(`/users/${user.id}/overrides`, { allow, deny });
      push("Permission overrides saved", "success");
      onClose();
    } catch (e: any) { push(e.message, "error"); }
    finally { setSaving(false); }
  };

  return (
    <Modal open onClose={onClose} title={`Permissions · ${user.name}`}
      footer={<>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving}>{saving ? <Spinner /> : "Save overrides"}</Button>
      </>}>
      {loading || !data ? (
        <div className="flex justify-center py-10 text-accent"><Spinner className="h-6 w-6" /></div>
      ) : (
        <div className="max-h-[60vh] space-y-4 overflow-y-auto pr-1">
          <p className="text-xs text-muted">
            Each permission inherits from the role by default. Click a chip to cycle
            <b className="text-ink"> Inherit → Allow → Deny</b>. Allow force-grants;
            Deny force-removes - overriding the role.
          </p>
          {Object.entries(grouped).map(([mod, list]) => (
            <div key={mod}>
              <h4 className="mb-2 text-sm font-bold text-ink">{mod}</h4>
              <div className="flex flex-wrap gap-2">
                {list.map((p) => {
                  const st = cur(p.code);
                  const effective = st === "allow" || (st === "inherit" && roleHas(p.code));
                  const cls = st === "allow" ? "border-success bg-success/15 text-success"
                    : st === "deny" ? "border-danger bg-danger/15 text-danger"
                    : roleHas(p.code) ? "border-accent/50 bg-accent/10 text-ink"
                    : "border-line bg-surface text-muted";
                  return (
                    <button key={p.code} type="button" onClick={() => cycle(p.code)}
                      className={`rounded-lg border px-2.5 py-1.5 text-xs font-medium ${cls}`}
                      title={`role default: ${roleHas(p.code) ? "granted" : "not granted"} · now: ${effective ? "yes" : "no"}`}>
                      {st === "allow" ? "+ " : st === "deny" ? "− " : roleHas(p.code) ? "· " : ""}{p.action}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}
