// Navigation model. Each item links to a module and the permission code that
// controls its visibility. The layout filters by the user's effective perms.
import type { Icon } from "@phosphor-icons/react";
import {
  SquaresFour, MagnifyingGlass, TrayArrowDown, Scroll, LockKey, Receipt,
  Tag, Warehouse, Handshake, ChartLineUp, Truck, Wallet, ChartBar,
  UsersThree, ShieldCheck, Gear, ClockCounterClockwise,
} from "@phosphor-icons/react";

export interface NavItem {
  label: string;
  path: string;
  perm: string;     // permission code required to see the item
  icon: Icon;       // Phosphor icon component
  group: string;    // sidebar section grouping
  ready?: boolean;
}

export const NAV: NavItem[] = [
  { label: "Dashboard", path: "/", perm: "Dashboard:view", icon: SquaresFour, group: "Overview", ready: true },

  { label: "Stock Check", path: "/stock-check", perm: "Stock Check:view", icon: MagnifyingGlass, group: "Inventory", ready: true },
  { label: "Stock Inward", path: "/stock-inward", perm: "Stock Inward:view", icon: TrayArrowDown, group: "Inventory", ready: true },
  { label: "Stock Ledger", path: "/stock-ledger", perm: "Stock Inward:view", icon: Scroll, group: "Inventory", ready: true },
  { label: "Products", path: "/products", perm: "Products:view", icon: Tag, group: "Inventory", ready: true },
  { label: "Warehouses", path: "/warehouses", perm: "Warehouses:view", icon: Warehouse, group: "Inventory", ready: true },

  { label: "Material Blocking", path: "/blocks", perm: "Stock Blocking:view", icon: LockKey, group: "Operations", ready: true },
  { label: "Orders", path: "/orders", perm: "Orders:view", icon: Receipt, group: "Operations", ready: true },
  { label: "Dispatch", path: "/dispatch", perm: "Dispatch:view", icon: Truck, group: "Operations", ready: true },

  { label: "Dealers", path: "/dealers", perm: "Dealers:view", icon: Handshake, group: "Commercial", ready: true },
  { label: "Salesman", path: "/salesman", perm: "Salesman Dashboard:view", icon: ChartLineUp, group: "Commercial", ready: true },
  { label: "Accounts", path: "/accounts", perm: "Accounts:view", icon: Wallet, group: "Commercial", ready: true },
  { label: "Reports", path: "/reports", perm: "Reports:view", icon: ChartBar, group: "Commercial", ready: true },

  { label: "Users", path: "/users", perm: "Users:view", icon: UsersThree, group: "Administration", ready: true },
  { label: "Roles & Permissions", path: "/roles", perm: "Roles & Permissions:view", icon: ShieldCheck, group: "Administration", ready: true },
  { label: "Audit Log", path: "/audit-logs", perm: "Roles & Permissions:view", icon: ClockCounterClockwise, group: "Administration", ready: true },
  { label: "Settings", path: "/settings", perm: "Settings:view", icon: Gear, group: "Administration", ready: true },
];

export const NAV_GROUPS = ["Overview", "Inventory", "Operations", "Commercial", "Administration"];
