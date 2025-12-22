#!/bin/bash
# Run database migration to add message_enqueued_at column

set -e

echo "Getting SQL Server credentials..."
DB_SERVER=$(az containerapp env show --name auditapp-staging-env --resource-group auditapp-staging-rg --query "customDomainConfiguration.dnsSuffix" -o tsv)
DB_NAME="auditapp-staging-db"
DB_USER=$(az sql server show --name auditapp-staging-sqlserver --resource-group auditapp-staging-rg --query "administratorLogin" -o tsv)

# Get password from environment or prompt
if [ -z "$DB_PASSWORD" ]; then
    echo "DB_PASSWORD not set. Get it from Azure Key Vault or set manually."
    exit 1
fi

echo "Running migration 003_add_message_enqueued_at.sql..."
sqlcmd -S auditapp-staging-sqlserver.database.windows.net -d auditapp-staging-db -U $DB_USER -P "$DB_PASSWORD" -i backend/migrations/003_add_message_enqueued_at.sql

echo "Migration complete!"
