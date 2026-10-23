from fastapi import APIRouter

from app.api import health
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.contracts.router import router as contracts_router
from app.modules.parties.router import router as parties_router
from app.modules.properties.router import router as properties_router
from app.modules.users.router import router as users_router

API_PREFIX = "/api/v1"

api_router = APIRouter(prefix=API_PREFIX)
api_router.include_router(health.router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(audit_router)
api_router.include_router(parties_router)
api_router.include_router(properties_router)
api_router.include_router(contracts_router)
