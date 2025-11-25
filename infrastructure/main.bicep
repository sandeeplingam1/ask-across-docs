// Main Bicep template for Audit App Production Infrastructure
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
    administratorLoginPassword: 'P@ssw0rd123!' // Change this!
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

// Queue for background processing
resource queueService 'Microsoft.Storage/storageAccounts/queueServices@2023-01-01' = if (!useExistingStorage) {
  parent: storageAccount
  name: 'default'
}

resource processingQueue 'Microsoft.Storage/storageAccounts/queueServices/queues@2023-01-01' = if (!useExistingStorage) {
  parent: queueService
  name: 'audit-${environment}-processing'
  properties: {}
}

// Note: If using existing storage, containers and queues must be created manually or via deployment script

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
// Azure Cache for Redis
// ===================================
resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: '${resourcePrefix}-redis-${uniqueSuffix}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: environment == 'prod' ? 'Standard' : 'Basic'
      family: 'C'
      capacity: environment == 'prod' ? 1 : 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
    }
  }
}

// ===================================
// Azure Key Vault
// ===================================
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${appName}-${take(uniqueSuffix, 10)}'
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// ===================================
// Application Insights
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
module backendApp 'modules/containerApps.bicep' = {
  name: 'backend-container-app'
  params: {
    location: location
    environment: environment
    containerAppsEnvironmentId: containerAppEnv.id
    containerRegistryName: containerRegistry.name
    containerRegistryUsername: containerRegistry.listCredentials().username
    containerRegistryPassword: containerRegistry.listCredentials().passwords[0].value
    backendImage: 'auditapp-backend:latest'
    databaseConnectionString: 'mssql+pyodbc://sqladmin:P@ssw0rd123!@${sqlServer.properties.fullyQualifiedDomainName}:1433/${sqlDatabase.name}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30'
    azureOpenAIEndpoint: 'https://cog-obghpsbi63abq.openai.azure.com/'
    azureOpenAIEmbeddingDeployment: 'text-embedding-3-large'
    azureOpenAIChatDeployment: 'gpt-4.1-mini'
    azureSearchEndpoint: useExistingAISearch ? 'https://${existingSearchService.name}.search.windows.net' : 'https://${searchService.name}.search.windows.net'
    azureSearchApiKey: useExistingAISearch ? existingSearchService.listAdminKeys().primaryKey : searchService.listAdminKeys().primaryKey
    azureSearchIndexName: 'audit-${environment}-documents'
    azureStorageConnectionString: useExistingStorage ? 'DefaultEndpointsProtocol=https;AccountName=${existingStorageAccount.name};AccountKey=${existingStorageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net' : 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
    azureStorageContainerName: 'audit-${environment}-documents'
    redisConnectionString: '${redis.properties.hostName}:6380,password=${redis.listKeys().primaryKey},ssl=True,abortConnect=False'
    applicationInsightsConnectionString: appInsights.properties.ConnectionString
  }
}

// ===================================
// Frontend Static Web App
// ===================================
module frontendApp 'modules/staticWebApp.bicep' = {
  name: 'frontend-static-web-app'
  params: {
    location: location
    environment: environment
    backendUrl: backendApp.outputs.backendUrl
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
output redisHostName string = redis.properties.hostName
output redisConnectionString string = '${redis.properties.hostName}:6380,password=${redis.listKeys().primaryKey},ssl=True,abortConnect=False'
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output containerRegistryName string = containerRegistry.name
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output containerAppsEnvironmentName string = containerAppEnv.name

// Application URLs
output backendUrl string = backendApp.outputs.backendUrl
output backendFqdn string = backendApp.outputs.backendFqdn
output frontendUrl string = frontendApp.outputs.staticWebAppUrl
output frontendHostname string = frontendApp.outputs.staticWebAppHostname
