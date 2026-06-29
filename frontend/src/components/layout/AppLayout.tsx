import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { List, SignOut, Cube } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";
import { NAV, NAV_GROUPS, NavItem } from "@/lib/nav";
import { ThemeToggle } from "./ThemeToggle";
import { NotificationBell } from "./NotificationBell";

function Brand({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <div className="flex items-center gap-2.5 px-3">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-accent-fg">
        <Cube size={18} weight="fill" />
      </div>
      {!collapsed && (
        <div className="leading-tight">
          <div className="text-sm font-bold tracking-tight text-brand-fg">Sainext</div>
          <div className="text-2xs text-brand-fg/45">Inventory OS</div>
        </div>
      )}
    </div>
  );
}

export function AppLayout() {
  const { user, logout, can } = useAuth();
  const navigate = useNavigate();
  const [drawer, setDrawer] = useState(false);
  const items = NAV.filter((i) => can(i.perm));

  const navList = (onClick?: () => void) => (
    <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-2">
      {NAV_GROUPS.map((group) => {
        const groupItems = items.filter((i) => i.group === group);
        if (!groupItems.length) return null;
        return (
          <div key={group}>
            <div className="px-3 pb-1.5 text-2xs font-semibold uppercase tracking-wider text-brand-fg/35">
              {group}
            </div>
            <div className="space-y-0.5">
              {groupItems.map((i) => <NavRow key={i.path} item={i} onClick={onClick} />)}
            </div>
          </div>
        );
      })}
    </nav>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-bg print:block print:h-auto print:overflow-visible">
      {/* Desktop sidebar */}
      <aside className="hidden w-[248px] shrink-0 flex-col border-r border-black/20 bg-brand py-4 md:flex print:hidden">
        <div className="mb-4"><Brand /></div>
        {navList()}
        <div className="mx-3 mt-2 border-t border-white/5 px-3 pt-3 text-2xs text-brand-fg/35">
          v0.1 · {items.length} modules
        </div>
      </aside>

      {/* Mobile drawer */}
      {drawer && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-brand/50 backdrop-blur-sm" onClick={() => setDrawer(false)} />
          <aside className="absolute left-0 top-0 flex h-full w-[260px] flex-col bg-brand py-4 shadow-pop">
            <div className="mb-4"><Brand /></div>
            {navList(() => setDrawer(false))}
          </aside>
        </div>
      )}

      {/* Main column */}
      <div className="flex flex-1 flex-col overflow-hidden print:overflow-visible">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-surface/80 px-4 backdrop-blur md:px-6 print:hidden">
          <button className="btn-ghost h-9 w-9 !px-0 md:hidden" onClick={() => setDrawer(true)}>
            <List size={20} />
          </button>
          <div className="flex-1" />
          <NotificationBell />
          <ThemeToggle />
          <div className="mx-1 h-6 w-px bg-line" />
          <div className="flex items-center gap-2.5">
            <div className="hidden text-right sm:block">
              <div className="text-xs font-semibold leading-tight text-ink">{user?.name}</div>
              <div className="text-2xs text-muted">{user?.role_name}</div>
            </div>
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/15 text-xs font-bold text-accent-strong ring-1 ring-inset ring-accent/25">
              {user?.name?.charAt(0)}
            </div>
            <button
              className="rounded-md p-2 text-muted transition hover:bg-surface-2 hover:text-ink"
              title="Log out"
              onClick={() => { logout(); navigate("/login"); }}
            >
              <SignOut size={18} />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto px-4 py-5 pb-24 md:px-6 md:py-7 md:pb-8 print:overflow-visible print:p-0">
          <div className="mx-auto max-w-[1400px] animate-fade-in print:max-w-none">
            <Outlet />
          </div>
        </main>

        {/* Mobile bottom nav */}
        <nav className="fixed bottom-0 left-0 right-0 z-30 flex border-t border-line bg-surface/95 backdrop-blur md:hidden print:hidden">
          {items.slice(0, 5).map((i) => (
            <NavLink key={i.path} to={i.path} end={i.path === "/"}
              className={({ isActive }) =>
                `flex flex-1 flex-col items-center gap-0.5 py-2 text-2xs ${isActive ? "text-accent-strong" : "text-muted"}`}>
              <i.icon size={20} weight="regular" />
              {i.label.split(" ")[0]}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}

function NavRow({ item, onClick }: { item: NavItem; onClick?: () => void }) {
  return (
    <NavLink
      to={item.path}
      end={item.path === "/"}
      onClick={onClick}
      className={({ isActive }) =>
        `group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition ${
          isActive
            ? "bg-white/10 text-brand-fg"
            : "text-brand-fg/65 hover:bg-white/5 hover:text-brand-fg"
        }`
      }
    >
      {({ isActive }) => (
        <>
          <span className={`relative flex h-5 w-5 items-center justify-center ${isActive ? "text-accent" : "text-brand-fg/55 group-hover:text-brand-fg/80"}`}>
            <item.icon size={18} weight={isActive ? "fill" : "regular"} />
          </span>
          <span className="flex-1">{item.label}</span>
          {isActive && <span className="h-4 w-1 rounded-full bg-accent" />}
        </>
      )}
    </NavLink>
  );
}
