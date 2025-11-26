// Clean Audit App Infrastructure - Production Ready
// Removed: Redis, Queue Storage, unused features
// Optimized for actual usage patterns

targetScope = 'resourceGroup'

@description('Environment name (dev, staging, prod)')
param environment string = 'prod'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Application name prefix')
param appName string = 'auditapp'

@description('Unique suffix for globally unique names')
param uniqueSuffix string = uniqueString(resourceGroup().id)

@description('Use existing AI Search service instead of creating new')
param useExistingAISearch bool = false

@description('Existing AI Search service name (if useExistingAISearch is true)')
param existingAISearchName string = ''

@description('Existing AI Search resource group (if useExistingAISearch is true)')
param existingAISearchRG string = ''

@description('Use existing Storage Account instead of creating new')
param useExistingStorage bool = false

@description('Existing Storage Account name (if useExistingStorage is true)')
param existingStorageAccountName string = ''

@description('Existing Storage Account resource group (if useExistingStorage is true)')
param existingStorageAccountRG string = ''

@description('Azure OpenAI API Key')
@secure()
param azureOpenAIApiKey string

@description('SQL Admin Password')
@secure()
param sqlAdminPassword string = 'P@ssw0rd123!'

// Variables
var resourcePrefix = '${appName}-${environment}'
var tags = {
  Environment: environment
  Application: 'AuditApp'
  ManagedBy: 'Bicep'
}

// ===================================
// Azure SQL Database
// ===================================
resource sqlServer 'Microsoft.Sql/servers@2023-02-01-preview' = {
  name: '${resourcePrefix}-sql-${uniqueSuffix}'
  location: location
  tags: tags
  properties: {
    administratorLogin: 'sqladmin'
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-02-01-preview' = {
  parent: sqlServer
  name: '${resourcePrefix}-db'
  location: location
  tags: tags
  sku: {
    name: environment == 'prod' ? 'S1' : 'Basic'
    tier: environment == 'prod' ? 'Standard' : 'Basic'
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: 2147483648 // 2GB
  }
}

resource sqlFirewallRule 'Microsoft.Sql/servers/firewallRules@2023-02-01-preview' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// ===================================
// Azure Storage Account
// ===================================
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = if (!useExistingStorage) {
  name: '${replace(resourcePrefix, '-', '')}st${uniqueSuffix}'
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

// Reference to existing storage account
resource existingStorageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = if (useExistingStorage) {
  name: existingStorageAccountName
  scope: resourceGroup(existingStorageAccountRG)
}

// Blob container for documents
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = if (!useExistingStorage) {
  parent: storageAccount
  name: 'default'
}

resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = if (!useExistingStorage) {
  parent: blobService
  name: 'audit-${environment}-documents'
  properties: {
    publicAccess: 'None'
  }
}

// ===================================
// Azure AI Search
// ===================================
resource searchService 'Microsoft.Search/searchServices@2023-11-01' = if (!useExistingAISearch) {
  name: '${resourcePrefix}-search-${uniqueSuffix}'
  location: location
  tags: tags
  sku: {
    name: environment == 'prod' ? 'standard' : 'basic'
  }
  properties: {
    replicaCount: environment == 'prod' ? 2 : 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
  }
}

// Reference to existing AI Search service
resource existingSearchService 'Microsoft.Search/searchServices@2023-11-01' existing = if (useExistingAISearch) {
  name: existingAISearchName
  scope: resourceGroup(existingAISearchRG)
}

// ===================================
// Application Insights & Monitoring
// ===================================
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${resourcePrefix}-logs-${uniqueSuffix}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${resourcePrefix}-insights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ===================================
// Azure Container Registry
// ===================================
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: '${replace(resourcePrefix, '-', '')}acr${uniqueSuffix}'
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// ===================================
// Azure Container Apps Environment
// ===================================
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${resourcePrefix}-containerenv'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ===================================
// Backend Container App
// ===================================
resource backendContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-backend'
  location: location
  tags: tags
  properties: {
    environmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
        {
          name: 'database-url'
          value: 'mssql+aioodbc://sqladmin:${uriComponent(sqlAdminPassword)}@${sqlServer.properties.fullyQualifiedDomainName}:1433/${sqlDatabase.name}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30'
        }
        {
          name: 'azure-search-api-key'
          value: useExistingAISearch ? existingSearchService.listAdminKeys().primaryKey : searchService.listAdminKeys().primaryKey
        }
        {
          name: 'storage-connection-string'
          value: useExistingStorage ? 'DefaultEndpointsProtocol=https;AccountName=${existingStorageAccount.name};AccountKey=${existingStorageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net' : 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'azure-openai-api-key'
          value: azureOpenAIApiKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: '${containerRegistry.properties.loginServer}/auditapp-backend:latest'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            {
              name: 'ENVIRONMENT'
              value: environment
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: 'https://cog-obghpsbi63abq.openai.azure.com/'
            }
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'azure-openai-api-key'
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: '2024-02-15-preview'
            }
            {
              name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
              value: 'text-embedding-3-large'
            }
            {
              name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
              value: 'gpt-4.1-mini'
            }
            {
              name: 'VECTOR_DB_TYPE'
              value: 'azure_search'
            }
            {
              name: 'AZURE_SEARCH_ENDPOINT'
              value: useExistingAISearch ? 'https://${existingSearchService.name}.search.windows.net' : 'https://${searchService.name}.search.windows.net'
            }
            {
              name: 'AZURE_SEARCH_API_KEY'
              secretRef: 'azure-search-api-key'
            }
            {
              name: 'AZURE_SEARCH_INDEX_NAME'
              value: 'audit-${environment}-documents'
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection-string'
            }
            {
              name: 'AZURE_STORAGE_CONTAINER_NAME'
              value: 'audit-${environment}-documents'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsights.properties.ConnectionString
            }
            {
              name: 'ENABLE_TELEMETRY'
              value: 'true'
            }
            {
              name: 'BACKEND_CORS_ORIGINS'
              value: 'https://${resourcePrefix}-frontend.azurestaticapps.net,http://localhost:5173'
            }
          ]
        }
      ]
      scale: {
        minReplicas: environment == 'prod' ? 2 : 1
        maxReplicas: environment == 'prod' ? 10 : 3
      }
    }
  }
}

// ===================================
// Frontend Static Web App
// ===================================
resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: '${resourcePrefix}-frontend'
  location: 'eastus2'  // Static Web Apps not available in all regions
  tags: tags
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    repositoryUrl: 'https://github.com/sandeeplingam1/Audit-App'
    branch: 'main'
    buildProperties: {
      appLocation: '/frontend'
      apiLocation: ''
      outputLocation: 'dist'
    }
  }
}

// Configure Static Web App settings
resource staticWebAppSettings 'Microsoft.Web/staticSites/config@2023-01-01' = {
  parent: staticWebApp
  name: 'appsettings'
  properties: {
    VITE_API_URL: 'https://${backendContainerApp.properties.configuration.ingress.fqdn}'
  }
}

// ===================================
// Outputs
// ===================================
output sqlServerName string = sqlServer.name
output sqlDatabaseName string = sqlDatabase.name
output sqlConnectionString string = 'Server=tcp:${sqlServer.properties.fullyQualifiedDomainName},1433;Initial Catalog=${sqlDatabase.name};Persist Security Info=False;User ID=sqladmin;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;'
output storageAccountName string = useExistingStorage ? existingStorageAccount.name : storageAccount.name
output storageConnectionString string = useExistingStorage ? 'DefaultEndpointsProtocol=https;AccountName=${existingStorageAccount.name};AccountKey=${existingStorageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net' : 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
output searchServiceName string = useExistingAISearch ? existingSearchService.name : searchService.name
output searchEndpoint string = useExistingAISearch ? 'https://${existingSearchService.name}.search.windows.net' : 'https://${searchService.name}.search.windows.net'
output searchApiKey string = useExistingAISearch ? existingSearchService.listAdminKeys().primaryKey : searchService.listAdminKeys().primaryKey
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output containerRegistryName string = containerRegistry.name
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output containerAppsEnvironmentName string = containerAppEnv.name

// Application URLs
output backendUrl string = 'https://${backendContainerApp.properties.configuration.ingress.fqdn}'
output backendFqdn string = backendContainerApp.properties.configuration.ingress.fqdn
output frontendUrl string = 'https://${staticWebApp.properties.defaultHostname}'
output frontendHostname string = staticWebApp.properties.defaultHostname
