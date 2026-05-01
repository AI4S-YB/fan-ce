from fastapi import APIRouter
from starlette.types import Scope, Receive, Send

from .api.database import databases_router
from .api.database_files import databases_file_router
from .api.database_meta import databases_meta_router
from .api.databases_file_api import databases_file_router as databases_file_api_router
from .api.actions import action_router


DEPRECATION_HEADERS = {
    b"deprecation": b"true",
    b"sunset": b"Sat, 01 Aug 2026 00:00:00 GMT",
    b"link": b'</api/v1/dataset/>; rel="successor-version"',
}


class DeprecationAPIRouter(APIRouter):
    """APIRouter subclass that adds deprecation headers to every response."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_with_deprecation(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers.update(DEPRECATION_HEADERS)
                message["headers"] = list(headers.items())
            await send(message)

        await super().__call__(scope, receive, send_with_deprecation)


# Legacy compatibility router.
# New dataset lifecycle, asset, lineage and public-query features should be added under apps.datasets only.
app_databases_router = DeprecationAPIRouter()
app_databases_router.include_router(databases_router, prefix='/database')
app_databases_router.include_router(action_router, prefix='/database')
app_databases_router.include_router(databases_file_router, prefix='/database')
app_databases_router.include_router(databases_file_api_router, prefix='/database-file')
app_databases_router.include_router(databases_meta_router, prefix='/database/meta')
