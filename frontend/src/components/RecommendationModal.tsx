import { useEffect, useState } from "react";
import { Calculator, WarningCircle } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { Modal, Spinner, Badge, EmptyState } from "@/components/ui";
import type { RecommendationResponse, RecoOption } from "@/types";

export function RecommendationModal({ productId, productLabel, requiredQty, warehouseId, onClose }: {
  productId: number; productLabel: string; requiredQty: number;
  warehouseId?: number | null; onClose: () => void;
}) {
  const { push } = useToast();
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setData(await api.post("/stock/recommendation", {
          product_id: productId, required_qty: requiredQty,
          warehouse_id: warehouseId || null,
        }));
      } catch (e: any) { push(e.message, "error"); }
      finally { setLoading(false); }
    })();
  }, [productId, requiredQty, warehouseId]); // eslint-disable-line

  return (
    <Modal open onClose={onClose} title={`Suggested allocation · ${productLabel}`}>
      {loading ? (
        <div className="flex justify-center py-10 text-accent"><Spinner className="h-6 w-6" /></div>
      ) : !data ? (
        <EmptyState icon={<Calculator size={22} weight="duotone" />} title="No suggestion available" />
      ) : !data.can_fulfill && data.options.length === 0 ? (
        <EmptyState icon={<WarningCircle size={22} weight="duotone" />} title="Cannot fulfil"
          hint={`Only ${data.total_saleable} saleable for a required ${data.required_qty}.`} />
      ) : (
        <div className="max-h-[65vh] space-y-4 overflow-y-auto pr-1">
          <p className="text-xs text-muted">
            Required <b className="text-ink">{data.required_qty}</b> · saleable{" "}
            <b className="text-ink">{data.total_saleable}</b>. Options ranked by fulfilment,
            minimum wastage, old stock first, then same batch.
          </p>
          {data.options.map((o, i) => (
            <OptionCard key={i} o={o} best={i === 0} />
          ))}
        </div>
      )}
    </Modal>
  );
}

function OptionCard({ o, best }: { o: RecoOption; best: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${best ? "border-accent bg-accent/5" : "border-line"}`}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {best && <Badge tone="accent">Recommended</Badge>}
        <Badge tone={o.fulfilled ? "success" : "danger"}>
          {o.fulfilled ? "Fulfils" : "Partial"} {o.total_allocated}/{o.required_qty}
        </Badge>
        <Badge tone={o.total_wastage > 0 ? "warning" : "success"}>wastage {o.total_wastage}</Badge>
        {o.same_batch && <Badge tone="neutral">same batch</Badge>}
        <span className="text-xs text-muted">{o.reason}</span>
      </div>
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase text-muted">
          <tr>
            <th className="py-1">Warehouse</th><th className="py-1">Batch</th>
            <th className="py-1">Roll</th><th className="py-1">Type</th>
            <th className="py-1 text-right">Take</th>
            <th className="py-1 text-right">Of</th>
            <th className="py-1 text-right">Remaining</th>
          </tr>
        </thead>
        <tbody>
          {o.picks.map((p) => (
            <tr key={p.stock_item_id} className="border-t border-line">
              <td className="py-1.5 text-muted">{p.warehouse_name}</td>
              <td className="py-1.5 font-medium text-ink">{p.batch_no || "-"}</td>
              <td className="py-1.5">{p.roll_no || "-"}</td>
              <td className="py-1.5">
                <Badge tone={p.is_full_roll ? "success" : "warning"}>
                  {p.is_full_roll ? "full" : "cut"} · {p.item_type}
                </Badge>
              </td>
              <td className="py-1.5 text-right font-semibold text-ink">{p.alloc_qty} {p.unit}</td>
              <td className="py-1.5 text-right text-muted">{p.source_qty}</td>
              <td className="py-1.5 text-right text-muted">{p.remaining_qty}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
