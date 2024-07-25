from sqlmodel import SQLModel, create_engine, Session
from .config import settings
from .logger import logger

engine = create_engine(str(settings.postgres_dsn))


def create_db_and_tables():
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database and tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database and tables: {str(e)}")
        raise


def get_session():
    with Session(engine) as session:
        yield session
