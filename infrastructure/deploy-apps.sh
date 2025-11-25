#!/bin/bash

# Audit App - Deploy Applications to Azure Container Apps
set -e

echo "========================================"
echo "Audit App - Application Deployment"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
ENVIRONMENT="${1:-staging}"
RESOURCE_GROUP="auditapp-${ENVIRONMENT}-rg"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Environment: $ENVIRONMENT"
echo "  Resource Group: $RESOURCE_GROUP"
echo ""

# Get deployment outputs
echo -e "${GREEN}Getting deployment information...${NC}"
CONTAINER_REGISTRY=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name $(az deployment group list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv) \
    --query "properties.outputs.containerRegistryName.value" -o tsv)

# Get deployment outputs
echo -e "${GREEN}Getting deployment information...${NC}"
CONTAINER_REGISTRY=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name $(az deployment group list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv) \
    --query "properties.outputs.containerRegistryName.value" -o tsv)

# Try to get Container Apps Environment from deployment outputs, fallback to list query
CONTAINER_ENV=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name $(az deployment group list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv) \
    --query "properties.outputs.containerAppsEnvironmentName.value" -o tsv 2>/dev/null)

# If empty, query directly for the environment
if [ -z "$CONTAINER_ENV" ]; then
    CONTAINER_ENV=$(az containerapp env list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
fi

echo "  Container Registry: $CONTAINER_REGISTRY"
echo "  Container Apps Environment: $CONTAINER_ENV"
echo ""

# Enable admin access for ACR (needed for simple deployments)
echo -e "${GREEN}Enabling ACR admin access...${NC}"
az acr update --name "$CONTAINER_REGISTRY" --admin-enabled true

# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name "$CONTAINER_REGISTRY" --query "username" -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$CONTAINER_REGISTRY" --query "passwords[0].value" -o tsv)
ACR_LOGIN_SERVER="${CONTAINER_REGISTRY}.azurecr.io"

echo ""
echo -e "${GREEN}Building and pushing Docker images...${NC}"

# Build and push backend
echo -e "${YELLOW}Building backend image...${NC}"
cd ../backend
docker build -t "${ACR_LOGIN_SERVER}/auditapp-backend:latest" .

echo -e "${YELLOW}Pushing backend image...${NC}"
az acr login --name "$CONTAINER_REGISTRY"
docker push "${ACR_LOGIN_SERVER}/auditapp-backend:latest"

# Build and push frontend
echo -e "${YELLOW}Building frontend image...${NC}"
cd ../frontend
docker build -t "${ACR_LOGIN_SERVER}/auditapp-frontend:latest" .

echo -e "${YELLOW}Pushing frontend image...${NC}"
docker push "${ACR_LOGIN_SERVER}/auditapp-frontend:latest"

cd ../infrastructure

echo ""
echo -e "${GREEN}Deploying Container Apps...${NC}"

# Get environment variables from .env.production
if [ -f "../.env.production" ]; then
    echo -e "${YELLOW}Loading environment variables from .env.production${NC}"
    set -a  # Automatically export all variables
    while IFS='=' read -r key value; do
        # Skip empty lines and comments
        if [[ ! -z "$key" && ! "$key" =~ ^[[:space:]]*# ]]; then
            # Remove leading/trailing whitespace
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            export "$key=$value"
        fi
    done < ../.env.production
    set +a
else
    echo -e "${RED}Error: .env.production not found${NC}"
    exit 1
fi

# Deploy Backend Container App
echo -e "${YELLOW}Deploying backend container app...${NC}"
az containerapp create \
    --name "auditapp-backend" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$CONTAINER_ENV" \
    --image "${ACR_LOGIN_SERVER}/auditapp-backend:latest" \
    --registry-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_USERNAME" \
    --registry-password "$ACR_PASSWORD" \
    --target-port 8000 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 1.0 \
    --memory 2.0Gi \
    --env-vars \
        "ENVIRONMENT=$ENVIRONMENT" \
        "DATABASE_URL=$DATABASE_URL" \
        "AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT" \
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT=$AZURE_OPENAI_EMBEDDING_DEPLOYMENT" \
        "AZURE_OPENAI_CHAT_DEPLOYMENT=$AZURE_OPENAI_CHAT_DEPLOYMENT" \
        "AZURE_SEARCH_ENDPOINT=$AZURE_SEARCH_ENDPOINT" \
        "AZURE_SEARCH_API_KEY=$AZURE_SEARCH_API_KEY" \
        "AZURE_SEARCH_INDEX_NAME=$AZURE_SEARCH_INDEX_NAME" \
        "AZURE_STORAGE_CONNECTION_STRING=$AZURE_STORAGE_CONNECTION_STRING" \
        "AZURE_STORAGE_CONTAINER_NAME=$AZURE_STORAGE_CONTAINER_NAME" \
        "REDIS_URL=$REDIS_URL" \
        "VECTOR_DB_TYPE=azure_search"

# Get backend URL
BACKEND_URL=$(az containerapp show \
    --name "auditapp-backend" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv)

echo ""
echo -e "${GREEN}Backend deployed: https://$BACKEND_URL${NC}"

# Deploy Frontend Container App
echo -e "${YELLOW}Deploying frontend container app...${NC}"
az containerapp create \
    --name "auditapp-frontend" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$CONTAINER_ENV" \
    --image "${ACR_LOGIN_SERVER}/auditapp-frontend:latest" \
    --registry-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_USERNAME" \
    --registry-password "$ACR_PASSWORD" \
    --target-port 80 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 0.5 \
    --memory 1.0Gi \
    --env-vars \
        "VITE_API_URL=https://$BACKEND_URL"

# Get frontend URL
FRONTEND_URL=$(az containerapp show \
    --name "auditapp-frontend" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv)

echo ""
echo -e "${GREEN}===========================================
Deployment Complete!
===========================================${NC}"
echo ""
echo -e "${GREEN}Application URLs:${NC}"
echo "  Frontend: https://$FRONTEND_URL"
echo "  Backend:  https://$BACKEND_URL"
echo "  API Docs: https://$BACKEND_URL/docs"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update CORS in backend to include frontend URL"
echo "2. Test the application"
echo "3. Monitor logs: az containerapp logs tail --name auditapp-backend -g $RESOURCE_GROUP"
echo ""
