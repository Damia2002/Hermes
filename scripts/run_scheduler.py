"""APScheduler-based background job runner for monitoring workflows."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update

from app.config import get_settings
from app.database import AsyncSessionLocal, MonitorRule, MonitorSnapshot, init_db
from app.flows.monitoring_flow import run_monitoring_flow
from app.observability.logging import configure_logging, get_logger

configure_logging()
settings = get_settings()
logger = get_logger(__name__)


async def execute_monitor(rule_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(MonitorRule).where(MonitorRule.id == rule_id, MonitorRule.is_active == True))
        rule = result.scalar_one_or_none()
        if not rule:
            return

        prev_result = await db.execute(
            select(MonitorSnapshot)
            .where(MonitorSnapshot.rule_id == rule_id)
            .order_by(MonitorSnapshot.created_at.desc())
            .limit(1)
        )
        prev_snap = prev_result.scalar_one_or_none()
        prev_snapshot = {"doc_ids": prev_snap.doc_ids} if prev_snap else None

        try:
            report = await run_monitoring_flow(
                rule={"id": rule.id, "query": rule.query, "source_types": rule.source_types},
                previous_snapshot=prev_snapshot,
            )

            snap = MonitorSnapshot(
                rule_id=rule_id,
                doc_ids=[],
                summary=report["summary"],
                change_type=report["change_type"],
            )
            db.add(snap)

            await db.execute(
                update(MonitorRule)
                .where(MonitorRule.id == rule_id)
                .values(last_run_at=__import__("datetime").datetime.utcnow())
            )
            await db.commit()

            if report["material_change"]:
                logger.info("monitor_alert", rule_id=rule_id, change_type=report["change_type"])
        except Exception as exc:
            logger.error("monitor_run_failed", rule_id=rule_id, error=str(exc))


async def load_and_schedule(scheduler: AsyncIOScheduler) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(MonitorRule).where(MonitorRule.is_active == True))
        rules = result.scalars().all()

    for rule in rules:
        try:
            parts = rule.schedule_cron.split()
            if len(parts) == 5:
                minute, hour, day, month, dow = parts
                trigger = CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=dow)
                scheduler.add_job(execute_monitor, trigger=trigger, args=[rule.id], id=f"monitor_{rule.id}", replace_existing=True)
                logger.info("monitor_scheduled", rule_id=rule.id, cron=rule.schedule_cron)
        except Exception as exc:
            logger.warning("monitor_schedule_failed", rule_id=rule.id, error=str(exc))


async def main() -> None:
    await init_db()
    scheduler = AsyncIOScheduler()
    await load_and_schedule(scheduler)
    scheduler.start()
    logger.info("scheduler_started")

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("scheduler_stopped")


if __name__ == "__main__":
    asyncio.run(main())
