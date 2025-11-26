#!/bin/bash
# Azure Resource Group Diagnostic Script
# This will show you EXACTLY what's deployed and what needs fixing

set -e

echo "=========================================="
echo "Azure Audit App - Resource Diagnostic"
echo "=========================================="
echo ""

RG_NAME="auditapp-staging-rg"

echo "🔍 Checking Resource Group: $RG_NAME"
echo ""

# Check if resource group exists
if ! az group show --name $RG_NAME &>/dev/null; then
    echo "❌ Resource group '$RG_NAME' not found!"
    echo "Available resource groups:"
    az group list --query "[].name" -o tsv
    exit 1
fi

echo "✅ Resource group exists"
echo ""

# List ALL resources with details
echo "📦 ALL RESOURCES IN RESOURCE GROUP:"
echo "===================================="
az resource list --resource-group $RG_NAME --output table
echo ""

# Check Container Apps
echo "🐳 CONTAINER APPS:"
echo "=================="
CONTAINER_APPS=$(az containerapp list --resource-group $RG_NAME --query "[].{Name:name, Status:properties.provisioningState, URL:properties.configuration.ingress.fqdn}" -o table)
if [ -z "$CONTAINER_APPS" ]; then
    echo "❌ No Container Apps found"
else
    echo "$CONTAINER_APPS"
fi
echo ""

# Check Static Web Apps
echo "🌐 STATIC WEB APPS:"
echo "==================="
STATIC_APPS=$(az staticwebapp list --resource-group $RG_NAME --query "[].{Name:name, Status:properties.provisioningState, DefaultHostname:properties.defaultHostname, CustomDomains:properties.customDomains}" -o table)
if [ -z "$STATIC_APPS" ]; then
    echo "❌ No Static Web Apps found"
else
    echo "$STATIC_APPS"
fi
echo ""

# Check SQL Server & Database
echo "🗄️  SQL SERVER & DATABASES:"
echo "============================"
SQL_SERVERS=$(az sql server list --resource-group $RG_NAME --query "[].{Name:name, Location:location, AdminLogin:administratorLogin}" -o table)
if [ -z "$SQL_SERVERS" ]; then
    echo "❌ No SQL Servers found"
else
    echo "$SQL_SERVERS"
    echo ""
    for server in $(az sql server list --resource-group $RG_NAME --query "[].name" -o tsv); do
        echo "  Databases on $server:"
        az sql db list --resource-group $RG_NAME --server $server --query "[].{Name:name, Status:status, Size:maxSizeBytes}" -o table
    done
fi
echo ""

# Check Storage Accounts
echo "💾 STORAGE ACCOUNTS:"
echo "===================="
STORAGE=$(az storage account list --resource-group $RG_NAME --query "[].{Name:name, Location:location, SKU:sku.name}" -o table)
if [ -z "$STORAGE" ]; then
    echo "❌ No Storage Accounts found"
else
    echo "$STORAGE"
fi
echo ""

# Check AI Search
echo "🔍 AI SEARCH SERVICES:"
echo "======================"
SEARCH=$(az search service list --resource-group $RG_NAME --query "[].{Name:name, Location:location, SKU:sku.name, Status:provisioningState}" -o table)
if [ -z "$SEARCH" ]; then
    echo "⚠️  No AI Search in this RG (might be using existing from another RG)"
else
    echo "$SEARCH"
fi
echo ""

# Check Redis
echo "🔴 REDIS CACHE:"
echo "==============="
REDIS=$(az redis list --resource-group $RG_NAME --query "[].{Name:name, Location:location, SKU:sku.name, Status:provisioningState}" -o table 2>/dev/null || echo "")
if [ -z "$REDIS" ]; then
    echo "✅ No Redis (good - we removed it)"
else
    echo "⚠️  REDIS FOUND (should be deleted):"
    echo "$REDIS"
fi
echo ""

# Check Key Vault
echo "🔑 KEY VAULT:"
echo "============="
KEYVAULT=$(az keyvault list --resource-group $RG_NAME --query "[].{Name:name, Location:location}" -o table 2>/dev/null || echo "")
if [ -z "$KEYVAULT" ]; then
    echo "✅ No Key Vault (good - we removed it)"
else
    echo "⚠️  KEY VAULT FOUND (should be deleted):"
    echo "$KEYVAULT"
fi
echo ""

# Check Container Registry
echo "📦 CONTAINER REGISTRY:"
echo "======================"
ACR=$(az acr list --resource-group $RG_NAME --query "[].{Name:name, LoginServer:loginServer, SKU:sku.name}" -o table)
if [ -z "$ACR" ]; then
    echo "❌ No Container Registry found"
else
    echo "$ACR"
    echo ""
    for acr_name in $(az acr list --resource-group $RG_NAME --query "[].name" -o tsv); do
        echo "  Images in $acr_name:"
        az acr repository list --name $acr_name --output table 2>/dev/null || echo "  (No images yet)"
    done
fi
echo ""

# Check Application Insights (commented out due to script hang)
# echo "📊 APPLICATION INSIGHTS:"
# echo "========================"
# APPINSIGHTS=$(az monitor app-insights component show --resource-group $RG_NAME --query "[].{Name:name, Location:location, AppId:appId}" -o table 2>/dev/null || echo "")
# if [ -z "$APPINSIGHTS" ]; then
#     echo "❌ No Application Insights found"
# else
#     echo "$APPINSIGHTS"
# fi
# echo ""

# Detailed Static Web App Configuration
echo "🌐 STATIC WEB APP DETAILED CONFIG:"
echo "==================================="
for app in $(az staticwebapp list --resource-group $RG_NAME --query "[].name" -o tsv); do
    echo "Static App: $app"
    az staticwebapp show --name $app --resource-group $RG_NAME --query "{Name:name, DefaultHostname:properties.defaultHostname, RepositoryUrl:properties.repositoryUrl, Branch:properties.branch, BuildLocation:properties.buildProperties.appLocation, Status:properties.provisioningState}" -o json
    echo ""
done

# Check for orphaned/deleted resources
echo "🗑️  CHECKING FOR ISSUES:"
echo "========================"

# Check if there are any failed deployments
echo "Recent deployments:"
az deployment group list --resource-group $RG_NAME --query "[].{Name:name, State:properties.provisioningState, Timestamp:properties.timestamp}" --output table | head -10

echo ""
echo "=========================================="
echo "✅ Diagnostic Complete!"
echo "=========================================="
echo ""
echo "📋 SUMMARY:"
echo "==========="
TOTAL_RESOURCES=$(az resource list --resource-group $RG_NAME --query "length(@)")
echo "Total resources in $RG_NAME: $TOTAL_RESOURCES"
echo ""
echo "💡 Next Steps:"
echo "1. Review the output above"
echo "2. Check for any '⚠️' warnings"
echo "3. Verify URLs are working"
echo ""
