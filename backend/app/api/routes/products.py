from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import Product, ProductCategory, User
from app.models.enums import ProductType, ProductStatus
from app.schemas import (
    ProductOut, ProductCreate, ProductUpdate, CategoryOut, CategoryCreate, Paginated,
)
from app.services.audit import log_action

router = APIRouter(prefix="/products", tags=["products"])


def _out(p: Product) -> ProductOut:
    return ProductOut.model_validate({
        **p.__dict__,
        "product_type": p.product_type.value,
        "status": p.status.value,
    })


@router.get("", response_model=Paginated)
def list_products(
    q: str | None = None,
    brand: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_permission("Products:view")),
):
    stmt = select(Product)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(
            Product.pattern_no.ilike(like), Product.product_code.ilike(like),
            Product.name.ilike(like), Product.collection_name.ilike(like),
            Product.brand.ilike(like),
        ))
    if brand:
        stmt = stmt.where(Product.brand == brand)
    if status:
        stmt = stmt.where(Product.status == ProductStatus(status))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(
        stmt.order_by(Product.pattern_no).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return Paginated(total=total or 0, page=page, page_size=page_size,
                     items=[_out(p) for p in rows])


@router.get("/search", response_model=list[ProductOut])
def search_products(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _=Depends(require_permission("Products:view")),
):
    like = f"%{q}%"
    rows = db.execute(
        select(Product).where(or_(
            Product.pattern_no.ilike(like), Product.product_code.ilike(like),
            Product.name.ilike(like), Product.collection_name.ilike(like),
            Product.brand.ilike(like),
        )).limit(25)
    ).scalars().all()
    return [_out(p) for p in rows]


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db),
                    _=Depends(require_permission("Products:view"))):
    return db.execute(select(ProductCategory).order_by(ProductCategory.name)).scalars().all()


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("Products:create"))):
    if db.execute(select(ProductCategory).where(ProductCategory.name == payload.name)).scalar_one_or_none():
        raise HTTPException(409, "Category already exists")
    cat = ProductCategory(name=payload.name, description=payload.description)
    db.add(cat)
    db.flush()
    log_action(db, actor.id, "Products", "create", "ProductCategory", cat.id,
               new_value={"name": cat.name})
    db.commit()
    db.refresh(cat)
    return cat


@router.post("", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("Products:create"))):
    if db.execute(select(Product).where(Product.product_code == payload.product_code)).scalar_one_or_none():
        raise HTTPException(409, "Product code already exists")
    data = payload.model_dump()
    data["product_type"] = ProductType(data["product_type"])
    data["status"] = ProductStatus(data["status"])
    product = Product(is_active=True, **data)
    db.add(product)
    db.flush()
    log_action(db, actor.id, "Products", "create", "Product", product.id,
               new_value={"code": product.product_code})
    db.commit()
    db.refresh(product)
    return _out(product)


@router.put("/{pid}", response_model=ProductOut)
def update_product(pid: int, payload: ProductUpdate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("Products:edit"))):
    product = db.get(Product, pid)
    if not product:
        raise HTTPException(404, "Product not found")
    data = payload.model_dump(exclude_unset=True)
    if "product_type" in data and data["product_type"] is not None:
        data["product_type"] = ProductType(data["product_type"])
    if "status" in data and data["status"] is not None:
        data["status"] = ProductStatus(data["status"])
    for f, val in data.items():
        if val is not None:
            setattr(product, f, val)
    log_action(db, actor.id, "Products", "edit", "Product", product.id)
    db.commit()
    db.refresh(product)
    return _out(product)
