#!/usr/bin/env python3
"""Test database connection"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import asyncio
from sqlalchemy import text
from src.config import settings
from src.database.core import engine, get_db
from sqlalchemy.orm import Session


async def test_connection():
    """Test database connection and print info"""
    # Parse the database URL safely
    from urllib.parse import urlparse
    parsed = urlparse(settings.database_url)
    print(f"🔍 Testing connection to: {parsed.hostname}:{parsed.port}/{parsed.path.lstrip('/')}")
    
    try:
        # Test raw connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL!")
            print(f"📊 Database version: {version}")
            
            # Test current database
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"📁 Current database: {db_name}")
            
            # List tables
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            
            if tables:
                print(f"\n📋 Existing tables ({len(tables)}):")
                for table in tables:
                    print(f"  - {table}")
            else:
                print("\n⚠️  No tables found. Run migrations with: uv run alembic upgrade head")
                
    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}: {e}")
        print("\n💡 Check your .env file has correct DATABASE_URL")
        print("   Format: postgresql://user:password@host:port/database")
        return False
    
    return True


if __name__ == "__main__":
    asyncio.run(test_connection())