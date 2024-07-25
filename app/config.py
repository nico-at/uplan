from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn

class Settings(BaseSettings):
    sqlite_url: str

    feed_url_template: str
    user_agent: str

    url_current_semester: str
    url_course_template: str
    url_ics_template: str

    regex_current_semester: str
    regex_course_id: str
    regex_course_id_with_group: str

    default_group: int
    default_feed_id_length: int
    max_courses_per_feed: int

    redis_host: str
    redis_port: int

    redis_dsn: RedisDsn
    postgres_dsn: PostgresDsn

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

settings = Settings()
