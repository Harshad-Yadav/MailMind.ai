from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from backend.api.routes import router
from backend.core.config import get_settings
from backend.db.sqlite import initialize_database

settings = get_settings()
app = FastAPI(title=settings.project_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup() -> None:
    initialize_database()


ui_dist = Path(settings.ui_dist_path)
if ui_dist.exists():
    app.mount("/", StaticFiles(directory=ui_dist, html=True), name="ui")

    @app.get("/{full_path:path}")
    async def serve_ui(full_path: str):
        index_file = ui_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "UI build not found."}
