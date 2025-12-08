#!/usr/bin/env python3
"""
Database Migration Script: Add updated_at column to documents table

This script adds the updated_at column to the documents table in Azure SQL Database.
It handles the migration safely with proper error handling and rollback.

Usage:
    python run_migration.py

Prerequisites:
    - Set environment variables for database connection (same as app config)
    - Run from backend directory
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import DATABASE_URL


def check_column_exists(engine):
    """Check if updated_at column already exists"""
    query = text("""
        SELECT COUNT(*) as col_count
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'documents' 
        AND COLUMN_NAME = 'updated_at'
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        count = result.scalar()
        return count > 0


def run_migration(engine):
    """Run the migration to add updated_at column"""
    
    print("🔍 Checking if migration is needed...")
    
    if check_column_exists(engine):
        print("✅ Column 'updated_at' already exists in documents table. Skipping migration.")
        return True
    
    print("📝 Adding updated_at column to documents table...")
    
    migration_steps = [
        # Step 1: Add the column with default value
        """
        ALTER TABLE documents 
        ADD updated_at DATETIME DEFAULT GETDATE() NOT NULL;
        """,
        
        # Step 2: Backfill with uploaded_at
        """
        UPDATE documents
        SET updated_at = uploaded_at
        WHERE updated_at IS NULL OR updated_at = '1900-01-01';
        """,
        
        # Step 3: Use processing_completed_at if available (more accurate)
        """
        UPDATE documents
        SET updated_at = processing_completed_at
        WHERE processing_completed_at IS NOT NULL;
        """
    ]
    
    try:
        with engine.begin() as conn:  # Use begin() for transaction
            for i, step in enumerate(migration_steps, 1):
                print(f"   Step {i}/{len(migration_steps)}...", end=" ")
                conn.execute(text(step))
                print("✅")
        
        print("\n✅ Migration completed successfully!")
        
        # Verify the column was added
        if check_column_exists(engine):
            print("✅ Verified: updated_at column exists in documents table")
            
            # Show sample data
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT TOP 3 filename, uploaded_at, updated_at 
                    FROM documents 
                    ORDER BY uploaded_at DESC
                """))
                rows = result.fetchall()
                
                if rows:
                    print("\n📊 Sample data:")
                    for row in rows:
                        print(f"   {row.filename[:40]:<40} | uploaded: {row.uploaded_at} | updated: {row.updated_at}")
        
        return True
        
    except SQLAlchemyError as e:
        print(f"\n❌ Migration failed: {e}")
        print("   Transaction has been rolled back.")
        return False


def main():
    """Main migration runner"""
    print("=" * 70)
    print("Database Migration: Add updated_at to documents table")
    print("=" * 70)
    print()
    
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print("   Make sure your .env file is configured correctly.")
        return 1
    
    print(f"📍 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'}")
    print()
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL, echo=False)
        
        # Test connection
        print("🔌 Testing database connection...", end=" ")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅")
        print()
        
        # Run migration
        success = run_migration(engine)
        
        print()
        print("=" * 70)
        
        if success:
            print("✅ Migration completed successfully!")
            print()
            print("ℹ️  Next steps:")
            print("   1. Deploy the updated backend code")
            print("   2. The updated_at column will now be automatically maintained")
            return 0
        else:
            print("❌ Migration failed. Please check the errors above.")
            return 1
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
