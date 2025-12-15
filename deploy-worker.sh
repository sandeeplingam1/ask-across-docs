#!/bin/bash
# Deploy document processing worker to Azure Container Apps
set -e

echo "🚀 Deploying Document Processing Worker..."

# Configuration
RESOURCE_GROUP="auditapp-staging-rg"
LOCATION="eastus"
ACR_NAME="auditappstagingacrwgjuafflp2o4o"
WORKER_APP_NAME="auditapp-staging-worker"
CONTAINER_ENV="auditapp-staging-containerenv"
IMAGE_TAG="stable-worker-$(date +%Y%m%d-%H%M%S)"

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query loginServer -o tsv)
echo "📦 ACR: $ACR_LOGIN_SERVER"

# Build and push worker image
echo "🔨 Building worker Docker image..."
cd backend
az acr build --registry $ACR_NAME \
    --image auditapp-worker:$IMAGE_TAG \
    --image auditapp-worker:latest \
    --file Dockerfile.worker \
    .
cd ..

echo "✅ Worker image built and pushed"

# Get all secrets from existing backend container
echo "🔑 Retrieving configuration from backend..."
DATABASE_URL=$(az containerapp show --name auditapp-staging-backend --resource-group $RESOURCE_GROUP --query 'properties.template.containers[0].env[?name==`DATABASE_URL`].secretRef' -o tsv)
STORAGE_CONN=$(az containerapp show --name auditapp-staging-backend --resource-group $RESOURCE_GROUP --query 'properties.template.containers[0].env[?name==`AZURE_STORAGE_CONNECTION_STRING`].secretRef' -o tsv)
SEARCH_KEY=$(az containerapp show --name auditapp-staging-backend --resource-group $RESOURCE_GROUP --query 'properties.template.containers[0].env[?name==`AZURE_SEARCH_API_KEY`].secretRef' -o tsv)

# Get all the env var values
AZURE_OPENAI_ENDPOINT=$(az containerapp show --name auditapp-staging-backend --resource-group $RESOURCE_GROUP --query 'properties.template.containers[0].env[?name==`AZURE_OPENAI_ENDPOINT`].value' -o tsv)
AZURE_OPENAI_CHAT_DEPLOYMENT=$(az containerapp show --name auditapp-staging-backend --resource-group $RESOURCE_GROUP --query 'properties.template.containers[0].env[?name==`AZURE_OPENAI_CHAT_DEPLOYMENT`].value' -o tsv)
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=$(az containerapp show --name auditapp-staging-backend --resource-group $RESOURCE_GROUP --query 'properties.template.containers[0].env[?name==`AZURE_OPENAI_EMBEDDING_DEPLOYMENT`].value' -o tsv)
AZURE_OPENAI_API_VERSION=$(az containerapp show --name auditapp-staging-backend --resource-group $RESOURCE_GROUP --query 'properties.template.containers[0].env[?name==`AZURE_OPENAI_API_VERSION`].value' -o tsv)
AZURE_SEARCH_ENDPOINT=$(az containerapp show --name auditapp-staging-backend --resource-group $RESOURCE_GROUP --query 'properties.template.containers[0].env[?name==`AZURE_SEARCH_ENDPOINT`].value' -o tsv)
AZURE_SEARCH_INDEX_NAME=$(az containerapp show --name auditapp-staging-backend --resource-group $RESOURCE_GROUP --query 'properties.template.containers[0].env[?name==`AZURE_SEARCH_INDEX_NAME`].value' -o tsv)
AZURE_STORAGE_CONTAINER_NAME=$(az containerapp show --name auditapp-staging-backend --resource-group $RESOURCE_GROUP --query 'properties.template.containers[0].env[?name==`AZURE_STORAGE_CONTAINER_NAME`].value' -o tsv)

# Check if worker already exists
if az containerapp show --name $WORKER_APP_NAME --resource-group $RESOURCE_GROUP &>/dev/null; then
    echo "📦 Updating existing worker container..."
    az containerapp update \
        --name $WORKER_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --image "$ACR_LOGIN_SERVER/auditapp-worker:latest" \
        --cpu 0.5 \
        --memory 1.0Gi \
        --min-replicas 1 \
        --max-replicas 1
else
    echo "🆕 Creating new worker container..."
    az containerapp create \
        --name $WORKER_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --environment $CONTAINER_ENV \
        --image "$ACR_LOGIN_SERVER/auditapp-worker:latest" \
        --registry-server $ACR_LOGIN_SERVER \
        --registry-identity system \
        --cpu 0.5 \
        --memory 1.0Gi \
        --min-replicas 1 \
        --max-replicas 1 \
        --ingress external \
        --target-port 8000 \
        --env-vars \
            "ENVIRONMENT=staging" \
            "VECTOR_DB_TYPE=azure_search" \
            "USE_AZURE_AD_AUTH=true" \
            "ENABLE_TELEMETRY=false" \
            "AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT" \
            "AZURE_OPENAI_CHAT_DEPLOYMENT=$AZURE_OPENAI_CHAT_DEPLOYMENT" \
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT=$AZURE_OPENAI_EMBEDDING_DEPLOYMENT" \
            "AZURE_OPENAI_API_VERSION=$AZURE_OPENAI_API_VERSION" \
            "AZURE_SEARCH_ENDPOINT=$AZURE_SEARCH_ENDPOINT" \
            "AZURE_SEARCH_INDEX_NAME=$AZURE_SEARCH_INDEX_NAME" \
            "AZURE_STORAGE_CONTAINER_NAME=$AZURE_STORAGE_CONTAINER_NAME" \
        --secrets \
            "database-url=$DATABASE_URL" \
            "storage-connection-string=$STORAGE_CONN" \
            "azure-search-api-key=$SEARCH_KEY" \
        --secret-env-vars \
            "DATABASE_URL=database-url" \
            "AZURE_STORAGE_CONNECTION_STRING=storage-connection-string" \
            "AZURE_SEARCH_API_KEY=azure-search-api-key"
fi

echo "✅ Worker deployment complete!"
echo ""
echo "📊 Check worker logs:"
echo "   az containerapp logs show --name $WORKER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo ""
echo "🔍 Check worker status:"
echo "   az containerapp show --name $WORKER_APP_NAME --resource-group $RESOURCE_GROUP --query 'properties.runningStatus'"
