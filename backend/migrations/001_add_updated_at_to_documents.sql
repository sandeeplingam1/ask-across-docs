-- Migration: Add updated_at column to documents table
-- Date: 2025-12-08
-- Description: Adds updated_at column to documents table for consistency with other tables

-- Add the updated_at column with default value
ALTER TABLE documents 
ADD updated_at DATETIME DEFAULT GETDATE() NOT NULL;

-- Add trigger to automatically update updated_at on row changes (SQL Server syntax)
-- Note: SQL Server doesn't have built-in ON UPDATE like MySQL, so we use a trigger
GO

CREATE TRIGGER trg_documents_updated_at
ON documents
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE documents
    SET updated_at = GETDATE()
    FROM documents d
    INNER JOIN inserted i ON d.id = i.id;
END;
GO

-- Backfill existing records: set updated_at to uploaded_at for historical data
UPDATE documents
SET updated_at = uploaded_at
WHERE updated_at IS NULL;

-- Optional: Set updated_at to processing_completed_at if available (more accurate)
UPDATE documents
SET updated_at = processing_completed_at
WHERE processing_completed_at IS NOT NULL;

GO
