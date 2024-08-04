import re
import random
import string
import requests
import time
import redis

from xml.etree import ElementTree
from sqlmodel import Session, select
from typing import List, Optional
from functools import wraps
from requests_cache import CachedSession
from fastapi import HTTPException

from .config import settings
from .logger import logger
from .models import Course, Feed

cached_session = CachedSession(
    "cache",
    backend="redis",
    host=settings.redis_host,
    port=settings.redis_port,
    expire_after=3600,
)

redis_client = redis.Redis(host=settings.redis_host, port=settings.redis_port)


def rate_limit(func):
    @wraps(func)
    def wrapper(url: str | bytes, remote_address: str, *args, **kwargs):
        if not remote_address:
            return func(url, remote_address, *args, **kwargs)
        
        # Check rate limit
        rate_key = f"rate:{remote_address}"
        current_time = int(time.time())
        window_start = current_time - settings.rate_limit_window

        # Remove old entries
        redis_client.zremrangebyscore(rate_key, 0, window_start)

        # Count requests in the current window
        request_count = redis_client.zcard(rate_key)
        if request_count >= settings.rate_limit_requests:
            raise HTTPException(status_code=429, detail="Too Many Requests")

        # Make the request
        response = func(url, remote_address, *args, **kwargs)

        # If the response wasn't from cache, add to rate limit
        if not response.from_cache:
            # Add current request to the sorted set
            redis_client.zadd(rate_key, {str(current_time): current_time})
            # Set TTL for the rate limit key (twice the window to be safe)
            redis_client.expire(rate_key, settings.rate_limit_window * 2)
        return response

    return wrapper


@rate_limit
def request_limited(url: str | bytes, remote_address: str) -> requests.Response:
    """Limit the number of requests to a given URL for a given remote address."""
    print(f"Requesting {url} from {remote_address}")
    response = cached_session.get(url, headers={"User-Agent": settings.user_agent})
    response.raise_for_status()
    return response


def generate_unique_path(session: Session) -> str:
    """Generate a unique path for a new feed."""
    for _ in range(100):  # Limit attempts to prevent infinite loop
        path = "".join(
            random.choice(string.ascii_lowercase + string.digits)
            for _ in range(settings.default_feed_id_length)
        )
        if not session.exec(select(Feed).where(Feed.path == path)).first():
            return path
    logger.error("Failed to generate a unique path after 100 attempts")
    raise RuntimeError(
        "Unable to generate a unique path, change DEFAULT_FEED_ID_LENGTH"
    )


def get_current_semester(remote_address: Optional[str] = None) -> Optional[str]:
    """Fetch the current semester from the university's API."""
    try:
        response = request_limited(
            url=settings.url_current_semester, remote_address=remote_address
        )
        response.raise_for_status()

        semester = response.text.strip()
        if not re.fullmatch(settings.regex_current_semester, semester):
            logger.error(f"Invalid semester format: {semester}")
            return None

        logger.info(f"Successfully fetched current semester: {semester}")
        return semester
    except requests.RequestException as e:
        logger.error(f"Error fetching current semester: {str(e)}")
        return None


def validate_course_path(
    path: str,
    semester: str,
    group: Optional[int] = None,
    remote_address: Optional[str] = None,
) -> Course:
    """
    Validates if a course exists and if the specified group is valid.
    Returns a Course object.
    """
    try:
        response = request_limited(
            url=settings.url_course_template.format(id=path, semester=semester),
            remote_address=remote_address,
        )
        response.raise_for_status()

        namespaces = {"xml": "http://www.w3.org/XML/1998/namespace"}
        root = ElementTree.fromstring(response.content)

        # Extract longname (preferring German, falling back to English)
        longname_de = root.find(".//longname[@xml:lang='de']", namespaces)
        longname_en = root.find(".//longname[@xml:lang='en']", namespaces)

        # Extract longname (preferring German, falling back to English)
        longname = longname_de.text if longname_de is not None else longname_en.text

        if not longname:
            raise Exception("no name of course found")

        # Extract type
        type_element = root.find(".//type")
        course_type = type_element.text if type_element is not None else ""

        if not course_type:
            raise Exception("no type of course found (VO, PUE, ...)")

        groups = root.findall(".//group")

        group_id = f"{path}-{group}"
        if any(group_element.get("id") == group_id for group_element in groups):
            return Course(
                path=path,
                group=group,
                semester=semester,
                name=longname,
                course_type=course_type,
            )

        raise Exception(f"group {group} not found")
    except requests.RequestException:
        raise Exception("course not found")
    except ElementTree.ParseError:
        raise Exception("invalid response from API")


def find_or_create_course(
    session: Session, path: str, group: int, semester: str, remote_address: str
) -> Course:
    """Find an existing course or create a new one if it doesn't exist."""
    try:
        existing_course = session.exec(
            select(Course).where(
                Course.path == path, Course.group == group, Course.semester == semester
            )
        ).first()

        if existing_course:
            logger.info(f"Found existing course: {path}-{group} ({semester})")
            return existing_course

        new_course = validate_course_path(
            path=path, semester=semester, group=group, remote_address=remote_address
        )

        session.add(new_course)
        session.commit()
        session.refresh(new_course)
        logger.info(f"Created new course: {path}-{group} ({semester})")
        return new_course

    except Exception as e:
        logger.error(f"Error processing course {path}-{group} ({semester}): {str(e)}")
        session.rollback()
        raise ValueError(
            f"Error processing course {path}-{group} ({semester}): {str(e)}"
        )


def find_or_create_feed(session: Session, courses: List[Course]) -> Feed:
    """Find an existing feed with the same courses or create a new one."""
    try:
        course_ids = {course.id for course in courses}

        for feed in session.exec(select(Feed)).all():
            if {fc.id for fc in feed.courses} == course_ids:
                logger.info(f"Found existing feed with path: {feed.path}")
                return feed

        new_feed = Feed(path=generate_unique_path(session), courses=courses)
        session.add(new_feed)
        session.commit()
        session.refresh(new_feed)
        logger.info(f"Created new feed with path: {new_feed.path}")
        return new_feed

    except Exception as e:
        logger.error(f"Error finding or creating feed: {str(e)}")
        session.rollback()
        raise ValueError(f"Error processing feed: {str(e)}")
