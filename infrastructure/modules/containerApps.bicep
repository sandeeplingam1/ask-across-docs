// Container Apps module for backend deployment
param location string
param environment string
param containerAppsEnvironmentId string
param containerRegistryName string
param containerRegistryUsername string
@secure()
param containerRegistryPassword string
param backendImage string = 'auditapp-backend:latest'

// Environment variables from outputs of other resources
param databaseConnectionString string
param azureOpenAIEndpoint string
param azureOpenAIEmbeddingDeployment string
param azureOpenAIChatDeployment string
param azureSearchEndpoint string
@secure()
param azureSearchApiKey string
param azureSearchIndexName string
param azureStorageConnectionString string
param azureStorageContainerName string
param redisConnectionString string
param applicationInsightsConnectionString string

var tags = {
  Environment: environment
  Application: 'AuditApp'
  ManagedBy: 'Bicep'
}

// Backend Container App
resource backendContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'auditapp-backend'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: '${containerRegistryName}.azurecr.io'
          username: containerRegistryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistryPassword
        }
        {
          name: 'database-connection-string'
          value: databaseConnectionString
        }
        {
          name: 'azure-search-api-key'
          value: azureSearchApiKey
        }
        {
          name: 'azure-storage-connection-string'
          value: azureStorageConnectionString
        }
        {
          name: 'redis-connection-string'
          value: redisConnectionString
        }
        {
          name: 'application-insights-connection-string'
          value: applicationInsightsConnectionString
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'auditapp-backend'
          image: '${containerRegistryName}.azurecr.io/${backendImage}'
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
              secretRef: 'database-connection-string'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAIEndpoint
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: '2024-02-15-preview'
            }
            {
              name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
              value: azureOpenAIEmbeddingDeployment
            }
            {
              name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
              value: azureOpenAIChatDeployment
            }
            {
              name: 'AZURE_SEARCH_ENDPOINT'
              value: azureSearchEndpoint
            }
            {
              name: 'AZURE_SEARCH_API_KEY'
              secretRef: 'azure-search-api-key'
            }
            {
              name: 'AZURE_SEARCH_INDEX_NAME'
              value: azureSearchIndexName
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'azure-storage-connection-string'
            }
            {
              name: 'AZURE_STORAGE_CONTAINER_NAME'
              value: azureStorageContainerName
            }
            {
              name: 'REDIS_URL'
              secretRef: 'redis-connection-string'
            }
            {
              name: 'VECTOR_DB_TYPE'
              value: 'azure_search'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              secretRef: 'application-insights-connection-string'
            }
            {
              name: 'ENABLE_TELEMETRY'
              value: 'true'
            }
            {
              name: 'MAX_UPLOAD_SIZE_MB'
              value: '100'
            }
            {
              name: 'CHUNK_SIZE'
              value: '1000'
            }
            {
              name: 'CHUNK_OVERLAP'
              value: '200'
            }
            {
              name: 'BACKEND_CORS_ORIGINS'
              value: 'https://auditapp-${environment}-frontend.azurestaticapps.net,http://localhost:5173'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scale-rule'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
}

output backendUrl string = 'https://${backendContainerApp.properties.configuration.ingress.fqdn}'
output backendFqdn string = backendContainerApp.properties.configuration.ingress.fqdn
