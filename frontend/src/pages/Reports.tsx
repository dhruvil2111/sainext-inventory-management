import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Spinner, TableSkeleton, EmptyState } from "@/components/ui";
import type { Warehouse } from "@/types";
import { ChartBar } from "@phosphor-icons/react";

const REPORTS = [
  { key: "stock", label: "Warehouse / batch stock" },
  { key: "ledger", label: "Stock ledger (in/out)" },
  { key: "orders", label: "Orders" },
  { key: "blocks", label: "Blocked material" },
  { key: "dispatch", label: "Dispatch" },
  { key: "payments", label: "Payments / dues" },
];

export default function Reports() {
  const { can } = useAuth();
  const { push } = useToast();
  const [report, setReport] = useState("stock");
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [filters, setFilters] = useState<any>({ date_from: "", date_to: "", warehouse_id: "", status: "" });
  const [data, setData] = useState<{ columns: string[]; rows: any[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const canExport = can("Reports:export");

  useEffect(() => { api.get("/warehouses").then(setWarehouses).catch(() => {}); }, []);

  const qs = () => {
    const p = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => { if (v) p.set(k, String(v)); });
    return p.toString();
  };

  const run = async () => {
    setLoading(true);
    try { setData(await api.get(`/reports/${report}?${qs()}`)); }
    catch (e: any) { push(e.message, "error"); setData(null); }
    finally { setLoading(false); }
  };
  useEffect(() => { run(); /* eslint-disable-next-line */ }, [report]);

  const exportFile = async (format: string) => {
    try { await api.download(`/reports/${report}/export?format=${format}&${qs()}`, `${report}.${format}`); }
    catch (e: any) { push(e.message, "error"); }
  };

  return (
    <div>
      <PageHeader icon={ChartBar} title="Reports" subtitle="Filter, export and print operational reports"
        actions={<>
          {canExport && <Button variant="outline" onClick={() => exportFile("csv")}>Export CSV</Button>}
          {canExport && <Button variant="outline" onClick={() => exportFile("xlsx")}>Export Excel</Button>}
          {can("Reports:print") && <Button variant="accent" onClick={() => window.print()}>Print</Button>}
        </>} />

      <Card className="mb-4 p-3 print:hidden">
        <div className="flex flex-wrap gap-3">
          <select className="input max-w-xs" value={report} onChange={(e) => setReport(e.target.value)}>
            {REPORTS.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
          </select>
          <input className="input max-w-[160px]" type="date" value={filters.date_from}
            onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} title="From" />
          <input className="input max-w-[160px]" type="date" value={filters.date_to}
            onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} title="To" />
          <select className="input max-w-xs" value={filters.warehouse_id}
            onChange={(e) => setFilters({ ...filters, warehouse_id: e.target.value })}>
            <option value="">All warehouses</option>
            {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <input className="input max-w-[160px]" placeholder="Status filter" value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })} />
          <Button onClick={run} disabled={loading}>{loading ? <Spinner /> : "Run"}</Button>
        </div>
      </Card>

      <Card className="overflow-hidden">
        {loading ? <TableSkeleton /> : !data?.rows.length ? (
          <EmptyState icon={<ChartBar size={22} weight="duotone" />} title="No rows" hint="Adjust filters and run the report." />
        ) : (
          <div className="overflow-x-auto">
            <div className="px-4 py-2 text-xs text-muted">{data.rows.length} rows</div>
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-xs uppercase text-muted">
                <tr>{data.columns.map((c) => <th key={c} className="px-3 py-2">{c.replace(/_/g, " ")}</th>)}</tr>
              </thead>
              <tbody>
                {data.rows.map((row, i) => (
                  <tr key={i} className="border-t border-line">
                    {data.columns.map((c) => <td key={c} className="px-3 py-2 text-ink">{String(row[c] ?? "")}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
