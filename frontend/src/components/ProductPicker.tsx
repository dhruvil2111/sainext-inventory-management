import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Product } from "@/types";

export function ProductPicker({ value, onChange }: {
  value: Product | null;
  onChange: (p: Product | null) => void;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Product[]>([]);
  const [openList, setOpenList] = useState(false);
  const timer = useRef<any>(null);

  useEffect(() => {
    if (!q || (value && q === `${value.pattern_no} · ${value.name}`)) return;
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      try {
        const r = await api.get(`/products/search?q=${encodeURIComponent(q)}`);
        setResults(r); setOpenList(true);
      } catch { /* ignore */ }
    }, 250);
    return () => clearTimeout(timer.current);
  }, [q]); // eslint-disable-line

  return (
    <div className="relative">
      <input className="input" placeholder="Search product by pattern / code / name…"
        value={value ? `${value.pattern_no} · ${value.name}` : q}
        onChange={(e) => { onChange(null); setQ(e.target.value); }}
        onFocus={() => results.length && setOpenList(true)} />
      {openList && results.length > 0 && !value && (
        <div className="absolute z-20 mt-1 max-h-60 w-full overflow-y-auto rounded-xl border border-line bg-surface shadow-card">
          {results.map((p) => (
            <button key={p.id} type="button"
              onClick={() => { onChange(p); setOpenList(false); setQ(""); }}
              className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-surface-2">
              <span><b className="text-ink">{p.pattern_no}</b> <span className="text-muted">{p.product_code}</span> - {p.name}</span>
              <span className="text-xs text-muted">{p.unit}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
