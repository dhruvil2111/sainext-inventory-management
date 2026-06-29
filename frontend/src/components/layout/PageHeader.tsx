import { ReactNode } from "react";
import type { Icon } from "@phosphor-icons/react";

export function PageHeader({ title, subtitle, actions, icon: Icn }: {
  title: string; subtitle?: string; actions?: ReactNode; icon?: Icon;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-3.5">
        {Icn && (
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-surface-2 text-accent-strong ring-1 ring-inset ring-line">
            <Icn size={20} weight="duotone" />
          </span>
        )}
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink md:text-[1.65rem] md:leading-tight">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2 print:hidden">{actions}</div>}
    </div>
  );
}
