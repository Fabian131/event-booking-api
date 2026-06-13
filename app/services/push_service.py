import httpx
import logging
from itertools import islice

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
EXPO_PUSH_RECEIPTS_URL = "https://exp.host/--/api/v2/push/getReceipts"
EXPO_CHUNK_SIZE = 100


def _chunk(iterable, size: int):
    """Split an iterable into chunks of at most `size` items."""
    it = iter(iterable)
    while True:
        batch = list(islice(it, size))
        if not batch:
            break
        yield batch


async def send_expo_push_notifications(
    messages: list[dict],
) -> list[dict]:
    """
    Send push notifications via the Expo Push HTTP API.

    Each message in `messages` must be a dict with at least the `to` key
    (an ExponentPushToken). Returns the list of raw ticket objects returned
    by Expo (one per message).

    Expo accepts at most 100 messages per request; this function batches
    automatically.
    """
    all_tickets: list[dict] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for batch in _chunk(messages, EXPO_CHUNK_SIZE):
            try:
                response = await client.post(
                    EXPO_PUSH_URL,
                    json=batch,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip, deflate",
                    },
                )
                response.raise_for_status()
                data = response.json()
                tickets = data.get("data", [])
                all_tickets.extend(tickets)
                logger.info(
                    "Expo push batch sent: %d messages, %d tickets returned",
                    len(batch),
                    len(tickets),
                )
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Expo push HTTP error %s: %s",
                    exc.response.status_code,
                    exc.response.text,
                )
            except Exception as exc:
                logger.error("Expo push unexpected error: %s", exc)

    return all_tickets


def build_event_reminder_messages(
    tokens: list[str],
    event_title: str,
    event_id: str,
    reservation_id: str,
) -> list[dict]:
    """Build the Expo push payload for an event reminder."""
    return [
        {
            "to": token,
            "sound": "default",
            "title": "¡Tu evento está por comenzar!",
            "body": f"El evento '{event_title}' inicia en menos de una hora.",
            "data": {
                "type": "event_reminder",
                "eventId": event_id,
                "reservationId": reservation_id,
            },
        }
        for token in tokens
    ]
