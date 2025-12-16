#!/usr/bin/env python3
"""Test script to debug database connection issues."""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import get_database

async def test_db_connection():
    """Test basic database connectivity."""
    print(f"Database DSN: {get_database().dsn}")
    
    if not get_database().dsn:
        print("❌ No database URL configured")
        return False
        
    try:
        import asyncpg
        conn = await asyncpg.connect(get_database().dsn)
        
        # Test basic query
        result = await conn.fetchval("SELECT 1")
        print(f"✓ Database connection successful: {result}")
        
        # Check if table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'database_connections'
            )
        """)
        print(f"✓ database_connections table exists: {table_exists}")
        
        # Check table schema
        if table_exists:
            columns = await conn.fetch("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'database_connections' 
                ORDER BY ordinal_position
            """)
            print("Table schema:")
            for col in columns:
                print(f"  - {col['column_name']}: {col['data_type']}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def main():
    """Main test function."""
    success = await test_db_connection()
    
    if success:
        print("\n✓ Database is working")
    else:
        print("\n❌ Database issues found")
        print("To fix:")
        print("1. Make sure PostgreSQL is running")
        print("2. Create a database: createdb dashboard")
        print("3. Update DATABASE_URL in .env file")

if __name__ == "__main__":
    asyncio.run(main())