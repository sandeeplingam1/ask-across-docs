// Static Web App for frontend
param location string
param environment string
param backendUrl string

var tags = {
  Environment: environment
  Application: 'AuditApp'
  ManagedBy: 'Bicep'
}

// Static Web App (Free tier for staging, Standard for prod)
resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: 'auditapp-${environment}-frontend'
  location: location
  tags: tags
  sku: {
    name: environment == 'prod' ? 'Standard' : 'Free'
    tier: environment == 'prod' ? 'Standard' : 'Free'
  }
  properties: {
    repositoryUrl: 'https://github.com/sandeeplingam1/Audit-App'
    branch: 'main'
    buildProperties: {
      appLocation: '/frontend'
      apiLocation: ''
      outputLocation: 'dist'
      appBuildCommand: 'npm run build'
    }
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
    enterpriseGradeCdnStatus: 'Disabled'
  }
}

// Configure backend API URL as environment variable
resource staticWebAppSettings 'Microsoft.Web/staticSites/config@2023-01-01' = {
  parent: staticWebApp
  name: 'appsettings'
  properties: {
    VITE_API_URL: backendUrl
  }
}

output staticWebAppUrl string = 'https://${staticWebApp.properties.defaultHostname}'
output staticWebAppName string = staticWebApp.name
output staticWebAppHostname string = staticWebApp.properties.defaultHostname
