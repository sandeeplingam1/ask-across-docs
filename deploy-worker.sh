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

# Get all the env var values from backend (non-secrets)
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
    echo "⚠️  Manual secret configuration required after creation"
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
            "AZURE_STORAGE_CONTAINER_NAME=$AZURE_STORAGE_CONTAINER_NAME"
    
    echo ""
    echo "📝 Now adding secrets from Azure Portal or CLI..."
    echo "   You need to add these secrets to the worker container:"
    echo "   - DATABASE_URL"
    echo "   - AZURE_STORAGE_CONNECTION_STRING"  
    echo "   - AZURE_SEARCH_API_KEY"
    echo ""
    echo "   Copy them from auditapp-staging-backend container in Azure Portal:"
    echo "   1. Go to Container Apps > auditapp-staging-backend > Secrets"
    echo "   2. Copy each secret"
    echo "   3. Go to Container Apps > auditapp-staging-worker > Secrets"
    echo "   4. Add each secret with same name"
    echo "   5. Add environment variables referencing the secrets"
fi

echo "✅ Worker deployment complete!"
echo ""
echo "📊 Check worker logs:"
echo "   az containerapp logs show --name $WORKER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo ""
echo "🔍 Check worker status:"
echo "   az containerapp show --name $WORKER_APP_NAME --resource-group $RESOURCE_GROUP --query 'properties.runningStatus'"
