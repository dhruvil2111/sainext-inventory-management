export interface Me {
  id: number;
  name: string;
  email: string;
  mobile?: string | null;
  role_id: number;
  role_name: string;
  status: string;
  assigned_warehouse_id?: number | null;
  permissions: string[];
}

export interface Role {
  id: number;
  name: string;
  description?: string | null;
  is_system: boolean;
  permission_codes: string[];
}

export interface Permission {
  id: number;
  module: string;
  action: string;
  code: string;
  description?: string | null;
}

export interface User {
  id: number;
  name: string;
  email: string;
  mobile?: string | null;
  role_id: number;
  status: string;
  assigned_warehouse_id?: number | null;
  created_at?: string;
}

export interface Warehouse {
  id: number;
  name: string;
  code: string;
  location?: string | null;
  address?: string | null;
  status: string;
}

export interface Paginated<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface Product {
  id: number;
  pattern_no: string;
  product_code: string;
  name: string;
  collection_name?: string | null;
  brand?: string | null;
  category_id?: number | null;
  product_type: string;
  unit: string;
  unit_size?: string | null;
  thickness?: string | null;
  roll_size?: string | null;
  standard_roll_qty?: number | null;
  price: number;
  status: string;
  remarks?: string | null;
  is_active: boolean;
}

export interface StockItem {
  id: number;
  product_id: number;
  warehouse_id: number;
  batch_id?: number | null;
  item_type: string;
  roll_no?: string | null;
  box_count?: number | null;
  roll_date?: string | null;
  inward_date?: string | null;
  purchase_date?: string | null;
  original_qty: number;
  available_qty: number;
  unit: string;
  status: string;
  remarks?: string | null;
  product_code: string;
  product_name: string;
  warehouse_name: string;
  batch_no?: string | null;
}

export interface LedgerRow {
  id: number;
  product_id: number;
  warehouse_id: number;
  batch_id?: number | null;
  stock_item_id?: number | null;
  txn_type: string;
  qty: number;
  before_qty: number;
  after_qty: number;
  ref_type?: string | null;
  ref_id?: number | null;
  created_at?: string | null;
  remarks?: string | null;
  product_code?: string | null;
  warehouse_name?: string | null;
}

export interface UserPermissions {
  role_codes: string[];
  override_allow: string[];
  override_deny: string[];
  effective: string[];
}

export interface Category {
  id: number;
  name: string;
  description?: string | null;
}

export interface WhAvail {
  warehouse_id: number;
  warehouse_name: string;
  available: number;
  blocked: number;
  saleable: number;
  status: "green" | "red" | "yellow";
}

export interface BatchAvail {
  batch_id: number;
  batch_no?: string | null;
  batch_date?: string | null;
  available: number;
  blocked: number;
  saleable: number;
}

export interface StockItemDetail {
  stock_item_id: number;
  warehouse_id: number;
  warehouse_name?: string | null;
  batch_id?: number | null;
  batch_no?: string | null;
  batch_date?: string | null;
  item_type: string;
  roll_no?: string | null;
  box_count?: number | null;
  unit: string;
  roll_date?: string | null;
  inward_date?: string | null;
  purchase_date?: string | null;
  original_qty: number;
  available_qty: number;
  blocked_qty: number;
  saleable_qty: number;
  status: string;
}

export interface StockCheckResult {
  product: Product & { price: number | null };
  total_available: number;
  total_blocked: number;
  total_saleable: number;
  required_qty: number;
  can_fulfill: boolean;
  status: "green" | "red" | "yellow";
  negative_warning: boolean;
  by_type: Record<string, number>;
  warehouses: WhAvail[];
  batches?: BatchAvail[];
  items?: StockItemDetail[];
}

export interface StockCheckResponse {
  count: number;
  can_view_price: boolean;
  can_view_batch_details: boolean;
  results: StockCheckResult[];
}

export interface RecoPick {
  stock_item_id: number;
  warehouse_id: number;
  warehouse_name?: string | null;
  batch_id?: number | null;
  batch_no?: string | null;
  batch_date?: string | null;
  roll_no?: string | null;
  item_type: string;
  unit: string;
  source_qty: number;
  alloc_qty: number;
  remaining_qty: number;
  is_full_roll: boolean;
  wastage: number;
}

export interface RecoOption {
  strategy: string;
  reason: string;
  picks: RecoPick[];
  total_allocated: number;
  required_qty: number;
  fulfilled: boolean;
  total_wastage: number;
  same_batch: boolean;
  same_warehouse: boolean;
  warehouses: string[];
  batches: string[];
}

export interface RecommendationResponse {
  product_id: number;
  required_qty: number;
  total_saleable: number;
  can_fulfill: boolean;
  options: RecoOption[];
}

export interface BlockItem {
  id: number;
  stock_item_id: number;
  warehouse_id: number;
  batch_id?: number | null;
  qty: number;
}

export interface Block {
  id: number;
  block_no: string;
  product_id: number;
  dealer_id?: number | null;
  salesman_id?: number | null;
  required_qty: number;
  hold_until?: string | null;
  status: string;
  approved_by?: number | null;
  approved_at?: string | null;
  remarks?: string | null;
  created_by?: number | null;
  created_at?: string | null;
  product_code?: string | null;
  product_name?: string | null;
  dealer_name?: string | null;
  items: BlockItem[];
}

export interface BlockSummary {
  pending_approval: number;
  approved: number;
  expiring_today: number;
  expired: number;
}

export interface OrderAllocation {
  id: number;
  stock_item_id: number;
  warehouse_id: number;
  batch_id?: number | null;
  roll_no?: string | null;
  alloc_qty: number;
  wastage_qty: number;
  is_full_roll: boolean;
  same_batch: boolean;
}

export interface OrderItemT {
  id: number;
  product_id: number;
  qty: number;
  unit: string;
  price: number;
  amount: number;
  product_snapshot?: { product_code?: string; name?: string } | null;
  allocations: OrderAllocation[];
}

export interface Order {
  id: number;
  order_no: string;
  dealer_id?: number | null;
  salesman_id?: number | null;
  status: string;
  total_amount: number;
  is_partial: boolean;
  stock_committed: boolean;
  source_block_id?: number | null;
  approved_by?: number | null;
  dispatch_by?: number | null;
  remarks?: string | null;
  created_by?: number | null;
  created_at?: string | null;
  dealer_name?: string | null;
  items: OrderItemT[];
}

export interface Dealer {
  id: number;
  firm_name: string;
  owner_name?: string | null;
  concern_person?: string | null;
  contact?: string | null;
  alt_contact?: string | null;
  address?: string | null;
  gst_no?: string | null;
  assigned_salesman_id?: number | null;
  category?: string | null;
  credit_period_days: number;
  rating?: number | null;
  price_list_access: boolean;
  offer_letter_access: boolean;
  status: string;
  salesman_name?: string | null;
}
