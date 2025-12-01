#!/bin/bash
# ============================================
# Audit App - Smart Deployment Script
# ============================================
# Intelligently deploys only what's needed based on what changed
# Usage: ./deploy.sh [environment] [what-to-deploy]
#   environment: staging | prod (default: staging)
#   what-to-deploy: all | backend | frontend | infra (default: auto-detect)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ENVIRONMENT="${1:-staging}"
DEPLOY_TARGET="${2:-auto}"
RG="auditapp-${ENVIRONMENT}-rg"
ACR_NAME="auditappstagingacrwgjuafflp2o4o"
CONTAINER_APP="auditapp-${ENVIRONMENT}-backend"
STATIC_APP="auditapp-${ENVIRONMENT}-frontend"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Audit App Smart Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Environment:${NC} $ENVIRONMENT"
echo -e "${YELLOW}Target:${NC} $DEPLOY_TARGET"
echo ""

# ============================================
# Function: Deploy Backend Only
# ============================================
deploy_backend() {
    echo -e "${GREEN}📦 Deploying Backend...${NC}"
    
    # Build Docker image
    echo -e "${YELLOW}Building Docker image...${NC}"
    cd ../backend
    docker build -t "${ACR_NAME}.azurecr.io/auditapp-backend:latest" .
    
    # Push to ACR
    echo -e "${YELLOW}Pushing to Azure Container Registry...${NC}"
    az acr login --name "$ACR_NAME"
    docker push "${ACR_NAME}.azurecr.io/auditapp-backend:latest"
    
    # Update Container App
    echo -e "${YELLOW}Updating Container App...${NC}"
    az containerapp update \
        --name "$CONTAINER_APP" \
        --resource-group "$RG" \
        --image "${ACR_NAME}.azurecr.io/auditapp-backend:latest"
    
    cd ../infrastructure
    echo -e "${GREEN}✅ Backend deployed successfully!${NC}"
    echo ""
}

# ============================================
# Function: Deploy Frontend Only
# ============================================
deploy_frontend() {
    echo -e "${GREEN}🌐 Deploying Frontend...${NC}"
    echo ""
    echo -e "${YELLOW}Frontend deploys automatically via GitHub Actions${NC}"
    echo -e "${YELLOW}Just push your code:${NC} git push origin main"
    echo ""
    echo -e "${BLUE}Manual deployment (if needed):${NC}"
    echo "  cd ../frontend"
    echo "  npm install && npm run build"
    echo "  npx @azure/static-web-apps-cli deploy ./dist --deployment-token \$TOKEN"
    echo ""
}

# ============================================
# Function: Deploy Infrastructure
# ============================================
deploy_infrastructure() {
    echo -e "${GREEN}🏗️  Deploying Infrastructure...${NC}"
    echo -e "${RED}⚠️  WARNING: This will update ALL Azure resources!${NC}"
    echo -e "${YELLOW}This includes: SQL, Container Apps, Static Web App, etc.${NC}"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo -e "${YELLOW}Infrastructure deployment cancelled.${NC}"
        return
    fi
    
    echo -e "${YELLOW}Running Bicep deployment...${NC}"
    DEPLOYMENT_NAME="auditapp-update-$(date +%Y%m%d-%H%M%S)"
    
    az deployment group create \
        --name "$DEPLOYMENT_NAME" \
        --resource-group "$RG" \
        --template-file main.bicep \
        --parameters environment="$ENVIRONMENT" \
                     appName="auditapp" \
                     sqlAdminPassword="P@ssw0rd123!" \
                     azureOpenAIResourceName="cog-obghpsbi63abq" \
                     azureOpenAIResourceGroup="rg-saga-dev" \
                     useExistingAISearch=true \
                     existingAISearchName="gptkb-obghpsbi63abq" \
                     existingAISearchRG="rg-saga-dev" \
                     useExistingStorage=true \
                     existingStorageAccountName="stobghpsbi63abq" \
                     existingStorageAccountRG="rg-saga-dev"
    
    echo -e "${GREEN}✅ Infrastructure deployed successfully!${NC}"
    echo ""
}

# ============================================
# Function: Deploy Everything
# ============================================
deploy_all() {
    echo -e "${GREEN}🚀 Deploying Everything...${NC}"
    echo ""
    
    deploy_infrastructure
    sleep 5
    deploy_backend
    sleep 2
    deploy_frontend
    
    echo -e "${GREEN}✅ Full deployment complete!${NC}"
}

# ============================================
# Function: Auto-detect what to deploy
# ============================================
auto_detect() {
    echo -e "${YELLOW}🔍 Auto-detecting changes...${NC}"
    
    # Check if we're in a git repo
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${YELLOW}Not in a git repository. Deploying backend by default.${NC}"
        deploy_backend
        return
    fi
    
    # Get changed files since last commit
    CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || echo "")
    
    if [ -z "$CHANGED_FILES" ]; then
        echo -e "${YELLOW}No changes detected. Deploying backend by default.${NC}"
        deploy_backend
        return
    fi
    
    # Check what changed
    BACKEND_CHANGED=$(echo "$CHANGED_FILES" | grep -c "^backend/" || true)
    FRONTEND_CHANGED=$(echo "$CHANGED_FILES" | grep -c "^frontend/" || true)
    INFRA_CHANGED=$(echo "$CHANGED_FILES" | grep -c "^infrastructure/main.bicep" || true)
    
    echo -e "${BLUE}Changes detected:${NC}"
    [ "$BACKEND_CHANGED" -gt 0 ] && echo -e "  ${GREEN}✓${NC} Backend"
    [ "$FRONTEND_CHANGED" -gt 0 ] && echo -e "  ${GREEN}✓${NC} Frontend"
    [ "$INFRA_CHANGED" -gt 0 ] && echo -e "  ${GREEN}✓${NC} Infrastructure"
    echo ""
    
    # Deploy based on changes
    if [ "$INFRA_CHANGED" -gt 0 ]; then
        deploy_infrastructure
    fi
    
    if [ "$BACKEND_CHANGED" -gt 0 ]; then
        deploy_backend
    fi
    
    if [ "$FRONTEND_CHANGED" -gt 0 ]; then
        deploy_frontend
    fi
}

# ============================================
# Function: Show status
# ============================================
show_status() {
    echo -e "${BLUE}📊 Current Deployment Status${NC}"
    echo ""
    
    # Backend
    echo -e "${YELLOW}Backend:${NC}"
    BACKEND_STATUS=$(az containerapp show --name "$CONTAINER_APP" --resource-group "$RG" \
        --query "properties.runningStatus" -o tsv 2>/dev/null || echo "not found")
    BACKEND_URL=$(az containerapp show --name "$CONTAINER_APP" --resource-group "$RG" \
        --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
    
    if [ "$BACKEND_STATUS" = "Running" ]; then
        echo -e "  Status: ${GREEN}●${NC} Running"
        echo -e "  URL: https://$BACKEND_URL"
    else
        echo -e "  Status: ${RED}●${NC} $BACKEND_STATUS"
    fi
    
    # Frontend
    echo ""
    echo -e "${YELLOW}Frontend:${NC}"
    FRONTEND_URL=$(az staticwebapp show --name "$STATIC_APP" --resource-group "$RG" \
        --query "defaultHostname" -o tsv 2>/dev/null || echo "not found")
    
    if [ "$FRONTEND_URL" != "not found" ] && [ -n "$FRONTEND_URL" ]; then
        echo -e "  Status: ${GREEN}●${NC} Deployed"
        echo -e "  URL: https://$FRONTEND_URL"
    else
        echo -e "  Status: ${RED}●${NC} Not deployed"
    fi
    
    echo ""
}

# ============================================
# Main Logic
# ============================================

case "$DEPLOY_TARGET" in
    "all")
        deploy_all
        ;;
    "backend")
        deploy_backend
        ;;
    "frontend")
        deploy_frontend
        ;;
    "infra"|"infrastructure")
        deploy_infrastructure
        ;;
    "status")
        show_status
        ;;
    "auto")
        auto_detect
        ;;
    *)
        echo -e "${RED}Unknown target: $DEPLOY_TARGET${NC}"
        echo ""
        echo -e "${YELLOW}Usage:${NC}"
        echo "  ./deploy.sh [environment] [target]"
        echo ""
        echo -e "${YELLOW}Targets:${NC}"
        echo "  auto          - Auto-detect what changed (default)"
        echo "  backend       - Deploy backend only"
        echo "  frontend      - Deploy frontend only"
        echo "  infra         - Deploy infrastructure only"
        echo "  all           - Deploy everything"
        echo "  status        - Show current deployment status"
        echo ""
        echo -e "${YELLOW}Examples:${NC}"
        echo "  ./deploy.sh                    # Auto-detect in staging"
        echo "  ./deploy.sh staging backend    # Deploy backend to staging"
        echo "  ./deploy.sh prod all           # Full production deployment"
        echo "  ./deploy.sh staging status     # Show status"
        exit 1
        ;;
esac

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
