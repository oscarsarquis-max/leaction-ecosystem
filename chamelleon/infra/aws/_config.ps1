# Configuracao AWS — Chamelleon (EC2 simples + Route53 + HTTPS)

$script:ChamelleonAws = @{
    Account          = '253137917703'
    Region           = 'us-east-2'
    HostedZoneId     = 'Z0992149RQUOCOE40JMA'
    Domain           = 'chamelleon.com.br'
    WwwDomain        = 'www.chamelleon.com.br'
    KeyName          = 'paneldx-bastion-key'
    InstanceType     = 't3.small'
    AmiId            = 'ami-0cf6185a5bb26f705'  # Ubuntu 22.04 LTS us-east-2
    VpcId            = 'vpc-0e05974106395b2b4'
    SubnetId         = 'subnet-0a8390bebcb0f6dd8'
    SecurityGroupName = 'chamelleon-web-sg'
    InstanceName     = 'chamelleon-web-01'
    CertbotEmail     = 'sysadmin@leaction.com.br'
    AppRoot          = '/opt/chamelleon'
    ApiPort          = 5010
}

function Get-ChamelleonRepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
}
