import { useEffect, useState } from "react";
import { ClockCounterClockwise } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Badge, Modal, TableSkeleton, EmptyState } from "@/components/ui";

interface Row {
  id: number; user_name: string; module: string; action: string;
  record_type?: string | null; record_id?: number | null;
  old_value?: any; new_value?: any; created_at?: string | null;
}
interface Page { total: number; page: number; page_size: number; items: Row[]; }

export default function AuditLog() {
  const { push } = useToast();
  const [data, setData] = useState<Page | null>(null);
  const [meta, setMeta] = useState<{ modules: string[]; actions: string[] }>({ modules: [], actions: [] });
  const [module, setModule] = useState("");
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<Row | null>(null);

  useEffect(() => { api.get("/audit-logs/meta").then(setMeta).catch(() => {}); }, []);

  const load = async () => {
    setLoading(true);
    const qs = new URLSearchParams({ page: String(page), page_size: "30" });
    if (module) qs.set("module", module);
    if (action) qs.set("action", action);
    try { setData(await api.get(`/audit-logs?${qs}`)); }
    catch (e: any) { push(e.message, "error"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [module, action, page]);

  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div>
      <PageHeader icon={ClockCounterClockwise} title="Audit Log"
        subtitle="Every create, edit, approval and stock action, with who and when" />

      <Card className="mb-4 flex flex-wrap gap-3 p-3">
        <select className="input max-w-xs" value={module} onChange={(e) => { setPage(1); setModule(e.target.value); }}>
          <option value="">All modules</option>
          {meta.modules.map((m) => <option key={m}>{m}</option>)}
        </select>
        <select className="input max-w-xs" value={action} onChange={(e) => { setPage(1); setAction(e.target.value); }}>
          <option value="">All actions</option>
          {meta.actions.map((a) => <option key={a}>{a}</option>)}
        </select>
      </Card>

      <Card className="overflow-hidden">
        {loading ? <TableSkeleton /> : !data?.items.length ? (
          <EmptyState icon={<ClockCounterClockwise size={22} weight="duotone" />} title="No audit entries"
            hint="Actions across the system will be recorded here." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-2xs font-semibold uppercase tracking-wider text-muted">
                <tr>
                  <th className="px-4 py-2.5">When</th><th className="px-4 py-2.5">User</th>
                  <th className="px-4 py-2.5">Module</th><th className="px-4 py-2.5">Action</th>
                  <th className="px-4 py-2.5">Record</th><th className="px-4 py-2.5 text-right">Details</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((r) => (
                  <tr key={r.id} className="border-t border-line">
                    <td className="px-4 py-3 text-muted tabular">{r.created_at ? new Date(r.created_at).toLocaleString() : "-"}</td>
                    <td className="px-4 py-3 text-ink">{r.user_name}</td>
                    <td className="px-4 py-3 text-muted">{r.module}</td>
                    <td className="px-4 py-3"><Badge tone="accent">{r.action}</Badge></td>
                    <td className="px-4 py-3 text-muted">{r.record_type ? `${r.record_type} #${r.record_id ?? "-"}` : "-"}</td>
                    <td className="px-4 py-3 text-right">
                      {(r.old_value || r.new_value)
                        ? <Button variant="ghost" className="!py-1" onClick={() => setDetail(r)}>View</Button>
                        : <span className="text-muted">-</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && pages > 1 && (
          <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm">
            <span className="text-muted">{data.total} entries · page {page}/{pages}</span>
            <div className="flex gap-2">
              <button className="btn-outline !py-1" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
              <button className="btn-outline !py-1" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          </div>
        )}
      </Card>

      {detail && (
        <Modal open onClose={() => setDetail(null)} title={`${detail.module} · ${detail.action}`}>
          <div className="space-y-3 text-sm">
            <p className="text-muted">{detail.user_name} · {detail.created_at ? new Date(detail.created_at).toLocaleString() : ""}</p>
            {detail.old_value && (
              <div>
                <div className="label">Before</div>
                <pre className="overflow-x-auto rounded-sm bg-surface-2 p-3 text-xs text-ink">{JSON.stringify(detail.old_value, null, 2)}</pre>
              </div>
            )}
            {detail.new_value && (
              <div>
                <div className="label">After</div>
                <pre className="overflow-x-auto rounded-sm bg-surface-2 p-3 text-xs text-ink">{JSON.stringify(detail.new_value, null, 2)}</pre>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
