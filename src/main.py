from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import ConnectionPool

from src.authn.jwks import JwksTokenVerifier, TokenVerifier, UnconfiguredVerifier
from src.authz.postgres import PostgresMembershipStore
from src.authz.store import AppStore
from src.config import settings
from src.debug.router import router as debug_router
from src.http_errors import register_exception_handlers
from src.orgs.router import orgs_root_router, user_orgs_router
from src.orgs.router import router as orgs_router
from src.seed import membership_store
from src.teams.router import router as teams_router
from src.workflows.router import router as workflows_router


def create_app(
    *,
    store: AppStore | None = None,
    verifier: TokenVerifier | None = None,
    debug: bool | None = None,
) -> FastAPI:
    debug_enabled = settings.DEBUG if debug is None else debug

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        pool: ConnectionPool | None = None
        if store is not None:
            application.state.store = store
            application.state.pool = None
        elif settings.DATABASE_URL:
            pool = ConnectionPool(
                conninfo=settings.DATABASE_URL,
                min_size=1,
                max_size=4,
                kwargs={"prepare_threshold": None},
                open=True,
            )
            application.state.store = PostgresMembershipStore(pool)
            application.state.pool = pool
        else:
            application.state.store = membership_store()
            application.state.pool = None
        yield
        if pool is not None:
            pool.close()

    application = FastAPI(title=settings.NAME, lifespan=lifespan)
    application.state.debug = debug_enabled
    application.state.pool = None
    if store is not None:
        application.state.store = store
    if verifier is not None:
        application.state.verifier = verifier
    elif settings.SUPABASE_URL:
        application.state.verifier = JwksTokenVerifier.from_supabase_url(
            settings.SUPABASE_URL,
            audience=settings.JWT_AUDIENCE,
        )
    else:
        application.state.verifier = UnconfiguredVerifier()
    register_exception_handlers(application)
    application.include_router(orgs_root_router)
    application.include_router(teams_router)
    application.include_router(orgs_router)
    application.include_router(user_orgs_router)
    application.include_router(workflows_router)
    if debug_enabled:
        application.include_router(debug_router)
    return application


app = create_app()
