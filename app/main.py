from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .routes import router
from .database import create_db_and_tables
from .logger import logger
from .utils import get_current_semester


@asynccontextmanager
async def lifespan(app: FastAPI):
    default_semester = get_current_semester()
    if not default_semester:
        logger.critical("Failed to fetch current semester. Exiting.")
        exit(1)
    logger.info(f"Current Semester: {default_semester}")
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan, docs_url="/api-docs")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


Instrumentator().instrument(app).expose(app)
