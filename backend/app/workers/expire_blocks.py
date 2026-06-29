"""Background worker: auto-release expired stock blocks.

Runs a simple polling loop (default every 60s). For each APPROVED block whose
hold_until has passed, posts BLOCK_RELEASE ledger entries, restores stock_item
availability, and marks the block EXPIRED. Designed to be safe to run alongside
the API (all work is transactional).
"""
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import StockBlock, StockBlockItem, StockItem, StockLedger
from app.models.enums import BlockStatus, LedgerTxnType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sainext.worker")

POLL_SECONDS = 60


def release_expired_once() -> int:
    db = SessionLocal()
    released = 0
    try:
        now = datetime.now(timezone.utc)
        blocks = db.execute(
            select(StockBlock).where(
                StockBlock.status == BlockStatus.APPROVED,
                StockBlock.hold_until.is_not(None),
                StockBlock.hold_until < now,
            )
        ).scalars().all()
        for block in blocks:
            items = db.execute(
                select(StockBlockItem).where(StockBlockItem.block_id == block.id)
            ).scalars().all()
            # Blocks never reduced physical available_qty; they reduce *saleable*
            # while APPROVED (saleable = available - approved blocks). Expiring a
            # block just flips its status so it stops counting against saleable.
            # We post an informational BLOCK_RELEASE ledger row (available
            # unchanged) for the audit trail.
            for it in items:
                si = db.get(StockItem, it.stock_item_id)
                if si:
                    db.add(StockLedger(
                        product_id=si.product_id, warehouse_id=si.warehouse_id,
                        batch_id=si.batch_id, stock_item_id=si.id,
                        txn_type=LedgerTxnType.BLOCK_RELEASE, qty=it.qty,
                        before_qty=si.available_qty, after_qty=si.available_qty,
                        ref_type="block", ref_id=block.id,
                        remarks="Auto-release: block expired",
                    ))
            block.status = BlockStatus.EXPIRED
            released += 1
        db.commit()
        if released:
            logger.info("Auto-released %s expired block(s).", released)
    except Exception:
        db.rollback()
        logger.exception("Error releasing expired blocks")
    finally:
        db.close()
    return released


def main():
    logger.info("Expired-block worker started (poll=%ss).", POLL_SECONDS)
    while True:
        release_expired_once()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
