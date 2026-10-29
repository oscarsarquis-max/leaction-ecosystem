# Compacta o disco virtual do Docker e devolve o espaço livre ao Windows.
# Exige PowerShell como administrador. Não apaga volume, imagem nem contêiner.
$ErrorActionPreference = "Stop"

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw "Rode este script numa janela de PowerShell como administrador."
}

$vhdx = Join-Path $env:LOCALAPPDATA "Docker\wsl\disk\docker_data.vhdx"
if (-not (Test-Path -LiteralPath $vhdx)) {
  throw "Disco virtual nao encontrado: $vhdx"
}

$cli = Join-Path $env:ProgramFiles "Docker\Docker\DockerCli.exe"
if (Test-Path -LiteralPath $cli) {
  & $cli -Shutdown
}
Get-Process -Name "Docker Desktop","com.docker.backend" -ErrorAction SilentlyContinue | Stop-Process -ErrorAction SilentlyContinue
wsl --shutdown
Start-Sleep -Seconds 8

$before = (Get-Item -LiteralPath $vhdx).Length
Write-Output ("vhdx_before_bytes " + $before)

if (Get-Module -ListAvailable -Name Hyper-V) {
  Import-Module Hyper-V
  Optimize-VHD -Path $vhdx -Mode Full
} else {
  $diskpartScript = Join-Path $env:TEMP "p107c-compact-diskpart.txt"
  @(
    "select vdisk file=`"$vhdx`""
    "attach vdisk readonly"
    "compact vdisk"
    "detach vdisk"
  ) | Set-Content -LiteralPath $diskpartScript -Encoding ASCII
  $output = diskpart /s $diskpartScript | Out-String
  Write-Output $output
  $ok = $output -match "successfully compacted|compactou o arquivo de disco virtual"
  if (-not $ok) {
    throw "diskpart nao confirmou a compactacao"
  }
}

$after = (Get-Item -LiteralPath $vhdx).Length
Write-Output ("vhdx_after_bytes " + $after)
Write-Output "compact_107c_done"
