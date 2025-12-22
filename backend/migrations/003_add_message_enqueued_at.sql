-- Migration: Add message_enqueued_at column to track if Service Bus message already sent
-- Purpose: Prevent duplicate Service Bus messages for same document (FIX 1)
-- Date: 2024-12-18

-- Add column to track if message already in Service Bus queue
ALTER TABLE documents ADD message_enqueued_at DATETIME NULL;

-- Index for efficient queries
CREATE INDEX idx_documents_message_enqueued ON documents(message_enqueued_at);

-- Document the change
PRINT 'Added message_enqueued_at column to prevent duplicate Service Bus messages';
