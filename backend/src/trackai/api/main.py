"""FastAPI application for TrackAI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from trackai.db.connection import init_db

# Initialize database on startup
init_db()

app = FastAPI(
    title="TrackAI",
    description="Lightweight experiment tracker for deep learning",
    version="0.1.0",
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "TrackAI",
        "version": "0.1.0",
        "description": "Lightweight experiment tracker for deep learning",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and register routers
from trackai.api.routes import projects, runs, metrics, mcp

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["mcp"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("trackai.api.main:app", host="0.0.0.0", port=8000, reload=True)
