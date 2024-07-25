from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship


class FeedCourseLink(SQLModel, table=True):
    feed_id: Optional[int] = Field(
        default=None, foreign_key="feed.id", primary_key=True
    )
    course_id: Optional[int] = Field(
        default=None, foreign_key="course.id", primary_key=True
    )


class Feed(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    path: str = Field(index=True)
    courses: List["Course"] = Relationship(
        back_populates="feeds", link_model=FeedCourseLink
    )


class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    path: str = Field(index=True)
    semester: str
    group: int = Field(default=1)
    name: str
    course_type: str

    feeds: List[Feed] = Relationship(
        back_populates="courses", link_model=FeedCourseLink
    )


class FeedResponse(SQLModel):
    url: str
    courses: List[str]
