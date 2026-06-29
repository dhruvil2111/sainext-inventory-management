"""Stock recommendation engine (Phase 4).

Given a required quantity for a product, suggest the best allocation(s) from the
available saleable stock. Encodes the business rules:

Priority order (spec §9):
  1. Fulfil the required quantity exactly if possible
  2. Minimum wastage
  3. Old stock first
  4. Same batch
  5. Same warehouse
  6. Mixed batch only when needed

Old-stock-first sort uses: batch_date -> roll_date -> inward_date ->
purchase_date -> stock entry (id). Loose material is preferred over cutting a
full roll when it reduces wastage.

Partial cutting: a roll of 50 can serve an order of 10; the remaining 40 stays
available as loose stock. Each pick records source/alloc/remaining/wastage,
where wastage is the leftover of a *partially* consumed piece (a fully consumed
piece has zero wastage).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import StockItem, Batch, Warehouse
from app.services.stock import _approved_blocked_by_item

EPS = 1e-9


def _ordinal(d) -> int:
    if d is None:
        return 10 ** 9
    if isinstance(d, date):
        return d.toordinal()
    return 10 ** 9


def _age_key(it: StockItem, batches: dict[int, Batch]):
    """Lower = older = allocate first."""
    b = batches.get(it.batch_id) if it.batch_id else None
    return (
        _ordinal(b.batch_date if b else None),
        _ordinal(it.roll_date),
        _ordinal(it.inward_date),
        _ordinal(it.purchase_date),
        it.id,
    )


def _saleable_sources(db: Session, product_id: int, warehouse_id: int | None):
    stmt = select(StockItem).where(StockItem.product_id == product_id)
    if warehouse_id:
        stmt = stmt.where(StockItem.warehouse_id == warehouse_id)
    items = db.execute(stmt).scalars().all()
    blocked = _approved_blocked_by_item(db, product_id)
    sources = []
    for it in items:
        sale = it.available_qty - blocked.get(it.id, 0.0)
        if sale > EPS:
            sources.append((it, sale))
    return sources


def _pick(it: StockItem, batches, wh_names, alloc: float, source_qty: float) -> dict:
    b = batches.get(it.batch_id) if it.batch_id else None
    partial = alloc < source_qty - EPS
    return {
        "stock_item_id": it.id,
        "warehouse_id": it.warehouse_id,
        "warehouse_name": wh_names.get(it.warehouse_id),
        "batch_id": it.batch_id,
        "batch_no": b.batch_no if b else None,
        "batch_date": b.batch_date.isoformat() if b and b.batch_date else None,
        "roll_no": it.roll_no,
        "item_type": it.item_type.value,
        "unit": it.unit,
        "source_qty": round(source_qty, 4),
        "alloc_qty": round(alloc, 4),
        "remaining_qty": round(source_qty - alloc, 4),
        "is_full_roll": not partial,            # fully consumed piece
        "wastage": round(source_qty - alloc, 4) if partial else 0.0,
    }


def _make_option(strategy: str, picks: list[dict], required: float,
                 batches: dict) -> dict | None:
    if not picks:
        return None
    allocated = sum(p["alloc_qty"] for p in picks)
    wastage = sum(p["wastage"] for p in picks)
    batch_ids = {p["batch_id"] for p in picks}
    wh_ids = {p["warehouse_id"] for p in picks}
    same_batch = len(batch_ids) == 1
    same_wh = len(wh_ids) == 1
    fulfilled = allocated >= required - EPS
    has_loose = any(p["item_type"] == "LOOSE" for p in picks)

    reasons = []
    if fulfilled:
        reasons.append("fulfils required qty")
    if wastage <= EPS:
        reasons.append("zero wastage")
    else:
        reasons.append("minimum wastage")
    if same_batch:
        reasons.append("same batch")
    if has_loose:
        reasons.append("loose first")
    reasons.append("old stock first")

    # oldest batch_date among picks for tie-breaking
    oldest = min((p["batch_date"] or "9999-99-99") for p in picks)
    return {
        "strategy": strategy,
        "reason": ", ".join(reasons),
        "picks": picks,
        "total_allocated": round(allocated, 4),
        "required_qty": required,
        "fulfilled": fulfilled,
        "total_wastage": round(wastage, 4),
        "same_batch": same_batch,
        "same_warehouse": same_wh,
        "warehouses": sorted({p["warehouse_name"] for p in picks}),
        "batches": sorted({p["batch_no"] for p in picks if p["batch_no"]}),
        "_oldest": oldest,
        "_picks_sig": tuple(sorted((p["stock_item_id"], p["alloc_qty"]) for p in picks)),
    }


def _greedy(sources, required, batches, wh_names, strategy):
    """Oldest-first greedy fill (last piece cut partially)."""
    need = required
    picks = []
    for it, s in sorted(sources, key=lambda x: _age_key(x[0], batches)):
        if need <= EPS:
            break
        take = min(s, need)
        picks.append(_pick(it, batches, wh_names, take, s))
        need -= take
    return _make_option(strategy, picks, required, batches)


def _min_waste(sources, required, batches, wh_names, strategy):
    """Consume oldest full pieces that fit without overshoot, then cover the
    remainder with the smallest single piece that still covers it (nearest
    above) -> minimum wastage. Falls back to largest-first if no single piece
    covers the remainder."""
    pool = sorted(sources, key=lambda x: _age_key(x[0], batches))
    need = required
    picks = []
    used = set()
    for it, s in pool:
        if need <= EPS:
            break
        if s <= need + EPS:                      # fits whole without overshoot
            picks.append(_pick(it, batches, wh_names, s, s))
            need -= s
            used.add(it.id)
    if need > EPS:
        remaining = [(it, s) for it, s in pool if it.id not in used]
        covers = [(it, s) for it, s in remaining if s >= need - EPS]
        if covers:
            it, s = min(covers, key=lambda x: x[1])   # nearest above
            picks.append(_pick(it, batches, wh_names, need, s))
            need = 0
        else:
            for it, s in sorted(remaining, key=lambda x: -x[1]):
                if need <= EPS:
                    break
                take = min(s, need)
                picks.append(_pick(it, batches, wh_names, take, s))
                need -= take
    return _make_option(strategy, picks, required, batches)


def recommend(db: Session, product, required_qty: float,
              warehouse_id: int | None = None, max_options: int = 5) -> dict:
    required = float(required_qty)
    sources = _saleable_sources(db, product.id, warehouse_id)
    batches = {b.id: b for b in db.execute(
        select(Batch).where(Batch.product_id == product.id)).scalars().all()}
    wh_names = {w.id: w.name for w in db.execute(select(Warehouse)).scalars().all()}
    total_saleable = sum(s for _, s in sources)

    options: list[dict] = []

    if required > EPS:
        # Case 1: single-source candidates (a piece that alone covers required).
        singles = [(it, s) for it, s in sources if s >= required - EPS]
        # nearest-above first, loose preferred, then old stock
        singles.sort(key=lambda x: (x[1] - required,
                                    0 if x[0].item_type.value == "LOOSE" else 1,
                                    _age_key(x[0], batches)))
        for it, s in singles[:3]:
            opt = _make_option("single", [_pick(it, batches, wh_names, required, s)],
                               required, batches)
            if opt:
                options.append(opt)

        # Case 2 / general: combinations.
        opt = _min_waste(sources, required, batches, wh_names, "min_waste")
        if opt:
            options.append(opt)
        opt = _greedy(sources, required, batches, wh_names, "old_first")
        if opt:
            options.append(opt)

        # same-batch combination: oldest batch that can fulfil on its own.
        by_batch: dict[int, list] = {}
        for it, s in sources:
            by_batch.setdefault(it.batch_id, []).append((it, s))
        batch_order = sorted(
            by_batch.keys(),
            key=lambda bid: _ordinal(batches[bid].batch_date) if bid in batches else 10 ** 9)
        for bid in batch_order:
            grp = by_batch[bid]
            if sum(s for _, s in grp) >= required - EPS:
                opt = _min_waste(grp, required, batches, wh_names, "same_batch")
                if opt:
                    options.append(opt)
                break

    # de-duplicate by pick signature
    seen = set()
    unique = []
    for o in options:
        sig = o["_picks_sig"]
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(o)

    # rank by spec priority
    unique.sort(key=lambda o: (
        0 if o["fulfilled"] else 1,        # 1. fulfil
        o["total_wastage"],                # 2. minimum wastage
        o["_oldest"],                      # 3. old stock first
        0 if o["same_batch"] else 1,       # 4. same batch
        0 if o["same_warehouse"] else 1,   # 5. same warehouse
        len(o["picks"]),                   # 6. fewer pieces / mixed only when needed
    ))

    for o in unique:
        o.pop("_oldest", None)
        o.pop("_picks_sig", None)

    return {
        "product_id": product.id,
        "required_qty": required,
        "total_saleable": round(total_saleable, 4),
        "can_fulfill": total_saleable >= required - EPS,
        "options": unique[:max_options],
    }
