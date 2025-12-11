-- Simple migration to add updated_at column
-- This checks if the column exists first to make it idempotent

-- Check and add column if it doesn't exist
IF NOT EXISTS (
    SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'documents' AND COLUMN_NAME = 'updated_at'
)
BEGIN
    PRINT 'Adding updated_at column to documents table...'
    
    -- Add the column with default value
    ALTER TABLE documents 
    ADD updated_at DATETIME DEFAULT GETDATE() NOT NULL;
    
    -- Backfill with uploaded_at for existing records
    UPDATE documents
    SET updated_at = uploaded_at;
    
    -- Use processing_completed_at if available (more accurate)
    UPDATE documents
    SET updated_at = processing_completed_at
    WHERE processing_completed_at IS NOT NULL;
    
    PRINT 'Migration completed successfully!'
END
ELSE
BEGIN
    PRINT 'Column updated_at already exists. Skipping migration.'
END
GO
