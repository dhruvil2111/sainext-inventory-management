"""Canonical lists of modules and permission actions used to seed the matrix."""

MODULES = [
    "Dashboard", "Users", "Roles & Permissions", "Warehouses", "Products",
    "Stock Inward", "Stock Check", "Stock Blocking", "Orders", "Dealers",
    "Salesman Dashboard", "Dispatch", "Accounts", "Reports", "Settings",
]

ACTIONS = [
    "view", "create", "edit", "delete", "approve", "reject", "export", "print",
    "block_stock", "release_stock", "convert_block_to_order", "view_price",
    "view_batch_details", "view_reports", "manage_users", "manage_permissions",
]

# Actions that only make sense on certain modules. Anything not listed gets the
# generic CRUD set. This keeps the seeded matrix realistic rather than a full
# cartesian explosion.
MODULE_ACTIONS = {
    "Dashboard": ["view"],
    "Users": ["view", "create", "edit", "delete", "manage_users"],
    "Roles & Permissions": ["view", "create", "edit", "delete", "manage_permissions"],
    "Warehouses": ["view", "create", "edit", "delete"],
    "Products": ["view", "create", "edit", "delete", "view_price"],
    "Stock Inward": ["view", "create", "edit", "delete"],
    "Stock Check": ["view", "view_price", "view_batch_details", "export", "print"],
    "Stock Blocking": ["view", "create", "edit", "approve", "reject",
                       "block_stock", "release_stock", "convert_block_to_order"],
    "Orders": ["view", "create", "edit", "approve", "reject", "delete"],
    "Dealers": ["view", "create", "edit", "delete", "view_price"],
    "Salesman Dashboard": ["view"],
    "Dispatch": ["view", "edit"],
    "Accounts": ["view", "edit", "export"],
    "Reports": ["view", "view_reports", "export", "print"],
    "Settings": ["view", "edit"],
}

DEFAULT_ROLES = [
    "Owner", "Admin", "Manager", "Operator", "Salesman",
    "Dealer/Partner", "Dispatch Team", "Accounts Team", "Telecaller",
]
