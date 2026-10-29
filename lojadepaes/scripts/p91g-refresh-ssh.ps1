$ErrorActionPreference = "Stop"
$dir = "C:\Temp\loja-ssh-p91g-" + (Get-Date -Format "HHmmss")
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Set-Content -Path "C:\Temp\loja-ssh-p91g-current.txt" -Value $dir -Encoding ascii
$raw = aws lightsail get-instance-access-details --region us-east-2 --instance-name lojadepaes-app --output json | ConvertFrom-Json
$ip = (Invoke-RestMethod -Uri "https://api.ipify.org").Trim()
aws lightsail open-instance-public-ports --region us-east-2 --instance-name lojadepaes-app --port-info "fromPort=22,toPort=22,protocol=tcp,cidrs=$ip/32" | Out-Null
Set-Content -Path "$dir\id_loja" -Value $raw.accessDetails.privateKey -Encoding ascii
Set-Content -Path "$dir\id_loja-cert.pub" -Value $raw.accessDetails.certKey -Encoding ascii
@"
Host lojadepaes
  HostName 52.15.107.86
  User ubuntu
  IdentitiesOnly yes
  IdentityFile $dir\id_loja
  CertificateFile $dir\id_loja-cert.pub
  StrictHostKeyChecking accept-new
"@ | Set-Content -Path "$dir\ssh_config" -Encoding ascii
$key = Join-Path $dir "id_loja"
$acl = Get-Acl $key
$acl.SetAccessRuleProtection($true, $false)
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
  [System.Security.Principal.WindowsIdentity]::GetCurrent().Name,
  "Read",
  "Allow"
)
$acl.AddAccessRule($rule)
Set-Acl -Path $key -AclObject $acl
Write-Output "ssh_ready $ip $dir"
