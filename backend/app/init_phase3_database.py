"""
Phase 3 Database Initialization
Creates tables for advanced session management and analytics
"""

import asyncio
import asyncpg
import logging
import os

logger = logging.getLogger(__name__)

async def init_phase3_database():
    """Initialize Phase 3 database tables"""
    
    # Database connection parameters
    db_config = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DB", "docqa"),
        "user": os.getenv("POSTGRES_USER", "docqa_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "docqa_password")
    }
    
    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(**db_config)
        logger.info("✅ Connected to PostgreSQL")
        
        # Create sessions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'active',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                document_count INTEGER NOT NULL DEFAULT 0,
                total_chunks INTEGER NOT NULL DEFAULT 0,
                last_activity TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                user_id VARCHAR(255),
                tags JSONB DEFAULT '[]'::jsonb
            );
        """)
        logger.info("✅ Created sessions table")
        
        # Create documents table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id VARCHAR(255) PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                filename VARCHAR(255) NOT NULL,
                uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                chunk_count INTEGER NOT NULL DEFAULT 0,
                size_bytes BIGINT NOT NULL,
                metadata JSONB DEFAULT '{}'::jsonb
            );
        """)
        logger.info("✅ Created documents table")
        
        # Create indexes for better performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
            CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
            CREATE INDEX IF NOT EXISTS idx_documents_session_id ON documents(session_id);
            CREATE INDEX IF NOT EXISTS idx_documents_uploaded_at ON documents(uploaded_at);
        """)
        logger.info("✅ Created database indexes")
        
        # Create performance monitoring table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                endpoint VARCHAR(255) NOT NULL,
                response_time_ms FLOAT NOT NULL,
                memory_usage_mb FLOAT NOT NULL,
                cpu_usage_percent FLOAT NOT NULL,
                active_connections INTEGER NOT NULL,
                cache_hit_rate FLOAT NOT NULL,
                error_count INTEGER NOT NULL DEFAULT 0
            );
        """)
        logger.info("✅ Created performance_metrics table")
        
        # Create security events table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                event_type VARCHAR(255) NOT NULL,
                source_ip INET NOT NULL,
                user_agent TEXT,
                endpoint VARCHAR(255),
                severity VARCHAR(50) NOT NULL,
                details JSONB DEFAULT '{}'::jsonb
            );
        """)
        logger.info("✅ Created security_events table")
        
        # Create indexes for monitoring tables
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics(timestamp);
            CREATE INDEX IF NOT EXISTS idx_performance_endpoint ON performance_metrics(endpoint);
            CREATE INDEX IF NOT EXISTS idx_security_timestamp ON security_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_security_source_ip ON security_events(source_ip);
            CREATE INDEX IF NOT EXISTS idx_security_severity ON security_events(severity);
        """)
        logger.info("✅ Created monitoring indexes")
        
        await conn.close()
        logger.info("🎉 Phase 3 database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(init_phase3_database())
