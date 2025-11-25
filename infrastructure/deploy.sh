#!/bin/bash

# Audit App - Complete Azure Deployment Script
# Deploys ALL infrastructure via Bicep (SQL, Redis, ACR, Container Apps Environment, Backend Container App, Static Web App)
set -e

echo "========================================"
echo "Audit App - Complete Deployment"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
ENVIRONMENT="${1:-staging}"
LOCATION="${2:-eastus}"
APP_NAME="auditapp"
RESOURCE_GROUP="${APP_NAME}-${ENVIRONMENT}-rg"

# Existing resources configuration (reusing from rg-saga-dev)
EXISTING_RG="rg-saga-dev"
EXISTING_AI_SEARCH="gptkb-obghpsbi63abq"
EXISTING_STORAGE="stobghpsbi63abq"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Environment: $ENVIRONMENT"
echo "  Location: $LOCATION"
echo "  Resource Group: $RESOURCE_GROUP"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    echo "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
echo -e "${GREEN}Checking Azure login...${NC}"
az account show > /dev/null 2>&1 || {
    echo -e "${YELLOW}Not logged in. Please login...${NC}"
    az login
}

# Get subscription
SUBSCRIPTION=$(az account show --query name -o tsv)
echo -e "${GREEN}Using subscription: $SUBSCRIPTION${NC}"
echo ""

# Create resource group if it doesn't exist
echo -e "${GREEN}Creating resource group: $RESOURCE_GROUP${NC}"
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --tags Environment="$ENVIRONMENT" Application="AuditApp" ManagedBy="Script"

echo ""
echo -e "${GREEN}Deploying infrastructure...${NC}"
echo "This may take 10-15 minutes..."
echo ""

# Deploy Bicep template
DEPLOYMENT_NAME="${APP_NAME}-deployment-$(date +%Y%m%d-%H%M%S)"

if [ "$ENVIRONMENT" = "staging" ]; then
    echo -e "${YELLOW}Reusing existing resources from $EXISTING_RG:${NC}"
    echo "  - AI Search: $EXISTING_AI_SEARCH"
    echo "  - Storage Account: $EXISTING_STORAGE"
    echo ""
    
    az deployment group create \
        --name "$DEPLOYMENT_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --template-file main.bicep \
        --parameters environment="$ENVIRONMENT" appName="$APP_NAME" \
                     useExistingAISearch=true \
                     existingAISearchName="$EXISTING_AI_SEARCH" \
                     existingAISearchRG="$EXISTING_RG" \
                     useExistingStorage=true \
                     existingStorageAccountName="$EXISTING_STORAGE" \
                     existingStorageAccountRG="$EXISTING_RG" \
        --output table
else
    echo -e "${YELLOW}Creating all new resources for production${NC}"
    echo ""
    
    az deployment group create \
        --name "$DEPLOYMENT_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --template-file main.bicep \
        --parameters environment="$ENVIRONMENT" appName="$APP_NAME" \
        --output table
fi

echo ""
echo -e "${GREEN}Deployment completed!${NC}"
echo ""

# Get ACR name from deployment
echo -e "${YELLOW}Building and pushing backend Docker image...${NC}"
ACR_NAME=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.containerRegistryName.value" -o tsv)

echo "  Container Registry: $ACR_NAME"

# Navigate to backend folder
cd ../backend

# Login to ACR
echo -e "${YELLOW}Logging in to ACR...${NC}"
az acr login --name "$ACR_NAME"

# Build and push image
echo -e "${YELLOW}Building backend image...${NC}"
docker build -t "${ACR_NAME}.azurecr.io/auditapp-backend:latest" .

echo -e "${YELLOW}Pushing to ACR...${NC}"
docker push "${ACR_NAME}.azurecr.io/auditapp-backend:latest"

echo -e "${GREEN}✓ Docker image deployed to ACR${NC}"
cd ../infrastructure

# Update Container App to pull the new image
echo -e "${YELLOW}Redeploying infrastructure with Docker image...${NC}"
if [ "$ENVIRONMENT" = "staging" ]; then
    az deployment group create \
        --name "${APP_NAME}-update-$(date +%Y%m%d-%H%M%S)" \
        --resource-group "$RESOURCE_GROUP" \
        --template-file main.bicep \
        --parameters environment="$ENVIRONMENT" appName="$APP_NAME" \
                     useExistingAISearch=true \
                     existingAISearchName="$EXISTING_AI_SEARCH" \
                     existingAISearchRG="$EXISTING_RG" \
                     useExistingStorage=true \
                     existingStorageAccountName="$EXISTING_STORAGE" \
                     existingStorageAccountRG="$EXISTING_RG" \
        --output none
else
    az deployment group create \
        --name "${APP_NAME}-update-$(date +%Y%m%d-%H%M%S)" \
        --resource-group "$RESOURCE_GROUP" \
        --template-file main.bicep \
        --parameters environment="$ENVIRONMENT" appName="$APP_NAME" \
        --output none
fi

echo -e "${GREEN}✓ Container App updated${NC}"
echo ""

# Create containers and queues in existing storage if using existing storage
if [ "$ENVIRONMENT" = "staging" ]; then
    echo -e "${YELLOW}Setting up containers and queues in existing storage...${NC}"
    
    # Create blob container
    az storage container create \
        --name "audit-${ENVIRONMENT}-documents" \
        --account-name "$EXISTING_STORAGE" \
        --auth-mode login \
        --only-show-errors || echo "Container may already exist"
    
    # Create queue
    az storage queue create \
        --name "audit-${ENVIRONMENT}-processing" \
        --account-name "$EXISTING_STORAGE" \
        --auth-mode login \
        --only-show-errors || echo "Queue may already exist"
    
    echo -e "${GREEN}Storage setup completed${NC}"
    echo ""
fi

# Get outputs
echo -e "${YELLOW}Getting deployment outputs...${NC}"
az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.outputs \
    --output json > deployment-outputs.json

echo ""
echo -e "${GREEN}Deployment outputs saved to: deployment-outputs.json${NC}"
echo ""

# Extract key values
SQL_SERVER=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.sqlServerName.value -o tsv)
STORAGE_ACCOUNT=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.storageAccountName.value -o tsv)
SEARCH_SERVICE=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.searchServiceName.value -o tsv)
KEY_VAULT=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.keyVaultName.value -o tsv)

echo -e "${YELLOW}Created Resources:${NC}"
echo "  SQL Server: $SQL_SERVER"
echo "  Storage Account: $STORAGE_ACCOUNT"
echo "  Search Service: $SEARCH_SERVICE"
echo "  Key Vault: $KEY_VAULT"
echo ""

# Generate .env.production file
echo -e "${GREEN}Generating .env.production file...${NC}"
cat > ../.env.production << EOF
# ==============================================
# PRODUCTION ENVIRONMENT CONFIGURATION
# ==============================================
# Generated: $(date)

ENVIRONMENT=production

# Azure OpenAI (update with your existing resource)
AZURE_OPENAI_ENDPOINT=https://cog-obghpsbi63abq.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4.1-mini

# Vector Database
VECTOR_DB_TYPE=azure_search
AZURE_SEARCH_ENDPOINT=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.searchEndpoint.value -o tsv)
AZURE_SEARCH_API_KEY=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.searchApiKey.value -o tsv)
AZURE_SEARCH_INDEX_NAME=audit-${ENVIRONMENT}-documents

# Database
DATABASE_URL=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.sqlConnectionString.value -o tsv)

# Storage
AZURE_STORAGE_CONNECTION_STRING=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.storageConnectionString.value -o tsv)
AZURE_STORAGE_CONTAINER_NAME=audit-${ENVIRONMENT}-documents

# Redis
REDIS_URL=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.redisConnectionString.value -o tsv)

# Monitoring
APPLICATIONINSIGHTS_CONNECTION_STRING=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.outputs.appInsightsConnectionString.value -o tsv)
ENABLE_TELEMETRY=true

# Application
BACKEND_CORS_ORIGINS=https://${APP_NAME}-${ENVIRONMENT}-frontend.azurestaticapps.net
MAX_UPLOAD_SIZE_MB=100
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
ENABLE_BACKGROUND_PROCESSING=true
MAX_CONCURRENT_DOCUMENT_PROCESSING=10

# Security
SECRET_KEY=$(openssl rand -base64 32)

EOF

echo -e "${GREEN}.env.production file created!${NC}"
echo ""

echo "========================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "========================================"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review .env.production file and update any missing values"
echo "2. Deploy backend: ./deploy-backend.sh"
echo "3. Deploy frontend: ./deploy-frontend.sh"
echo "4. Run database migrations"
echo "5. Test the deployment"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "- Store sensitive values in Azure Key Vault"
echo "- Update SQL admin password in Azure Portal"
echo "- Configure custom domains if needed"
echo "- Set up CI/CD pipelines"
echo ""
