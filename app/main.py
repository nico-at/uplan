import requests_cache
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .routes import router
from .database import create_db_and_tables
from .logger import logger
from .utils import get_current_semester
from .limiter import limiter
from .config import settings


# Set up global caching with requests-cache using Redis
requests_cache.install_cache(
    backend='redis',
    host=settings.redis_host,
    port=settings.redis_port,
    expire_after=3600
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    default_semester = get_current_semester()
    if not default_semester:
        logger.critical("Failed to fetch current semester. Exiting.")
        exit(1)
    logger.info(f"Current Semester: {default_semester}")
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan, docs_url='/api-docs')

app.mount("/static", StaticFiles(directory="static"), name="static")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(router)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all incoming requests and their processing time."""
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds() * 1000
    logger.info(
        f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Process Time: {process_time:.2f}ms"
    )
    return response
