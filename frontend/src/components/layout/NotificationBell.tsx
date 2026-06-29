import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, CheckCircle } from "@phosphor-icons/react";
import { api } from "@/lib/api";

interface Item { type: string; label: string; count: number; link: string; tone: string; }

export function NotificationBell() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Item[]>([]);
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  const load = () => api.get("/notifications")
    .then((d) => { setItems(d.items); setCount(d.count); }).catch(() => {});

  useEffect(() => {
    load();
    const t = setInterval(load, 60000);      // refresh each minute
    const onDoc = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => { clearInterval(t); document.removeEventListener("mousedown", onDoc); };
  }, []);

  const dot: Record<string, string> = { warning: "bg-warning", danger: "bg-danger", success: "bg-success" };

  return (
    <div ref={ref} className="relative">
      <button onClick={() => { setOpen((o) => !o); load(); }}
        className="relative rounded-md p-2 text-muted transition hover:bg-surface-2 hover:text-ink" title="Notifications">
        <Bell size={18} weight={count ? "fill" : "regular"} />
        {count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-bold text-white">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-72 overflow-hidden rounded-lg border border-line bg-surface shadow-pop animate-fade-in">
          <div className="border-b border-line px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-muted">
            Notifications
          </div>
          {items.length === 0 ? (
            <div className="flex flex-col items-center gap-2 px-4 py-8 text-center text-sm text-muted">
              <CheckCircle size={24} weight="duotone" className="text-success" />
              You're all caught up.
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              {items.map((it) => (
                <button key={it.type}
                  onClick={() => { setOpen(false); navigate(it.link); }}
                  className="flex w-full items-center gap-3 border-b border-line px-4 py-3 text-left text-sm transition hover:bg-surface-2 last:border-0">
                  <span className={`h-2 w-2 shrink-0 rounded-full ${dot[it.tone] || "bg-muted"}`} />
                  <span className="flex-1 text-ink">{it.label}</span>
                  <span className="rounded-full bg-surface-2 px-2 py-0.5 text-2xs font-bold text-ink">{it.count}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
