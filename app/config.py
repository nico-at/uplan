from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn, Field, computed_field


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

    # Rate limiting settings
    rate_limit_window: int
    rate_limit_requests: int

    # Redis settings
    redis_host: str
    redis_port: int
    redis_dsn: RedisDsn

    # PostgreSQL settings
    postgres_host: str = Field("localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(5432, env="POSTGRES_PORT")
    postgres_db: str = Field(..., env="POSTGRES_DB")
    postgres_user: str = Field(..., env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")

    @computed_field
    def postgres_dsn(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            path=self.postgres_db,
        )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
