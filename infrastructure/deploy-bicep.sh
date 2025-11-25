#!/bin/bash

# Proper deployment script using Bicep
# This script builds Docker images and then deploys using Bicep

set -e

ENVIRONMENT=${1:-staging}
RESOURCE_GROUP="auditapp-${ENVIRONMENT}-rg"

echo "========================================="
echo "Audit App - Bicep Deployment"
echo "========================================="
echo ""
echo "Environment: $ENVIRONMENT"
echo "Resource Group: $RESOURCE_GROUP"
echo ""

# Get ACR name
echo "Getting Container Registry information..."
ACR_NAME=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name $(az deployment group list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv) \
    --query "properties.outputs.containerRegistryName.value" -o tsv)

echo "Container Registry: $ACR_NAME"
echo ""

# Build and push backend image using ACR Tasks (no local Docker required!)
echo "Building backend image in Azure..."
az acr build \
    --registry "$ACR_NAME" \
    --image auditapp-backend:latest \
    --file ../backend/Dockerfile \
    ../backend

echo ""
echo "✅ Backend image built and pushed to ACR"
echo ""

# Deploy using Bicep
echo "Deploying infrastructure with Bicep..."
az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file main.bicep \
    --parameters environment="$ENVIRONMENT" \
    --parameters useExistingAISearch=true \
    --parameters existingAISearchName=gptkb-obghpsbi63abq \
    --parameters existingAISearchRG=rg-saga-dev \
    --parameters useExistingStorage=true \
    --parameters existingStorageAccountName=stobghpsbi63abq \
    --parameters existingStorageAccountRG=rg-saga-dev \
    --query "properties.outputs" \
    -o json > deployment-outputs.json

echo ""
echo "✅ Bicep deployment complete"
echo ""

# Extract outputs
BACKEND_URL=$(jq -r '.backendUrl.value' deployment-outputs.json)
FRONTEND_URL=$(jq -r '.frontendUrl.value' deployment-outputs.json)

echo "==========================================="
echo "Deployment Complete!"
echo "==========================================="
echo ""
echo "Application URLs:"
echo "  Frontend: $FRONTEND_URL"
echo "  Backend:  $BACKEND_URL"
echo "  API Docs: ${BACKEND_URL}/docs"
echo ""
echo "Next Steps:"
echo "1. Configure GitHub deployment token for Static Web App"
echo "2. Push code to trigger Static Web App build"
echo "3. Test the application"
echo ""
