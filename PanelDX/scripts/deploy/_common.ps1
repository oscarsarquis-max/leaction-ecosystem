# Funções compartilhadas — deploy PanelDX

. (Join-Path $PSScriptRoot '_config.ps1')

function Write-DeployStep([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Write-DeployOk([string]$Message) {
    Write-Host "    [OK] $Message" -ForegroundColor Green
}

function Write-DeployWarn([string]$Message) {
    Write-Host "    [!]  $Message" -ForegroundColor Yellow
}

function Get-AwsSslArgs([bool]$VerifySsl) {
    if ($VerifySsl) { return @() }
    return @('--no-verify-ssl')
}

function Invoke-DeployNative {
    param(
        [Parameter(Mandatory)][string]$Exe,
        [Parameter(ValueFromRemainingArguments)][string[]]$CmdArgs
    )
    & $Exe @CmdArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Comando falhou (exit $LASTEXITCODE): $Exe $($CmdArgs -join ' ')"
    }
}

function Invoke-DeployAws {
    param(
        [bool]$VerifySsl = $false,
        [Parameter(ValueFromRemainingArguments)][string[]]$CmdArgs
    )
    $ssl = Get-AwsSslArgs $VerifySsl
    $full = @($CmdArgs) + $ssl
    $quoted = ($full | ForEach-Object {
            if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
        }) -join ' '
    $out = cmd /c "aws $quoted 2>nul"
    if ($LASTEXITCODE -ne 0) {
        $err = cmd /c "aws $quoted 2>&1"
        throw "AWS CLI falhou (exit $LASTEXITCODE): aws $($CmdArgs -join ' ')`n$err"
    }
    if ($null -eq $out) { return '' }
    if ($out -is [array]) { return ($out -join "`n").Trim() }
    return "$out".Trim()
}

function Test-DeployPrerequisites {
    param(
        [string]$Account,
        [bool]$VerifySsl = $false
    )
    Write-DeployStep 'Verificando docker, aws e identidade AWS'
    Invoke-DeployNative docker --version | Out-Null
    Invoke-DeployNative aws --version | Out-Null
    $ident = Invoke-DeployAws -VerifySsl:$VerifySsl sts get-caller-identity --output json | ConvertFrom-Json
    if ($ident.Account -ne $Account) {
        throw "Conta AWS ativa ($($ident.Account)) difere da esperada ($Account). Abortei por seguranca."
    }
    Write-DeployOk "Conta $($ident.Account)"
    return $ident
}

function Connect-DeployEcr {
    param(
        [string]$Registry,
        [string]$Region,
        [bool]$VerifySsl = $false
    )
    Write-DeployStep "Login no ECR ($Registry)"
    $pw = Invoke-DeployAws -VerifySsl:$VerifySsl ecr get-login-password --region $Region
    $pw | docker login --username AWS --password-stdin $Registry
    if ($LASTEXITCODE -ne 0) { throw 'docker login no ECR falhou.' }
    Write-DeployOk "Autenticado em $Registry"
}

function Publish-DeployImages {
    param(
        [string]$Tag,
        [string]$Registry,
        [object[]]$Services,
        [string]$RepoRoot
    )
    foreach ($s in $Services) {
        $image = "$Registry/$($s.Repo):$Tag"
        $df = Join-Path $RepoRoot $s.Dockerfile
        $ctx = Join-Path $RepoRoot $s.Context

        Write-DeployStep "BUILD $($s.Name) -> $image"
        if (-not (Test-Path $df)) { throw "Dockerfile nao encontrado: $df" }
        if (-not (Test-Path $ctx)) { throw "Contexto nao encontrado: $ctx" }

        Invoke-DeployNative docker build -f $df -t $image $ctx
        Write-DeployStep "PUSH $($s.Name)"
        Invoke-DeployNative docker push $image
        Write-DeployOk "Publicado $image"
    }
}

function Merge-DeployContainerEnvironment {
    param(
        [object]$Container,
        [hashtable]$Vars
    )
    if (-not $Vars -or $Vars.Count -eq 0) { return }

    $byName = @{}
    if ($Container.environment) {
        foreach ($entry in $Container.environment) {
            $byName[$entry.name] = $entry.value
        }
    }
    foreach ($key in $Vars.Keys) {
        $byName[$key] = [string]$Vars[$key]
    }
    $Container.environment = @(
        foreach ($key in ($byName.Keys | Sort-Object)) {
            @{ name = $key; value = $byName[$key] }
        }
    )
}

function Merge-DeployContainerSecrets {
    param(
        [object]$Container,
        [object[]]$Secrets
    )
    if (-not $Secrets -or $Secrets.Count -eq 0) { return }

    $byName = @{}
    if ($Container.secrets) {
        foreach ($entry in $Container.secrets) {
            $byName[$entry.name] = $entry.valueFrom
        }
    }
    foreach ($entry in $Secrets) {
        $byName[$entry.name] = $entry.valueFrom
    }
    $Container.secrets = @(
        foreach ($key in ($byName.Keys | Sort-Object)) {
            @{ name = $key; valueFrom = $byName[$key] }
        }
    )
}

function Update-DeployEcsServices {
    param(
        [string]$Tag,
        [string]$Registry,
        [string]$Region,
        [string]$Cluster,
        [object[]]$Services,
        [bool]$VerifySsl = $false
    )
    foreach ($s in $Services) {
        $image = "$Registry/$($s.Repo):$Tag"
        Write-DeployStep "ECS $($s.Name): nova revisao de '$($s.Family)' -> $Tag"

        $td = (Invoke-DeployAws -VerifySsl:$VerifySsl ecs describe-task-definition `
                --task-definition $s.Family --region $Region `
                --query 'taskDefinition' --output json) | ConvertFrom-Json

        $matched = 0
        foreach ($c in $td.containerDefinitions) {
            if ($c.image -match ('/' + [regex]::Escape($s.Repo) + ':')) {
                $c.image = $image
                $matched++
            }
        }
        if ($matched -eq 0) {
            Write-DeployWarn "Nenhum container em '$($s.Family)' referencia '$($s.Repo)'. Pulando."
            continue
        }

        $hubVars = $script:DeployHubIntegration[$s.Name]
        if ($hubVars) {
            foreach ($c in $td.containerDefinitions) {
                if ($c.image -match ('/' + [regex]::Escape($s.Repo) + ':')) {
                    Merge-DeployContainerEnvironment -Container $c -Vars $hubVars
                }
            }
            Write-DeployOk "Variaveis Action Hub aplicadas em $($s.Name)"
        }

        if ($s.Name -eq 'frontend' -and $script:DeployGatekeeperFrontend) {
            $gkVars = @{}
            foreach ($k in $script:DeployGatekeeperFrontend.Keys) {
                $gkVars[$k] = $script:DeployGatekeeperFrontend[$k]
            }
            if ($env:PRODUCTION_MASTER_KEY) {
                $gkVars['PRODUCTION_MASTER_KEY'] = $env:PRODUCTION_MASTER_KEY
            } elseif (-not $gkVars['PRODUCTION_MASTER_KEY']) {
                Write-DeployWarn 'PRODUCTION_MASTER_KEY nao definida no ambiente do deploy; gatekeeper bypass/unlock falhara em producao.'
            }
            foreach ($c in $td.containerDefinitions) {
                if ($c.image -match ('/' + [regex]::Escape($s.Repo) + ':')) {
                    Merge-DeployContainerEnvironment -Container $c -Vars $gkVars
                    if ($script:DeployGatekeeperFrontendSecrets) {
                        Merge-DeployContainerSecrets -Container $c -Secrets $script:DeployGatekeeperFrontendSecrets
                    }
                }
            }
            Write-DeployOk 'Variaveis Gatekeeper aplicadas no frontend (DB + NODE_ENV)'
        }

        $allowed = @(
            'family', 'taskRoleArn', 'executionRoleArn', 'networkMode', 'containerDefinitions',
            'volumes', 'placementConstraints', 'requiresCompatibilities', 'cpu', 'memory',
            'tags', 'pidMode', 'ipcMode', 'proxyConfiguration', 'inferenceAccelerators',
            'ephemeralStorage', 'runtimePlatform'
        )
        $tdInput = [ordered]@{}
        foreach ($k in $allowed) {
            if ($null -ne $td.PSObject.Properties[$k] -and $null -ne $td.$k) {
                $tdInput[$k] = $td.$k
            }
        }

        if ($s.Name -eq 'frontend' -and $script:DeployFrontendTaskRoleArn) {
            $tdInput['taskRoleArn'] = $script:DeployFrontendTaskRoleArn
            Write-DeployOk 'Task role IAM aplicada no frontend (S3 CMS)'
        }

        $tmp = Join-Path $env:TEMP ("taskdef_{0}_{1}.json" -f $s.Name, ([guid]::NewGuid().ToString('N')))
        $json = $tdInput | ConvertTo-Json -Depth 100
        [System.IO.File]::WriteAllText($tmp, $json, (New-Object System.Text.UTF8Encoding($false)))

        try {
            $reg = (Invoke-DeployAws -VerifySsl:$VerifySsl ecs register-task-definition `
                    --region $Region --cli-input-json ("file://" + $tmp) --output json) | ConvertFrom-Json
            $newRev = "$($reg.taskDefinition.family):$($reg.taskDefinition.revision)"
            Write-DeployOk "Registrada task definition $newRev"

            Invoke-DeployAws -VerifySsl:$VerifySsl ecs update-service `
                --cluster $Cluster --service $s.Service `
                --task-definition $newRev --region $Region --output json | Out-Null
            Write-DeployOk "Servico '$($s.Service)' atualizado para $newRev"
        }
        finally {
            Remove-Item $tmp -ErrorAction SilentlyContinue
        }
    }
}

function Show-DeployWaitCommands {
    param(
        [string]$Cluster,
        [string]$Region,
        [object[]]$Services,
        [bool]$VerifySsl = $false
    )
    $ssl = Get-AwsSslArgs $VerifySsl
    Write-DeployStep 'Acompanhe a estabilizacao com:'
    foreach ($s in $Services) {
        Write-Host ("    aws ecs wait services-stable --cluster {0} --services {1} --region {2} {3}" -f `
                $Cluster, $s.Service, $Region, ($ssl -join ' ')) -ForegroundColor DarkGray
    }
}
