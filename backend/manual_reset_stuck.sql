-- Reset stuck documents for engagement dce7c233-1969-4407-aeb0-85d8a5617754
-- This will reset all processing/queued documents back to queued status
-- Then we need to manually trigger Service Bus messages

UPDATE documents 
SET 
    status = 'queued',
    updated_at = CURRENT_TIMESTAMP,
    error_message = NULL
WHERE 
    engagement_id = 'dce7c233-1969-4407-aeb0-85d8a5617754'
    AND status IN ('processing', 'queued')
    AND updated_at < (CURRENT_TIMESTAMP - INTERVAL '1 hour');

-- Show affected documents
SELECT id, filename, status, updated_at 
FROM documents 
WHERE engagement_id = 'dce7c233-1969-4407-aeb0-85d8a5617754'
ORDER BY updated_at DESC;
