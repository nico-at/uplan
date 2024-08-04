import re
import requests

from typing import Optional
from sqlmodel import Session, select
from icalendar import Calendar

from .models import Feed, FeedResponse
from .config import settings
from .utils import (
    get_current_semester,
    find_or_create_course,
    find_or_create_feed,
    request_limited,
)
from .logger import logger


async def create_feed_service(
    courses: str, semester: Optional[str], session: Session, remote_address: str
) -> FeedResponse:
    """Generate a feed for the given courses."""
    logger.info(f"Generating feed for courses: {courses}, semester: {semester}")
    course_ids = courses.split(",")
    if not course_ids:
        raise ValueError("No courses provided")

    if len(course_ids) > settings.max_courses_per_feed:
        raise ValueError(
            f"Too many courses provided ({len(course_ids)} > {settings.max_courses_per_feed})"
        )

    if not semester:
        semester = get_current_semester()
        if not semester:
            raise ValueError("Failed to fetch current semester from u:find API")

    processed_courses = []
    for course_id in course_ids:
        path, group = None, None
        if re.fullmatch(settings.regex_course_id, course_id):
            path, group = course_id, settings.default_group
        elif re.fullmatch(settings.regex_course_id_with_group, course_id):
            path, group = course_id.split("-")
        else:
            raise ValueError(f"Invalid course ID format: {course_id}")

        course = find_or_create_course(
            session,
            path=path,
            group=int(group),
            semester=semester,
            remote_address=remote_address,
        )
        processed_courses.append(course)

    feed = find_or_create_feed(session, courses=processed_courses)
    feed_url = settings.url_feed_template.format(path=feed.path)
    logger.info(f"Successfully generated feed with URL: {feed_url}")

    return FeedResponse(
        url=feed_url,
        courses=[
            f"{course.path}-{course.group} {course.course_type} {course.name} ({course.semester})"
            for course in processed_courses
        ],
    )


async def get_combined_feed_service(
    feed_id: str, session: Session, remote_address: str
) -> bytes:
    """Retrieve the combined feed for the given feed ID."""
    logger.info(f"Retrieving combined feed for ID: {feed_id}")
    feed = session.exec(select(Feed).where(Feed.path == feed_id)).first()
    if not feed:
        raise ValueError("Feed not found")

    combined_calendar = Calendar()

    for course in feed.courses:
        url = settings.url_ics_template.format(
            id=course.path, semester=course.semester, group=course.group
        )
        try:
            response = request_limited(url=url, remote_address=remote_address)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Error fetching course {course.path}: {str(e)}")
            raise ValueError(f"Error fetching course {course.path}")

        calendar = Calendar.from_ical(response.content)
        for component in calendar.walk():
            if component.name == "VEVENT":
                combined_calendar.add_component(component)

    logger.info(f"Successfully generated combined feed for ID: {feed_id}")
    return combined_calendar.to_ical()
