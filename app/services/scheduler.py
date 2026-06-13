"""
Event reminder push notification scheduler.

Runs every 5 minutes and sends Expo push notifications to all users
that have a CONFIRMED reservation for an event starting within the next
hour and whose reminder has not been sent yet.
"""
import logging
from datetime import datetime, timedelta, timezone, time, date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.domain.models import Reservation, Event
from app.repositories.user_device_token_repository import UserDeviceTokenRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.push_service import send_expo_push_notifications, build_event_reminder_messages

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def send_event_reminders() -> None:
    """
    Core job: finds reservations whose event starts within the next hour
    and fires push notifications + in-app notifications for each one.
    """
    now_utc = datetime.now(timezone.utc)
    window_end = now_utc + timedelta(hours=1)

    logger.info(
        "Reminder job running at %s — checking events starting before %s",
        now_utc.isoformat(),
        window_end.isoformat(),
    )

    async with AsyncSessionLocal() as db:
        try:
            # --- 1. Query pending reservations ---
            # Event stores date + start_time separately (Date + Time columns).
            # We fetch all CONFIRMED reservations for today and tomorrow
            # and filter in Python to combine date+time correctly.
            result = await db.execute(
                select(Reservation)
                .options(selectinload(Reservation.event))
                .where(
                    Reservation.status == "CONFIRMED",
                    Reservation.reminder_sent == False,
                )
            )
            all_reservations = result.scalars().all()

            pending = []
            for r in all_reservations:
                event = r.event
                if not event or not event.is_active:
                    continue
                # Combine event date + start_time into a timezone-aware UTC datetime
                event_start_naive = datetime.combine(event.date, event.start_time)
                # Treat stored times as UTC (consistent with the rest of the project)
                event_start = event_start_naive.replace(tzinfo=timezone.utc)
                if now_utc <= event_start <= window_end:
                    pending.append((r, event, event_start))

            if not pending:
                logger.debug("No pending reminders found.")
                return

            logger.info("Found %d reservation(s) to remind.", len(pending))

            # --- 2. Collect unique user_ids and fetch their active tokens ---
            user_ids = list({r.user_id for r, _, _ in pending})
            device_token_repo = UserDeviceTokenRepository(db)
            notification_repo = NotificationRepository(db)

            device_tokens = await device_token_repo.get_active_by_user_ids(user_ids)

            # Build a map: user_id -> list[token_string]
            tokens_by_user: dict = {}
            for dt in device_tokens:
                tokens_by_user.setdefault(dt.user_id, []).append(dt.token)

            # --- 3. Build messages and send ---
            all_messages = []
            reservation_ids_to_mark = []

            for reservation, event, _ in pending:
                user_tokens = tokens_by_user.get(reservation.user_id, [])
                if user_tokens:
                    messages = build_event_reminder_messages(
                        tokens=user_tokens,
                        event_title=event.title,
                        event_id=str(event.id),
                        reservation_id=str(reservation.id),
                    )
                    all_messages.extend(messages)

                # Always mark as sent and create in-app notification,
                # even if the user has no push token registered.
                reservation_ids_to_mark.append(reservation.id)

                # Create in-app notification record
                await notification_repo.create_notification(
                    user_id=reservation.user_id,
                    notification_type="event_reminder",
                    title="¡Tu evento está por comenzar!",
                    message=f"El evento '{event.title}' inicia en menos de una hora.",
                    reservation_id=reservation.id,
                    event_id=event.id,
                )

            # Send all push messages in bulk (batched internally)
            if all_messages:
                tickets = await send_expo_push_notifications(all_messages)
                logger.info(
                    "Push batch completed: %d messages sent, %d tickets received.",
                    len(all_messages),
                    len(tickets),
                )

                # --- 4. Deactivate tokens that Expo reports as invalid ---
                for ticket in tickets:
                    if ticket.get("status") == "error":
                        details = ticket.get("details", {})
                        if details.get("error") == "DeviceNotRegistered":
                            invalid_token = details.get("expoPushToken")
                            if invalid_token:
                                bad = await device_token_repo.get_by_token(invalid_token)
                                if bad:
                                    await device_token_repo.update(bad, is_active=False)
                                    logger.warning(
                                        "Deactivated invalid token: %s", invalid_token
                                    )

            # --- 5. Mark reservations as reminded ---
            for r, _, _ in pending:
                if r.id in reservation_ids_to_mark:
                    r.reminder_sent = True

            await db.commit()
            logger.info(
                "Marked %d reservation(s) as reminded.", len(reservation_ids_to_mark)
            )

        except Exception as exc:
            await db.rollback()
            logger.error("Reminder job failed: %s", exc, exc_info=True)


def start_scheduler() -> None:
    """Register the reminder job and start the APScheduler."""
    scheduler.add_job(
        send_event_reminders,
        trigger="interval",
        minutes=settings.REMINDER_CHECK_INTERVAL_MINUTES,
        id="event_reminder_job",
        name="Event Reminder Push Notifications",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )
    scheduler.start()
    logger.info(
        "Scheduler started — reminder job runs every %d minute(s).",
        settings.REMINDER_CHECK_INTERVAL_MINUTES,
    )


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
