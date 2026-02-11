from .profile import router as profile_router
from .matching import router as matching_router
from .payments import router as payments_router

__all__ = ["profile_router", "matching_router", "payments_router"]
