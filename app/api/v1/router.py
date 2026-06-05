from fastapi import APIRouter
from app.api.v1 import auth, users, events, reservations, notifications

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(events.router)
router.include_router(reservations.router)
router.include_router(notifications.router)
