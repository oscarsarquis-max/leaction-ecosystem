$ErrorActionPreference = "Stop"
$dir = "C:\Temp\loja-ssh-p90"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
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
Write-Output "ssh_ready $ip"
