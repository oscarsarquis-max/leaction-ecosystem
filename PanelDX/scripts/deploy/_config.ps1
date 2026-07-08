# Configuração compartilhada — deploy PanelDX (AWS ECS / ECR)
# Editável por parâmetros nos scripts ou aqui para defaults da conta.

$script:DeployDefaults = @{
    Account  = '253137917703'
    Region   = 'us-east-2'
    Cluster  = 'paneldx-cluster'
    VerifySsl = $false
}

$script:DeployServices = @(
    [pscustomobject]@{
        Name       = 'backend'
        Repo       = 'paneldx-backend'
        Dockerfile = 'LeAction_SysF/Dockerfile.backend'
        Context    = 'LeAction_SysF'
        Service    = 'paneldx-backend-service'
        Family     = 'paneldx-backend-task'
    },
    [pscustomobject]@{
        Name       = 'worker'
        Repo       = 'leactionf-ai-processor'
        Dockerfile = 'LeAction_SysF/ai_engine/Dockerfile.ai'
        Context    = 'LeAction_SysF'
        Service    = 'leactionf-ai-worker-service'
        Family     = 'leactionf-ai-processor-task'
    },
    [pscustomobject]@{
        Name       = 'frontend'
        Repo       = 'paneldx-frontend'
        Dockerfile = 'LeAction_Sys_FE/Dockerfile.frontend'
        Context    = 'LeAction_Sys_FE'
        Service    = 'paneldx-frontend-service'
        Family     = 'paneldx-frontend-task'
    }
)

function Get-DeployRepoRoot {
    # scripts/deploy -> raiz PanelDX
    return (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
}

function Get-DeployServices {
    param([string[]]$Only)
    if ($Only -and $Only.Count -gt 0) {
        return $script:DeployServices | Where-Object { $Only -contains $_.Name }
    }
    return $script:DeployServices
}

# Variáveis de integração Action Hub — injetadas nas task definitions ECS em cada deploy.
# Domínios conforme produção atual (paneldx.com.br + actionhub.com.br).
# Task role do frontend — necessário para PutObject no S3 (upload CMS).
$script:DeployFrontendTaskRoleArn = 'arn:aws:iam::253137917703:role/paneldx-backend-task-role'

$script:DeployHubIntegration = @{
    frontend = @{
        BACKEND_URL                = 'https://paneldx.com.br'
        HUB_GATEWAY_INTERNAL_URL   = 'https://api.actionhub.com.br'
        HUB_PUBLIC_URL             = 'https://actionhub.com.br'
        HUB_WEBHOOK_URL            = 'https://paneldx.com.br/api/hub/payment-webhook'
        CMS_S3_BUCKET              = 'paneldx-cms-assets-2026'
        CMS_S3_PREFIX              = 'cms'
        CMS_S3_REGION              = 'us-east-2'
        ADMIN_EMAIL                = 'sysadmin@leaction.com.br'
    }
    backend = @{
        HUB_JWT_SECRET  = $(if ($env:HUB_JWT_SECRET) { $env:HUB_JWT_SECRET } else { 'super-secret-hub-key-2026' })
        HUB_API_URL     = 'https://api.actionhub.com.br'
        HUB_PUBLIC_URL  = 'https://actionhub.com.br'
        HUB_WEBHOOK_URL = 'https://paneldx.com.br/api/hub/payment-webhook'
    }
}

# Gatekeeper — frontend BFF consulta system_config no RDS (mesmo host do backend).
$script:DeployGatekeeperFrontend = @{
    NODE_ENV     = 'production'
    DB_HOST      = 'paneldx-database.czqyam2auctn.us-east-2.rds.amazonaws.com'
    DB_PORT      = '5432'
    DB_NAME      = 'LeAction_SysF'
    DB_SSLMODE   = 'require'
}

$script:DeployGatekeeperFrontendSecrets = @(
    @{
        name      = 'DB_USER'
        valueFrom = 'arn:aws:secretsmanager:us-east-2:253137917703:secret:paneldx-db-credentials-TLIqUc:username::'
    },
    @{
        name      = 'DB_PASS'
        valueFrom = 'arn:aws:secretsmanager:us-east-2:253137917703:secret:paneldx-db-credentials-TLIqUc:password::'
    }
)
