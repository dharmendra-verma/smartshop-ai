targetScope = 'subscription'

@description('Environment name (staging or prod)')
param environmentName string

@description('Azure region for resources')
param location string = 'eastus'

@description('ACR SKU')
param acrSku string = 'Basic'

@description('PostgreSQL SKU name')
param dbSkuName string = 'Standard_B1ms'

@description('Redis SKU')
param redisSku string = 'Basic'

@description('API minimum replicas')
param apiMinReplicas int = 1

@description('API maximum replicas')
param apiMaxReplicas int = 5

@description('UI minimum replicas')
param uiMinReplicas int = 1

@description('UI maximum replicas')
param uiMaxReplicas int = 3

@description('PostgreSQL administrator login')
param dbAdminLogin string = 'smartshopadmin'

@secure()
@description('PostgreSQL administrator password')
param dbAdminPassword string

// Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: 'rg-smartshop-${environmentName}'
  location: location
}

// Deploy all resources into the resource group
module resources 'modules/resources.bicep' = {
  name: 'smartshop-resources-${environmentName}'
  scope: rg
  params: {
    environmentName: environmentName
    location: location
    acrSku: acrSku
    dbSkuName: dbSkuName
    redisSku: redisSku
    apiMinReplicas: apiMinReplicas
    apiMaxReplicas: apiMaxReplicas
    uiMinReplicas: uiMinReplicas
    uiMaxReplicas: uiMaxReplicas
    dbAdminLogin: dbAdminLogin
    dbAdminPassword: dbAdminPassword
  }
}

output resourceGroupName string = rg.name
output acrLoginServer string = resources.outputs.acrLoginServer
output apiUrl string = resources.outputs.apiUrl
output uiUrl string = resources.outputs.uiUrl
