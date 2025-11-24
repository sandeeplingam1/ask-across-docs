# Azure Infrastructure for Audit App Production

This directory contains Infrastructure as Code (IaC) templates for deploying the Audit App to Azure.

## Resources Deployed

1. **Azure OpenAI** - AI services for embeddings and chat
2. **Azure AI Search** - Vector database for document chunks
3. **Azure SQL Database** - Relational database for metadata
4. **Azure Blob Storage** - File storage for uploaded documents
5. **Azure Storage Queue** - Message queue for background processing
6. **Azure Container Apps** - Backend API hosting
7. **Azure Static Web Apps** - Frontend hosting
8. **Azure Key Vault** - Secrets management
9. **Azure Application Insights** - Monitoring and logging
10. **Azure Cache for Redis** - Caching and session storage

## Deployment Options

### Option 1: Azure CLI with Bicep (Recommended)
```bash
cd infrastructure
./deploy.sh
```

### Option 2: Azure Portal
Use the `main.bicep` template in the Azure Portal

### Option 3: Terraform
Use the terraform configuration in `terraform/` directory

## Cost Estimates

### Development/Staging Environment
- ~$100-200/month
- Basic tiers for most services
- Auto-shutdown capabilities

### Production Environment
- ~$300-700/month
- Standard tiers with HA
- Auto-scaling enabled
- Depends on usage

## Prerequisites

1. Azure CLI installed
2. Azure subscription with permissions
3. Resource group created
4. Azure OpenAI access approved

## Configuration

Copy `.env.production.example` to `.env.production` and fill in values.
