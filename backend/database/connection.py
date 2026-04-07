"""
backend/database/connection.py – Async database engine and session management.

Supports three modes:
  1. AlloyDB via Connector (Cloud Run production) – uses asyncpg + IAM auth
  2. PostgreSQL direct (staging) – uses asyncpg
  3. SQLite (local dev / Cloud Shell) – uses aiosqlite

Set USE_SQLITE=true in env or .env for local dev without PostgreSQL.
Set ALLOYDB_INSTANCE for Cloud Run production with AlloyDB Connector.
"""
import asyncio
import logging
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import threading

logger = logging.getLogger(__name__)

# These are set at module level so they can be monkey-patched by conftest.py
# before the app starts.  The _create_default_engine() helper fills them in
# on first real use (production) or they are overridden in tests.
engine = None
AsyncSessionLocal = None

_initialised = False
_init_lock = threading.Lock()


def _create_default_engine():
    """Create the production engine on first use (lazy)."""
    global engine, AsyncSessionLocal, _initialised
    if _initialised:
        return
        
    with _init_lock:
        if _initialised:
            return

        try:
            from sqlalchemy.ext.asyncio import create_async_engine
            from backend.config import get_settings

            settings = get_settings()

            if settings.use_sqlite:
                # Local dev mode – no PostgreSQL needed
                DATABASE_URL = "sqlite+aiosqlite:///agentflow.db"
                logger.info("Using SQLite database (local dev mode)")
                engine = create_async_engine(
                    DATABASE_URL,
                    echo=False,
                    connect_args={"check_same_thread": False},
                )
            elif getattr(settings, "alloydb_instance", ""):
                # Cloud Run production – AlloyDB via Connector with IAM auth
                logger.info("Using AlloyDB via Connector (Cloud Run mode)")
                try:
                    from google.cloud.alloydb.connector import AsyncConnector

                    connector = AsyncConnector()

                    async def getconn():
                        return await connector.connect(
                            settings.alloydb_instance,
                            "asyncpg",
                            user=settings.db_user,
                            password=settings.db_password,
                            db=settings.db_name,
                            enable_iam_auth=getattr(settings, "alloydb_iam_auth", True),
                        )

                    engine = create_async_engine(
                        "postgresql+asyncpg://",
                        async_creator=getconn,
                        echo=False,
                        pool_size=5,       # Cloud Run has limited connections
                        max_overflow=10,
                        pool_pre_ping=True,  # Handle connection drops on scale-to-zero
                        pool_recycle=1800,   # Recycle connections every 30 min
                    )
                except ImportError:
                    logger.warning(
                        "google-cloud-alloydb-connector not installed, "
                        "falling back to direct PostgreSQL connection"
                    )
                    _create_direct_pg_engine(settings)
            else:
                # Direct PostgreSQL connection (staging / custom setup)
                _create_direct_pg_engine(settings)

            AsyncSessionLocal = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
            _initialised = True
        except Exception as e:
            logger.error("Failed to create database engine: %s", e)
            raise


def _create_direct_pg_engine(settings):
    """Create a direct PostgreSQL engine using URL.create() for secure credential handling."""
    global engine
    from sqlalchemy.ext.asyncio import create_async_engine

    # Use URL.create() to avoid credentials in string interpolation
    DATABASE_URL = URL.create(
        drivername="postgresql+asyncpg",
        username=settings.db_user,
        password=settings.db_password,
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )
    logger.info("Using PostgreSQL database (direct connection)")
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


def _ensure_engine():
    """Ensure the engine is initialised; called by public functions."""
    if not _initialised:
        _create_default_engine()


def get_session_factory():
    """Ensure engine is initialised and return the session factory."""
    _ensure_engine()
    return AsyncSessionLocal


async def init_db():
    """Create tables on startup (idempotent)."""
    _ensure_engine()
    from backend.database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified.")


async def close_db():
    """Dispose of the engine's connection pool."""
    if engine is not None:
        await engine.dispose()
        logger.info("Database connection pool closed.")


async def get_db():
    """FastAPI dependency – yields an AsyncSession, auto-commits on success."""
    _ensure_engine()
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
