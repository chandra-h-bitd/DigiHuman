"""
Database initialization script for enhanced session management
"""

import os
import asyncio
import asyncpg
import logging

logger = logging.getLogger(__name__)

async def init_database():
    """Initialize the database with enhanced schema"""
    try:
        # Database connection parameters
        postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        postgres_port = int(os.getenv("POSTGRES_PORT", 5432))
        postgres_db = os.getenv("POSTGRES_DB", "docqa")
        postgres_user = os.getenv("POSTGRES_USER", "docqa_user")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "docqa_password")
        
        # Connect to PostgreSQL
        conn = await asyncpg.connect(
            host=postgres_host,
            port=postgres_port,
            database=postgres_db,
            user=postgres_user,
            password=postgres_password
        )
        
        logger.info("Connected to PostgreSQL database")
        
        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(__file__), "database_schema.sql")
        
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Execute schema
            await conn.execute(schema_sql)
            logger.info("Database schema initialized successfully")
        else:
            logger.warning(f"Schema file not found at {schema_path}")
        
        await conn.close()
        logger.info("Database initialization completed")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(init_database())
