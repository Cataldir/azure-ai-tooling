param(
    [Parameter(Mandatory=$true)][string]$username,
    [Parameter(Mandatory=$true)][securestring]$password,
    [Parameter(Mandatory=$true)][string]$imageName,
    [Parameter(Mandatory=$true)][string]$imageVersion
)

# Login to Azure Container Registry
az acr login --name amlsandbox.azureacr.io --username ${username} --password ${password}

# Build the Docker image
docker build -t ${imageName} .

# Tag the Docker image
$tag = "${imageName}:${imageVersion}"
docker tag ${tag} amlsandbox.azureacr.io/${imageName}

# Push the Docker image
docker push amlsandbox.azurecr.io/${tag}