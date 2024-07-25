import re
import random
import string
import requests

from xml.etree import ElementTree
from sqlmodel import Session, select
from typing import List, Optional

from .config import settings
from .logger import logger
from .models import Course, Feed


def generate_unique_path(session: Session) -> str:
    """Generate a unique path for a new feed."""
    for _ in range(100):  # Limit attempts to prevent infinite loop
        path = "".join(
            random.choice(string.ascii_letters + string.digits)
            for _ in range(settings.default_feed_id_length)
        )
        if not session.exec(select(Feed).where(Feed.path == path)).first():
            return path
    logger.error("Failed to generate a unique path after 100 attempts")
    raise RuntimeError(
        "Unable to generate a unique path, change DEFAULT_FEED_ID_LENGTH"
    )


def get_current_semester() -> Optional[str]:
    """Fetch the current semester from the university's API."""
    try:
        response = requests.get(settings.url_current_semester, headers={"User-Agent": settings.user_agent})
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
    path: str, semester: str, group: Optional[int] = None
) -> Course:
    """
    Validates if a course exists and if the specified group is valid.
    Returns a Course object.
    """
    try:
        response = requests.get(
            settings.url_course_template.format(id=path, semester=semester), headers={"User-Agent": settings.user_agent}
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
    session: Session, path: str, group: int, semester: str
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

        new_course = validate_course_path(path=path, semester=semester, group=group)

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
