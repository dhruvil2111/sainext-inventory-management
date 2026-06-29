from datetime import datetime, date
from typing import Optional, Any

from pydantic import BaseModel, EmailStr, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Auth ----
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ---- Permissions / roles ----
class PermissionOut(ORMModel):
    id: int
    module: str
    action: str
    code: str
    description: Optional[str] = None


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleOut(ORMModel):
    id: int
    name: str
    description: Optional[str] = None
    is_system: bool
    permission_codes: list[str] = []


class RolePermissionsUpdate(BaseModel):
    permission_codes: list[str]


# ---- Users ----
class UserBase(BaseModel):
    name: str
    email: EmailStr
    mobile: Optional[str] = None
    role_id: int
    assigned_warehouse_id: Optional[int] = None
    assigned_salesman_id: Optional[int] = None
    assigned_dealer_id: Optional[int] = None


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None
    role_id: Optional[int] = None
    status: Optional[str] = None
    assigned_warehouse_id: Optional[int] = None
    assigned_salesman_id: Optional[int] = None
    assigned_dealer_id: Optional[int] = None
    monthly_target: Optional[float] = None
    password: Optional[str] = None


class UserOut(ORMModel):
    id: int
    name: str
    email: EmailStr
    mobile: Optional[str] = None
    role_id: int
    status: str
    assigned_warehouse_id: Optional[int] = None
    assigned_salesman_id: Optional[int] = None
    assigned_dealer_id: Optional[int] = None
    monthly_target: Optional[float] = None
    created_at: Optional[datetime] = None


class UserPermissionsOut(BaseModel):
    role_codes: list[str]            # granted by the user's role
    override_allow: list[str]        # force-granted on top of role
    override_deny: list[str]         # force-removed from role
    effective: list[str]             # final resolved set


class UserOverridesUpdate(BaseModel):
    allow: list[str] = []
    deny: list[str] = []


class MeOut(UserOut):
    role_name: str
    permissions: list[str] = []


# ---- Warehouses ----
class WarehouseBase(BaseModel):
    name: str
    code: str
    location: Optional[str] = None
    address: Optional[str] = None


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None


class WarehouseOut(ORMModel):
    id: int
    name: str
    code: str
    location: Optional[str] = None
    address: Optional[str] = None
    status: str


# ---- Generic ----
class Paginated(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[Any]


# ---- Products ----
class ProductBase(BaseModel):
    pattern_no: str
    product_code: str
    name: str
    collection_name: Optional[str] = None
    brand: Optional[str] = None
    category_id: Optional[int] = None
    product_type: str = "ROLL"
    unit: str = "SQM"
    unit_size: Optional[str] = None
    thickness: Optional[str] = None
    roll_size: Optional[str] = None
    standard_roll_qty: Optional[float] = None
    price: float = 0.0
    status: str = "CONTINUED"
    remarks: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    pattern_no: Optional[str] = None
    name: Optional[str] = None
    collection_name: Optional[str] = None
    brand: Optional[str] = None
    category_id: Optional[int] = None
    product_type: Optional[str] = None
    unit: Optional[str] = None
    unit_size: Optional[str] = None
    thickness: Optional[str] = None
    roll_size: Optional[str] = None
    standard_roll_qty: Optional[float] = None
    price: Optional[float] = None
    status: Optional[str] = None
    remarks: Optional[str] = None
    is_active: Optional[bool] = None


class ProductOut(ORMModel):
    id: int
    pattern_no: str
    product_code: str
    name: str
    collection_name: Optional[str] = None
    brand: Optional[str] = None
    category_id: Optional[int] = None
    product_type: str
    unit: str
    unit_size: Optional[str] = None
    thickness: Optional[str] = None
    roll_size: Optional[str] = None
    standard_roll_qty: Optional[float] = None
    price: float
    status: str
    remarks: Optional[str] = None
    is_active: bool


class CategoryOut(ORMModel):
    id: int
    name: str
    description: Optional[str] = None


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


# ---- Stock ----
class InwardRequest(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: float
    unit: str = "SQM"
    item_type: str = "ROLL"               # ROLL / BOX / LOOSE
    entry_kind: str = "INWARD"            # INWARD | RETURN_IN
    batch_no: Optional[str] = None
    batch_date: Optional[date] = None
    roll_no: Optional[str] = None
    roll_date: Optional[date] = None
    box_count: Optional[int] = None
    purchase_date: Optional[date] = None
    inward_date: Optional[date] = None
    remarks: Optional[str] = None


class AdjustmentRequest(BaseModel):
    stock_item_id: int
    delta: float                          # +in / -out
    remarks: Optional[str] = None
    allow_negative: bool = False          # honoured only for Owner/Admin


class DamageRequest(BaseModel):
    stock_item_id: int
    quantity: float
    remarks: Optional[str] = None


class TransferRequest(BaseModel):
    stock_item_id: int
    to_warehouse_id: int
    quantity: float
    remarks: Optional[str] = None


class StockItemOut(ORMModel):
    id: int
    product_id: int
    warehouse_id: int
    batch_id: Optional[int] = None
    item_type: str
    roll_no: Optional[str] = None
    box_count: Optional[int] = None
    roll_date: Optional[date] = None
    inward_date: Optional[date] = None
    purchase_date: Optional[date] = None
    original_qty: float
    available_qty: float
    unit: str
    status: str
    remarks: Optional[str] = None


class StockItemRow(StockItemOut):
    product_code: str
    product_name: str
    warehouse_name: str
    batch_no: Optional[str] = None


class BlockItemIn(BaseModel):
    stock_item_id: int
    qty: float


class BlockCreate(BaseModel):
    product_id: int
    items: list[BlockItemIn] = []
    auto_allocate: bool = False        # if true and items empty -> use recommendation
    required_qty: Optional[float] = None  # used with auto_allocate
    dealer_id: Optional[int] = None
    salesman_id: Optional[int] = None
    hold_until: Optional[datetime] = None
    remarks: Optional[str] = None
    submit: bool = False               # submit for approval vs save draft


class BlockExtend(BaseModel):
    hold_until: datetime


class BlockActionRemarks(BaseModel):
    remarks: Optional[str] = None


class BlockItemOut(ORMModel):
    id: int
    stock_item_id: int
    warehouse_id: int
    batch_id: Optional[int] = None
    qty: float


class BlockOut(ORMModel):
    id: int
    block_no: str
    product_id: int
    dealer_id: Optional[int] = None
    salesman_id: Optional[int] = None
    required_qty: float
    hold_until: Optional[datetime] = None
    status: str
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    remarks: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    # enriched
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    dealer_name: Optional[str] = None
    items: list[BlockItemOut] = []


class OrderAllocIn(BaseModel):
    stock_item_id: int
    qty: float


class OrderCreate(BaseModel):
    product_id: int
    allocations: list[OrderAllocIn] = []
    auto_allocate: bool = False
    required_qty: Optional[float] = None
    dealer_id: Optional[int] = None
    salesman_id: Optional[int] = None
    is_partial: bool = False
    remarks: Optional[str] = None
    submit: bool = False


class DispatchAction(BaseModel):
    notes: Optional[str] = None
    transport_details: Optional[str] = None


class OrderActionRemarks(BaseModel):
    remarks: Optional[str] = None


class OrderAllocOut(ORMModel):
    id: int
    stock_item_id: int
    warehouse_id: int
    batch_id: Optional[int] = None
    roll_no: Optional[str] = None
    alloc_qty: float
    wastage_qty: float
    is_full_roll: bool
    same_batch: bool


class OrderItemOut(ORMModel):
    id: int
    product_id: int
    qty: float
    unit: str
    price: float
    amount: float
    product_snapshot: Optional[dict] = None
    allocations: list[OrderAllocOut] = []


class OrderOut(ORMModel):
    id: int
    order_no: str
    dealer_id: Optional[int] = None
    salesman_id: Optional[int] = None
    status: str
    total_amount: float
    is_partial: bool
    stock_committed: bool
    source_block_id: Optional[int] = None
    approved_by: Optional[int] = None
    dispatch_by: Optional[int] = None
    remarks: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    dealer_name: Optional[str] = None
    items: list[OrderItemOut] = []


class DealerBase(BaseModel):
    firm_name: str
    owner_name: Optional[str] = None
    concern_person: Optional[str] = None
    contact: Optional[str] = None
    alt_contact: Optional[str] = None
    address: Optional[str] = None
    gst_no: Optional[str] = None
    assigned_salesman_id: Optional[int] = None
    category: Optional[str] = None
    credit_period_days: int = 0
    rating: Optional[float] = None
    price_list_access: bool = False
    offer_letter_access: bool = False


class DealerCreate(DealerBase):
    pass


class DealerUpdate(BaseModel):
    firm_name: Optional[str] = None
    owner_name: Optional[str] = None
    concern_person: Optional[str] = None
    contact: Optional[str] = None
    alt_contact: Optional[str] = None
    address: Optional[str] = None
    gst_no: Optional[str] = None
    assigned_salesman_id: Optional[int] = None
    category: Optional[str] = None
    credit_period_days: Optional[int] = None
    rating: Optional[float] = None
    price_list_access: Optional[bool] = None
    offer_letter_access: Optional[bool] = None
    status: Optional[str] = None


class DealerOut(ORMModel):
    id: int
    firm_name: str
    owner_name: Optional[str] = None
    concern_person: Optional[str] = None
    contact: Optional[str] = None
    alt_contact: Optional[str] = None
    address: Optional[str] = None
    gst_no: Optional[str] = None
    assigned_salesman_id: Optional[int] = None
    category: Optional[str] = None
    credit_period_days: int
    rating: Optional[float] = None
    price_list_access: bool
    offer_letter_access: bool
    status: str
    salesman_name: Optional[str] = None


class PaymentCreate(BaseModel):
    dealer_id: int
    amount: float
    type: str = "DUE"               # DUE | PAYMENT
    order_id: Optional[int] = None
    due_date: Optional[date] = None
    remarks: Optional[str] = None


class PaymentOut(ORMModel):
    id: int
    dealer_id: int
    order_id: Optional[int] = None
    amount: float
    type: str
    due_date: Optional[date] = None
    paid_at: Optional[datetime] = None
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None


class LedgerRow(ORMModel):
    id: int
    product_id: int
    warehouse_id: int
    batch_id: Optional[int] = None
    stock_item_id: Optional[int] = None
    txn_type: str
    qty: float
    before_qty: float
    after_qty: float
    ref_type: Optional[str] = None
    ref_id: Optional[int] = None
    created_at: Optional[datetime] = None
    remarks: Optional[str] = None
    product_code: Optional[str] = None
    warehouse_name: Optional[str] = None
