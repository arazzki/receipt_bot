import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from config import DATABASE_URL, SQLITE_FALLBACK_URL, DB_NAME, DB_HOST, DB_USER, DB_PASSWORD, DB_PORT
from database.models import Base

logger = logging.getLogger(__name__)

def get_engine(db_url: str = DATABASE_URL):
    """Create SQLAlchemy engine with retry/fallback logic."""
    try:
        if db_url.startswith("mysql"):
            # Check if database exists, create if not
            try:
                import pymysql
                conn = pymysql.connect(
                    host=DB_HOST,
                    port=int(DB_PORT),
                    user=DB_USER,
                    password=DB_PASSWORD,
                    connect_timeout=2
                )
                cursor = conn.cursor()
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                conn.commit()
                cursor.close()
                conn.close()
                logger.info(f"MariaDB database '{DB_NAME}' verified/created.")
            except Exception as e:
                logger.warning(f"Could not auto-create MariaDB database '{DB_NAME}': {e}")

            engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to MariaDB server.")
            return engine
    except Exception as e:
        logger.warning(f"Failed to connect to MariaDB at {db_url}: {e}. Falling back to SQLite.")

    # Fallback to SQLite
    sqlite_engine = create_engine(
        SQLITE_FALLBACK_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
    logger.info(f"Using SQLite engine at {SQLITE_FALLBACK_URL}")
    return sqlite_engine

engine = get_engine()
SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
ScopedSession = scoped_session(SessionFactory)

def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")

def get_db_session():
    """Get a new database session."""
    return SessionFactory()
