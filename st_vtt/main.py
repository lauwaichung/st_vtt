"""FastAPI application factory."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from . import service
from .config import Config, load_config
from .content import load_content
from .db import Database
from .ws import Hub, websocket_endpoint

log = logging.getLogger("st_vtt")


def create_app(config: Config | None = None) -> FastAPI:
    if config is None:
        config = load_config(os.environ.get("ST_VTT_CONFIG", "config.json"))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    pack = load_content(config.content_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        app.state.db.close()

    app = FastAPI(title="Shared Table", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)
    app.state.config = config
    app.state.pack = pack
    app.state.pack_json = pack.model_dump(mode="json", by_alias=True)
    app.state.db = Database(config.database_path)
    app.state.hub = Hub()
    service.autocreate_shared(app)

    app.include_router(api_router)
    app.add_api_websocket_route("/ws", websocket_endpoint)

    static = config.static_path
    index = static / "index.html"
    if index.exists():
        app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            candidate = static / path
            if path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index)

    else:
        log.warning("frontend build not found at %s (run `npm run build` in frontend/)", static)

        @app.get("/", include_in_schema=False)
        def no_frontend() -> JSONResponse:
            return JSONResponse({"error": f"frontend not built; expected {index}. Run `npm run build` in frontend/."}, status_code=503)

    log.info("loaded content pack %r (%d playbooks) from %s", pack.pack.name, len(pack.playbooks), config.content_path)
    log.info("database: %s", config.database_path)
    return app
