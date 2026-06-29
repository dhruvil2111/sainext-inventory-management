import enum


class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class WarehouseStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class ProductType(str, enum.Enum):
    ROLL = "ROLL"
    BOX = "BOX"
    LOOSE = "LOOSE"
    BATCH = "BATCH"


class ProductStatus(str, enum.Enum):
    CONTINUED = "CONTINUED"
    DISCONTINUED = "DISCONTINUED"


class StockItemType(str, enum.Enum):
    ROLL = "ROLL"
    BOX = "BOX"
    LOOSE = "LOOSE"


class LedgerTxnType(str, enum.Enum):
    INWARD = "INWARD"
    OUTWARD = "OUTWARD"
    BLOCK = "BLOCK"
    BLOCK_RELEASE = "BLOCK_RELEASE"
    ORDER_COMMIT = "ORDER_COMMIT"
    ORDER_CANCEL_RELEASE = "ORDER_CANCEL_RELEASE"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"
    DAMAGE = "DAMAGE"
    RETURN_IN = "RETURN_IN"


class BlockStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"
    CONVERTED = "CONVERTED"


class OrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    IN_PROCESS = "IN_PROCESS"
    READY_FOR_DISPATCH = "READY_FOR_DISPATCH"
    DISPATCHED = "DISPATCHED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    PRE_ORDER = "PRE_ORDER"


class PaymentType(str, enum.Enum):
    DUE = "DUE"
    PAYMENT = "PAYMENT"
