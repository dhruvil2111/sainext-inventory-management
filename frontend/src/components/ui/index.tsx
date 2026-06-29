import { ReactNode, ButtonHTMLAttributes } from "react";
import { CircleNotch, X, Package } from "@phosphor-icons/react";

export function Button({
  variant = "accent", className = "", children, ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "accent" | "primary" | "ghost" | "outline" | "danger";
}) {
  const map: Record<string, string> = {
    accent: "btn-accent", primary: "btn-primary", ghost: "btn-ghost",
    outline: "btn-outline", danger: "btn-danger",
  };
  return (
    <button className={`${map[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function Card({ className = "", children }: { className?: string; children: ReactNode }) {
  return <div className={`card ${className}`}>{children}</div>;
}

type Tone = "success" | "danger" | "warning" | "neutral" | "accent" | "info";

export function Badge({ tone = "neutral", dot = false, children }: { tone?: Tone; dot?: boolean; children: ReactNode }) {
  const map: Record<Tone, string> = {
    success: "bg-success/12 text-success ring-success/20",
    danger: "bg-danger/12 text-danger ring-danger/20",
    warning: "bg-warning/15 text-warning ring-warning/25",
    accent: "bg-accent/15 text-accent-strong ring-accent/25",
    info: "bg-info/12 text-info ring-info/20",
    neutral: "bg-surface-2 text-muted ring-line",
  };
  const dotc: Record<Tone, string> = {
    success: "bg-success", danger: "bg-danger", warning: "bg-warning",
    accent: "bg-accent", info: "bg-info", neutral: "bg-muted",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-2xs font-semibold ring-1 ring-inset ${map[tone]}`}>
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${dotc[tone]}`} />}
      {children}
    </span>
  );
}

export function StatusDot({ tone }: { tone: "success" | "danger" | "warning" }) {
  const map = { success: "bg-success", danger: "bg-danger", warning: "bg-warning" };
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${map[tone]}`} />;
}

export function Spinner({ className = "" }: { className?: string }) {
  return <CircleNotch className={`animate-spin ${className}`} weight="bold" />;
}

export function EmptyState({ title, hint, icon }: { title: string; hint?: string; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-2 text-muted">
        {icon || <Package size={22} weight="duotone" />}
      </div>
      <p className="text-base font-semibold text-ink">{title}</p>
      {hint && <p className="max-w-sm text-sm leading-relaxed text-muted">{hint}</p>}
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2.5 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-9 w-full" />
      ))}
    </div>
  );
}

export function Modal({ open, onClose, title, children, footer }: {
  open: boolean; onClose: () => void; title: string;
  children: ReactNode; footer?: ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-brand/40 backdrop-blur-[2px]" onClick={onClose} />
      <div className="card relative z-10 w-full max-w-lg animate-fade-in shadow-pop">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h3 className="text-base font-semibold text-ink">{title}</h3>
          <button onClick={onClose} className="rounded-md p-1 text-muted transition hover:bg-surface-2 hover:text-ink">
            <X size={18} weight="bold" />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-line px-5 py-3">{footer}</div>}
      </div>
    </div>
  );
}

export function ConfirmModal({ open, onClose, onConfirm, title, message, danger }: {
  open: boolean; onClose: () => void; onConfirm: () => void;
  title: string; message: string; danger?: boolean;
}) {
  return (
    <Modal open={open} onClose={onClose} title={title}
      footer={<>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button variant={danger ? "danger" : "accent"} onClick={onConfirm}>Confirm</Button>
      </>}>
      <p className="text-sm leading-relaxed text-muted">{message}</p>
    </Modal>
  );
}
