from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response, FileResponse
from sqlmodel import Session
from typing import Optional

from .database import get_session
from .services import create_feed_service, get_combined_feed_service
from .logger import logger
from .models import FeedResponse
from .limiter import limiter

router = APIRouter()


@router.get("/")
async def index():
    return FileResponse("static/index.html")


@router.get(
    "/create",
    summary="Generate ICS Feed",
    description="Generates an ICS feed for the specified courses.",
    response_model=FeedResponse,
)
@limiter.limit("5/minute")
async def create_feed(
    request: Request,
    courses: str,
    semester: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """
    Generates an ICS feed for the specified courses and optional semester.

    Args:
    - courses (str): A comma-separated list of course paths/IDs.
    - semester (Optional[str]): The semester code (e.g., "2024W").

    Returns:
    - JSONResponse: A JSON response containing the generated feed.
    """
    try:
        return create_feed_service(courses, semester, session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating feed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/ics/{id}",
    summary="Get Combined Feed",
    description="Retrieves a combined feed based on the specified ID.",
)
async def get_combined_feed(id: str, session: Session = Depends(get_session)):
    """
    Retrieves a combined feed based on the specified ID.

    Args:
    - id (str): The ID for the combined feed.

    Returns:
    - Response: An iCalendar (.ics) file containing the combined feed.
    """
    try:
        result = get_combined_feed_service(id, session)
        return Response(
            content=result,
            media_type="text/calendar",
            headers={"Content-Disposition": "attachment; filename=combined_feed.ics"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving combined feed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
