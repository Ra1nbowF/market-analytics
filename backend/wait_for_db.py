import asyncio
import asyncpg
import os
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def wait_for_postgres(max_retries=30, retry_interval=2):
    """Wait for PostgreSQL to be ready"""
    db_url = os.getenv('DATABASE_URL')

    # Fallback for local development
    if not db_url:
        db_url = 'postgresql://admin:admin123@postgres:5432/market_analytics'

    # Railway uses DATABASE_URL with postgres:// prefix, we need postgresql://
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    # Log connection attempt (without password)
    from urllib.parse import urlparse
    parsed = urlparse(db_url)
    logger.info(f"Database host: {parsed.hostname}, port: {parsed.port}, db: {parsed.path.lstrip('/')}")

    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to PostgreSQL (attempt {attempt + 1}/{max_retries})...")
            conn = await asyncpg.connect(db_url)
            await conn.fetchval('SELECT 1')
            await conn.close()
            logger.info("PostgreSQL is ready!")
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL not ready yet: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_interval)

    logger.error("Failed to connect to PostgreSQL after maximum retries")
    return False

if __name__ == "__main__":
    asyncio.run(wait_for_postgres())