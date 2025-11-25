// Container App Bicep Module
@description('Container App name')
param containerAppName string

@description('Location for resources')
param location string = resourceGroup().location

@description('Container Apps Environment ID')
param environmentId string

@description('Container image')
param containerImage string

@description('Container Registry server')
param registryServer string

@description('Container Registry username')
@secure()
param registryUsername string

@description('Container Registry password')
@secure()
param registryPassword string

@description('Target port for the container')
param targetPort int = 8000

@description('CPU cores')
param cpu string = '1.0'

@description('Memory')
param memory string = '2Gi'

@description('Min replicas')
param minReplicas int = 1

@description('Max replicas')
param maxReplicas int = 3

@description('Environment variables')
param environmentVariables array = []

@description('Tags')
param tags object = {}

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  tags: tags
  properties: {
    environmentId: environmentId
    configuration: {
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: registryServer
          username: registryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: registryPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: containerAppName
          image: containerImage
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: environmentVariables
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
output name string = containerApp.name
output id string = containerApp.id
