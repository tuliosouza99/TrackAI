"""FastAPI application for TrackAI."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from trackai.db.connection import init_db

STATIC_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "static"

# Initialize database on startup
init_db()

app = FastAPI(
    title="TrackAI",
    description="Lightweight experiment tracker for deep learning",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins since we're serving the frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and register routers
from trackai.api.routes import projects, runs, metrics, mcp, views

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["mcp"])
app.include_router(views.router, prefix="/api/views", tags=["views"])


# Serve frontend static files if the build output exists
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the frontend SPA - return index.html for all non-API routes."""
        file_path = STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("trackai.api.main:app", host="0.0.0.0", port=8000, reload=True)
