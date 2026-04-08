"""
backend/database/setup_vector.py – Enable Vector & AI Extensions on AlloyDB.

This script should be run after 'upgrade_alloydb.sh' has enabled the 
google_ml_integration flag at the instance level.
"""
import asyncio
import logging
from sqlalchemy import text
from backend.database.connection import get_db, AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_extensions():
    logger.info("🛠️  Starting AlloyDB Vector/AI extensions setup...")
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Enable pgvector
            logger.info("🔹 Enabling 'vector' extension...")
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
            # 2. Enable Google ML Integration
            logger.info("🔹 Enabling 'google_ml_integration' extension...")
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS google_ml_integration;"))
            
            # 3. Grant permissions to the service account (assumed current user)
            # This is often needed if the proxy user isn't the owner
            logger.info("🔹 Granting schema permissions...")
            await session.execute(text("GRANT USAGE ON SCHEMA google_ml_integration TO public;"))
            await session.execute(text("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA google_ml_integration TO public;"))
            
            await session.commit()
            logger.info("✅ Extensions and permissions configured successfully!")
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(setup_extensions())
