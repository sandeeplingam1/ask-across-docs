-- Migration: Add production-grade patterns for distributed systems
-- Implements: Outbox Pattern, Leases, Idempotency, Retry Logic

-- Step 1: Add lease and retry columns to documents table
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS processing_attempts INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 3,
ADD COLUMN IF NOT EXISTS last_error TEXT;

-- Create index for lease expiration queries
CREATE INDEX IF NOT EXISTS idx_documents_lease_expires ON documents(lease_expires_at) WHERE status = 'processing';

-- Step 2: Create outbox table for transactional consistency
CREATE TABLE IF NOT EXISTS document_processing_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    engagement_id UUID NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL DEFAULT 'process_document',
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    attempts INTEGER DEFAULT 0,
    last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_outbox_unprocessed ON document_processing_outbox(created_at) WHERE processed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_outbox_document ON document_processing_outbox(document_id);

-- Step 3: Add backpressure tracking table
CREATE TABLE IF NOT EXISTS processing_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engagement_id UUID REFERENCES engagements(id) ON DELETE CASCADE,
    metric_type VARCHAR(50) NOT NULL,
    value INTEGER NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_metrics_engagement_type ON processing_metrics(engagement_id, metric_type, recorded_at);

-- Step 4: Create function to acquire document lease
CREATE OR REPLACE FUNCTION acquire_document_lease(
    p_document_id UUID,
    p_lease_duration_minutes INTEGER DEFAULT 5
) RETURNS BOOLEAN AS $$
DECLARE
    v_acquired BOOLEAN;
BEGIN
    UPDATE documents
    SET 
        status = 'processing',
        lease_expires_at = NOW() + (p_lease_duration_minutes || ' minutes')::INTERVAL,
        processing_attempts = processing_attempts + 1,
        updated_at = NOW()
    WHERE 
        id = p_document_id
        AND (
            status = 'queued'
            OR (status = 'processing' AND (lease_expires_at IS NULL OR lease_expires_at < NOW()))
        )
        AND processing_attempts < max_retries
    RETURNING TRUE INTO v_acquired;
    
    RETURN COALESCE(v_acquired, FALSE);
END;
$$ LANGUAGE plpgsql;

-- Step 5: Create function to release document lease
CREATE OR REPLACE FUNCTION release_document_lease(
    p_document_id UUID,
    p_success BOOLEAN,
    p_error TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    IF p_success THEN
        UPDATE documents
        SET 
            status = 'completed',
            lease_expires_at = NULL,
            last_error = NULL,
            updated_at = NOW()
        WHERE id = p_document_id;
    ELSE
        UPDATE documents
        SET 
            status = CASE 
                WHEN processing_attempts >= max_retries THEN 'failed'
                ELSE 'queued'
            END,
            lease_expires_at = NULL,
            last_error = p_error,
            error_message = p_error,
            updated_at = NOW()
        WHERE id = p_document_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Step 6: Create function to find expired leases
CREATE OR REPLACE FUNCTION find_expired_leases()
RETURNS TABLE(document_id UUID, engagement_id UUID) AS $$
BEGIN
    RETURN QUERY
    UPDATE documents
    SET 
        status = 'queued',
        lease_expires_at = NULL,
        updated_at = NOW()
    WHERE 
        status = 'processing'
        AND lease_expires_at < NOW()
        AND processing_attempts < max_retries
    RETURNING id, engagement_id;
END;
$$ LANGUAGE plpgsql;

-- Step 7: Add comments for documentation
COMMENT ON COLUMN documents.lease_expires_at IS 'Implements lease pattern - document lock expires and can be retried';
COMMENT ON COLUMN documents.processing_attempts IS 'Tracks retry attempts for idempotency and circuit breaking';
COMMENT ON COLUMN documents.max_retries IS 'Maximum retry attempts before marking as failed (default 3)';
COMMENT ON TABLE document_processing_outbox IS 'Outbox pattern - ensures transactional consistency between DB and Service Bus';
COMMENT ON FUNCTION acquire_document_lease IS 'Atomically acquires lease on document for processing with expiration';
COMMENT ON FUNCTION release_document_lease IS 'Releases lease and marks document as completed/failed';
COMMENT ON FUNCTION find_expired_leases IS 'Finds and resets expired leases for automatic retry';
