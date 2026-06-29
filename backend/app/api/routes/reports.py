"""Reports (Phase 7): JSON data + CSV / XLSX export.

Report types: stock, ledger, orders, blocks, dispatch, payments.
Filters: date_from/date_to, warehouse_id, dealer_id, salesman_id, product_id, status.
Print is handled client-side (window.print on the rendered table).
"""
import csv
import io
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import (
    StockItem, StockLedger, Order, OrderItem, StockBlock, DispatchRecord,
    PaymentRecord, Product, Warehouse, Dealer,
)

router = APIRouter(prefix="/reports", tags=["reports"])

REPORTS = {"stock", "ledger", "orders", "blocks", "dispatch", "payments"}


def _names(db):
    return (
        {p.id: (p.product_code, p.name) for p in db.execute(select(Product)).scalars()},
        {w.id: w.name for w in db.execute(select(Warehouse)).scalars()},
        {d.id: d.firm_name for d in db.execute(select(Dealer)).scalars()},
    )


def _between(dt, dfrom, dto):
    if dt is None:
        return False
    d = dt.date() if isinstance(dt, datetime) else dt
    if dfrom and d < dfrom:
        return False
    if dto and d > dto:
        return False
    return True


def build_report(db: Session, report: str, *, date_from=None, date_to=None,
                 warehouse_id=None, dealer_id=None, product_id=None, status=None):
    prods, whs, deals = _names(db)
    cols: list[str] = []
    rows: list[dict] = []

    if report == "stock":
        cols = ["product_code", "product", "warehouse", "batch", "roll", "type",
                "available", "unit", "inward_date"]
        items = db.execute(select(StockItem)).scalars().all()
        from app.models import Batch
        batches = {b.id: b.batch_no for b in db.execute(select(Batch)).scalars()}
        for it in items:
            if warehouse_id and it.warehouse_id != warehouse_id:
                continue
            if product_id and it.product_id != product_id:
                continue
            if not _between(it.inward_date, date_from, date_to) and (date_from or date_to):
                continue
            pc, pn = prods.get(it.product_id, ("", ""))
            rows.append({"product_code": pc, "product": pn,
                         "warehouse": whs.get(it.warehouse_id, ""),
                         "batch": batches.get(it.batch_id, ""), "roll": it.roll_no or "",
                         "type": it.item_type.value, "available": it.available_qty,
                         "unit": it.unit,
                         "inward_date": it.inward_date.isoformat() if it.inward_date else ""})

    elif report == "ledger":
        cols = ["id", "product_code", "warehouse", "txn_type", "qty", "before", "after", "when", "remarks"]
        for le in db.execute(select(StockLedger).order_by(StockLedger.id.desc())).scalars():
            if warehouse_id and le.warehouse_id != warehouse_id:
                continue
            if product_id and le.product_id != product_id:
                continue
            if status and le.txn_type.value != status:
                continue
            if (date_from or date_to) and not _between(le.created_at, date_from, date_to):
                continue
            pc, _ = prods.get(le.product_id, ("", ""))
            rows.append({"id": le.id, "product_code": pc,
                         "warehouse": whs.get(le.warehouse_id, ""),
                         "txn_type": le.txn_type.value, "qty": le.qty,
                         "before": le.before_qty, "after": le.after_qty,
                         "when": le.created_at.isoformat() if le.created_at else "",
                         "remarks": le.remarks or ""})

    elif report == "orders":
        cols = ["order_no", "dealer", "status", "amount", "committed", "created"]
        for o in db.execute(select(Order).order_by(Order.id.desc())).scalars():
            if dealer_id and o.dealer_id != dealer_id:
                continue
            if status and o.status.value != status:
                continue
            if (date_from or date_to) and not _between(o.created_at, date_from, date_to):
                continue
            rows.append({"order_no": o.order_no, "dealer": deals.get(o.dealer_id, ""),
                         "status": o.status.value, "amount": o.total_amount,
                         "committed": "yes" if o.stock_committed else "no",
                         "created": o.created_at.isoformat() if o.created_at else ""})

    elif report == "blocks":
        cols = ["block_no", "product_code", "dealer", "qty", "status", "hold_until"]
        for b in db.execute(select(StockBlock).order_by(StockBlock.id.desc())).scalars():
            if dealer_id and b.dealer_id != dealer_id:
                continue
            if product_id and b.product_id != product_id:
                continue
            if status and b.status.value != status:
                continue
            pc, _ = prods.get(b.product_id, ("", ""))
            rows.append({"block_no": b.block_no, "product_code": pc,
                         "dealer": deals.get(b.dealer_id, ""), "qty": b.required_qty,
                         "status": b.status.value,
                         "hold_until": b.hold_until.isoformat() if b.hold_until else ""})

    elif report == "dispatch":
        cols = ["id", "order_id", "status", "notes", "dispatched_at"]
        for d in db.execute(select(DispatchRecord).order_by(DispatchRecord.id.desc())).scalars():
            if status and d.status != status:
                continue
            if (date_from or date_to) and not _between(d.created_at, date_from, date_to):
                continue
            rows.append({"id": d.id, "order_id": d.order_id, "status": d.status,
                         "notes": d.notes or "",
                         "dispatched_at": d.dispatched_at.isoformat() if d.dispatched_at else ""})

    elif report == "payments":
        cols = ["id", "dealer", "type", "amount", "due_date", "paid_at", "remarks"]
        for p in db.execute(select(PaymentRecord).order_by(PaymentRecord.id.desc())).scalars():
            if dealer_id and p.dealer_id != dealer_id:
                continue
            if status and p.type.value != status:
                continue
            rows.append({"id": p.id, "dealer": deals.get(p.dealer_id, ""),
                         "type": p.type.value, "amount": p.amount,
                         "due_date": p.due_date.isoformat() if p.due_date else "",
                         "paid_at": p.paid_at.isoformat() if p.paid_at else "",
                         "remarks": p.remarks or ""})

    return cols, rows


def _filters(date_from, date_to, warehouse_id, dealer_id, product_id, status):
    return dict(date_from=date_from, date_to=date_to, warehouse_id=warehouse_id,
                dealer_id=dealer_id, product_id=product_id, status=status)


@router.get("/{report}")
def get_report(
    report: str,
    date_from: date | None = None, date_to: date | None = None,
    warehouse_id: int | None = None, dealer_id: int | None = None,
    product_id: int | None = None, status: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_permission("Reports:view")),
):
    if report not in REPORTS:
        raise HTTPException(404, f"Unknown report '{report}'")
    cols, rows = build_report(db, report,
                              **_filters(date_from, date_to, warehouse_id, dealer_id, product_id, status))
    return {"report": report, "columns": cols, "count": len(rows), "rows": rows}


@router.get("/{report}/export")
def export_report(
    report: str,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    date_from: date | None = None, date_to: date | None = None,
    warehouse_id: int | None = None, dealer_id: int | None = None,
    product_id: int | None = None, status: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_permission("Reports:export")),
):
    if report not in REPORTS:
        raise HTTPException(404, f"Unknown report '{report}'")
    cols, rows = build_report(db, report,
                              **_filters(date_from, date_to, warehouse_id, dealer_id, product_id, status))
    fname = f"sainext_{report}_{date.today().isoformat()}"

    if format == "csv":
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]), media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={fname}.csv"})

    # xlsx
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = report[:31]
    ws.append(cols)
    for r in rows:
        ws.append([r.get(c, "") for c in cols])
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return StreamingResponse(
        out, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}.xlsx"})
