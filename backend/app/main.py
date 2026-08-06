import logging

from app.config import settings
from app.models.api import APIResponse, ErrorDetail
from app.routers import agent, analytics, artifacts, health
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app.main")

app = FastAPI(
    title="Exaqube Discord Analytics API",
    description="Postgres-backed FastAPI service and LangChain AI Agent with Plugin Architecture.",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(health.router)
app.include_router(analytics.router)
app.include_router(artifacts.router)
app.include_router(agent.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Standardized Error Envelope for all unhandled exceptions.
    Prevents 500 stack traces from being exposed on the wire.
    """
    logger.error(f"Unhandled Exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse(
            success=False,
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An internal server error occurred. Please check server logs.",
                details={"path": request.url.path}
            )
        ).model_dump()
    )


@app.on_event("startup")
async def on_startup():
    logger.info("Initializing Exaqube Discord Analytics Platform API...")
    # Discover plugins on startup
    from app.agent.registry import PluginRegistry
    plugins = PluginRegistry.discover_plugins()
    logger.info(f"Loaded {len(plugins)} agent plugins: {list(plugins.keys())}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
