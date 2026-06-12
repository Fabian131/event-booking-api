"""Send push notifications via Expo Push API v2."""
import json
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class ExpoPushService:
    """Sends push notifications to Expo Go / dev client apps."""

    @staticmethod
    async def send(to: str, title: str, body: str, data: dict | None = None) -> bool:
        if not to:
            return False

        payload = {
            "to": to,
            "title": title,
            "body": body,
            "sound": "default",
            "priority": "high",
        }
        if data:
            payload["data"] = data

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if settings.EXPO_ACCESS_TOKEN:
            headers["Authorization"] = f"Bearer {settings.EXPO_ACCESS_TOKEN}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(EXPO_PUSH_URL, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                ticket = result.get("data", {}).get("id") if "data" in result else None
                return ticket is not None
        except httpx.HTTPStatusError as e:
            logger.warning("Expo push HTTP %s for token %s...: %s", e.response.status_code, to[:12], e.response.text[:200])
            return False
        except httpx.RequestError as e:
            logger.error("Expo push network error for token %s...: %s", to[:12], e)
            return False
        except Exception:
            logger.exception("Unexpected Expo push error for token %s...", to[:12])
            return False


expo_push_service = ExpoPushService()
