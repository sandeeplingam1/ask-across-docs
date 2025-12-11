"""Simple migration runner that can be executed inside the container"""
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def run_migration():
    """Add updated_at column to documents table"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not set")
        return
    
    print("🔌 Connecting to database...")
    engine = create_async_engine(database_url, echo=False)
    
    async with engine.begin() as conn:
        # Check if column exists
        check_sql = text("""
            SELECT COUNT(*) as col_count
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'documents' AND COLUMN_NAME = 'updated_at'
        """)
        
        result = await conn.execute(check_sql)
        exists = result.scalar() > 0
        
        if exists:
            print("✅ Column 'updated_at' already exists. Skipping migration.")
            return
        
        print("📝 Adding updated_at column...")
        
        # Add column
        await conn.execute(text("""
            ALTER TABLE documents 
            ADD updated_at DATETIME DEFAULT GETDATE() NOT NULL
        """))
        
        print("📝 Backfilling data...")
        
        # Backfill with uploaded_at
        await conn.execute(text("""
            UPDATE documents SET updated_at = uploaded_at
        """))
        
        # Use processing_completed_at if available
        await conn.execute(text("""
            UPDATE documents SET updated_at = processing_completed_at
            WHERE processing_completed_at IS NOT NULL
        """))
        
        print("✅ Migration completed successfully!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migration())
