-- Migration: Add Production Patterns (Outbox, Leases, Backpressure)
-- Database: Azure SQL Server
-- Date: 2025-01-XX

-- Step 1: Add columns to documents table for lease management and retry logic
ALTER TABLE documents 
ADD lease_expires_at DATETIME2 NULL;

ALTER TABLE documents
ADD processing_attempts INT NOT NULL DEFAULT 0;

ALTER TABLE documents
ADD max_retries INT NOT NULL DEFAULT 3;

ALTER TABLE documents
ADD last_error NVARCHAR(MAX) NULL;

-- Step 2: Create outbox table for transactional consistency
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'document_processing_outbox')
BEGIN
    CREATE TABLE document_processing_outbox (
        id VARCHAR(36) PRIMARY KEY,
        document_id VARCHAR(36) NOT NULL FOREIGN KEY REFERENCES documents(id) ON DELETE CASCADE,
        message_type VARCHAR(50) NOT NULL DEFAULT 'process_document',
        payload NVARCHAR(MAX) NOT NULL,
        created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        processed_at DATETIME2 NULL,
        attempts INT NOT NULL DEFAULT 0
    );
END;
GO

-- Step 3: Create indexes for performance
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_outbox_pending')
BEGIN
    CREATE INDEX idx_outbox_pending ON document_processing_outbox(processed_at, created_at)
    WHERE processed_at IS NULL;
END;
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_documents_lease')
BEGIN
    CREATE INDEX idx_documents_lease ON documents(status, lease_expires_at)
    WHERE status = 'processing';
END;
GO

-- Step 4: Create stored procedure for atomic lease acquisition
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'acquire_document_lease')
    DROP PROCEDURE acquire_document_lease;
GO

CREATE PROCEDURE acquire_document_lease
    @p_document_id VARCHAR(36),
    @p_lease_duration_minutes INT = 5,
    @acquired BIT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET @acquired = 0;

    BEGIN TRANSACTION;
    
    DECLARE @current_attempts INT;
    DECLARE @max INT;
    DECLARE @current_status VARCHAR(50);
    DECLARE @lease_expiry DATETIME2;

    -- Check if document is eligible for lease
    SELECT 
        @current_attempts = processing_attempts,
        @max = max_retries,
        @current_status = status,
        @lease_expiry = lease_expires_at
    FROM documents WITH (UPDLOCK)
    WHERE id = @p_document_id;

    -- Acquire lease if eligible (not yet max retries, and either queued or lease expired)
    IF @current_attempts < @max AND 
       (@current_status = 'queued' OR (@current_status = 'processing' AND @lease_expiry < GETUTCDATE()))
    BEGIN
        UPDATE documents
        SET 
            status = 'processing',
            lease_expires_at = DATEADD(MINUTE, @p_lease_duration_minutes, GETUTCDATE()),
            processing_attempts = processing_attempts + 1,
            processing_started_at = CASE WHEN processing_started_at IS NULL THEN GETUTCDATE() ELSE processing_started_at END
        WHERE id = @p_document_id;

        SET @acquired = 1;
    END;

    COMMIT TRANSACTION;
    RETURN @acquired;
END;
GO

-- Step 5: Create stored procedure for releasing lease (on completion or failure)
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'release_document_lease')
    DROP PROCEDURE release_document_lease;
GO

CREATE PROCEDURE release_document_lease
    @p_document_id VARCHAR(36),
    @p_success BIT,
    @p_error_message NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF @p_success = 1
    BEGIN
        -- Success: Mark as completed
        UPDATE documents
        SET 
            status = 'completed',
            lease_expires_at = NULL,
            error_message = NULL,
            last_error = NULL,
            processing_completed_at = GETUTCDATE()
        WHERE id = @p_document_id;
    END
    ELSE
    BEGIN
        -- Failure: Check if we should retry or mark as failed
        DECLARE @attempts INT;
        DECLARE @max INT;

        SELECT @attempts = processing_attempts, @max = max_retries
        FROM documents
        WHERE id = @p_document_id;

        IF @attempts >= @max
        BEGIN
            -- Max retries reached, mark as failed
            UPDATE documents
            SET 
                status = 'failed',
                lease_expires_at = NULL,
                error_message = @p_error_message,
                last_error = @p_error_message,
                processing_completed_at = GETUTCDATE()
            WHERE id = @p_document_id;
        END
        ELSE
        BEGIN
            -- Retry available, release lease and queue for retry
            UPDATE documents
            SET 
                status = 'queued',
                lease_expires_at = NULL,
                last_error = @p_error_message
            WHERE id = @p_document_id;
        END;
    END;
END;
GO

-- Step 6: Create stored procedure to find expired leases
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'find_expired_leases')
    DROP PROCEDURE find_expired_leases;
GO

CREATE PROCEDURE find_expired_leases
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        id,
        filename,
        processing_attempts,
        max_retries,
        lease_expires_at,
        last_error
    FROM documents
    WHERE 
        status = 'processing' 
        AND lease_expires_at < GETUTCDATE()
        AND processing_attempts < max_retries
    ORDER BY lease_expires_at ASC;
END;
GO

PRINT 'Migration completed successfully!';
PRINT 'Added columns: lease_expires_at, processing_attempts, max_retries, last_error';
PRINT 'Created table: document_processing_outbox';
PRINT 'Created procedures: acquire_document_lease, release_document_lease, find_expired_leases';
