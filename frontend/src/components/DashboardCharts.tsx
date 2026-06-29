import { useEffect, useState } from "react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell,
} from "recharts";
import { api } from "@/lib/api";
import { Card } from "@/components/ui";

interface Analytics {
  movement: { date: string; in: number; out: number }[];
  orders_by_status: { status: string; count: number }[];
  top_dues: { dealer: string; outstanding: number }[];
}

function cssVar(name: string, fallback: string) {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v ? `rgb(${v})` : fallback;
}

export function DashboardCharts() {
  const [a, setA] = useState<Analytics | null>(null);
  useEffect(() => { api.get("/dashboard/analytics").then(setA).catch(() => {}); }, []);
  if (!a) return null;

  const accent = cssVar("--c-accent", "#c98a1a");
  const success = cssVar("--c-success", "#169663");
  const danger = cssVar("--c-danger", "#d13a36");
  const line = cssVar("--c-border", "#e2e6ec");
  const muted = cssVar("--c-text-muted", "#646e7c");
  const tip = {
    contentStyle: {
      background: cssVar("--c-surface", "#fff"), border: `1px solid ${line}`,
      borderRadius: 8, fontSize: 12, color: cssVar("--c-text", "#171e2a"),
    },
    cursor: { fill: "rgb(127 127 127 / 0.08)" },
  };
  const fmtDay = (d: string) => d.slice(5); // MM-DD

  return (
    <div className="mt-7 grid gap-4 lg:grid-cols-2">
      <Card className="p-5">
        <h3 className="mb-4 text-sm font-semibold text-ink">Stock movement (last 14 days)</h3>
        {a.movement.length === 0 ? <Empty /> : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={a.movement} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke={line} vertical={false} />
              <XAxis dataKey="date" tickFormatter={fmtDay} tick={{ fill: muted, fontSize: 11 }} axisLine={{ stroke: line }} tickLine={false} />
              <YAxis tick={{ fill: muted, fontSize: 11 }} axisLine={false} tickLine={false} width={32} />
              <Tooltip {...tip} />
              <Bar dataKey="in" name="In" fill={success} radius={[3, 3, 0, 0]} />
              <Bar dataKey="out" name="Out" fill={accent} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Card className="p-5">
        <h3 className="mb-4 text-sm font-semibold text-ink">Orders by status</h3>
        {a.orders_by_status.length === 0 ? <Empty /> : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={a.orders_by_status} layout="vertical" margin={{ left: 24 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={line} horizontal={false} />
              <XAxis type="number" tick={{ fill: muted, fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
              <YAxis type="category" dataKey="status" tick={{ fill: muted, fontSize: 10 }} axisLine={false} tickLine={false} width={120}
                tickFormatter={(s: string) => s.replace(/_/g, " ")} />
              <Tooltip {...tip} />
              <Bar dataKey="count" radius={[0, 3, 3, 0]} fill={accent}>
                {a.orders_by_status.map((_, i) => <Cell key={i} fill={accent} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      {a.top_dues.length > 0 && (
        <Card className="p-5 lg:col-span-2">
          <h3 className="mb-4 text-sm font-semibold text-ink">Top outstanding dealers</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={a.top_dues} margin={{ left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={line} vertical={false} />
              <XAxis dataKey="dealer" tick={{ fill: muted, fontSize: 11 }} axisLine={{ stroke: line }} tickLine={false} />
              <YAxis tick={{ fill: muted, fontSize: 11 }} axisLine={false} tickLine={false} width={56} />
              <Tooltip {...tip} formatter={(v: number) => [`${v.toLocaleString()}`, "Outstanding"]} />
              <Bar dataKey="outstanding" radius={[3, 3, 0, 0]} fill={danger} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}

function Empty() {
  return <div className="flex h-[200px] items-center justify-center text-sm text-muted">No data yet</div>;
}
