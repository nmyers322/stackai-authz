from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.authz.exceptions import AuthorizationError
from src.exceptions import Conflict, NotFound, Unauthenticated


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Unauthenticated)
    async def unauthenticated_handler(
        request: Request, exc: Unauthenticated
    ) -> JSONResponse:
        _ = (request, exc)
        return JSONResponse(status_code=401, content={"error": "unauthenticated"})

    @app.exception_handler(AuthorizationError)
    async def forbidden_handler(
        request: Request, exc: AuthorizationError
    ) -> JSONResponse:
        _ = request
        return JSONResponse(
            status_code=403,
            content={"error": "forbidden", "reason": exc.reason.value},
        )

    @app.exception_handler(NotFound)
    async def not_found_handler(request: Request, exc: NotFound) -> JSONResponse:
        _ = (request, exc)
        return JSONResponse(status_code=404, content={"error": "not_found"})

    @app.exception_handler(Conflict)
    async def conflict_handler(request: Request, exc: Conflict) -> JSONResponse:
        _ = (request, exc)
        return JSONResponse(status_code=409, content={"error": "conflict"})
