from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from src.debug import catalog as debug_catalog

router = APIRouter(prefix="/debug", tags=["debug"])
_PAGE = Path(__file__).parent / "static" / "index.html"


class DebugUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=200)


@router.get("")
@router.get("/")
async def debug_page() -> FileResponse:
    return FileResponse(_PAGE, media_type="text/html")


@router.get("/state")
async def debug_state(request: Request) -> dict[str, object]:
    store = request.app.state.store
    pool = getattr(request.app.state, "pool", None)
    snapshot = await run_in_threadpool(debug_catalog.snapshot, store, pool)
    snapshot["impersonation"] = "X-Debug-User"
    return snapshot


@router.post("/users", status_code=201)
async def debug_create_user(
    request: Request, body: DebugUserCreate
) -> dict[str, str]:
    store = request.app.state.store
    pool = getattr(request.app.state, "pool", None)
    return await run_in_threadpool(
        debug_catalog.create_user, store, pool, body.email.strip()
    )


@router.delete("/users/{user_id}", status_code=204)
async def debug_delete_user(request: Request, user_id: UUID) -> None:
    store = request.app.state.store
    pool = getattr(request.app.state, "pool", None)
    await run_in_threadpool(debug_catalog.delete_user, store, pool, user_id)
