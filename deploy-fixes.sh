#!/bin/bash
# Deploy Fix 1 + Fix 2 for document processing
# Fix 1: Prevent duplicate Service Bus messages
# Fix 2: Janitor auto-resets stuck leases every 1 minute

set -e

echo "=========================================="
echo "Deploying Fix 1 + Fix 2"
echo "=========================================="

# Wait for builds to complete
echo "Waiting for ACR builds to complete..."
echo "Check build status: az acr task list-runs --registry auditappstagingacrwgjuafflp2o4o --top 2"

# Deploy backend with Fix 1
echo ""
echo "1. Deploying backend with Fix 1 (prevent duplicate tickets)..."
az containerapp update \
  --name auditapp-staging-backend \
  --resource-group auditapp-staging-rg \
  --revision-suffix $(date +%s) \
  --query "properties.latestRevisionName" -o tsv

# Deploy worker with Fix 1 + Fix 2
echo ""
echo "2. Deploying worker with Fix 1 + Fix 2 (janitor)..."
az containerapp update \
  --name auditapp-staging-worker \
  --resource-group auditapp-staging-rg \
  --revision-suffix $(date +%s) \
  --query "properties.latestRevisionName" -o tsv

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run database migration: ./run-migration.sh"
echo "2. Reset stuck documents: curl -X POST \$BACKEND_URL/api/engagements/\$ENGAGEMENT_ID/documents/reset-stuck"
echo "3. Trigger processing: curl -X POST \$BACKEND_URL/api/engagements/\$ENGAGEMENT_ID/documents/trigger-processing"
echo "4. Monitor logs: az containerapp logs show --name auditapp-staging-worker -g auditapp-staging-rg --follow"
echo ""
