#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$certs = Join-Path $root "ops\compose\https-trial\certs"
New-Item -ItemType Directory -Force -Path $certs | Out-Null

function Assert-NativeExit {
  param([Parameter(Mandatory = $true)][string] $Step)
  if ($null -eq $LASTEXITCODE -or $LASTEXITCODE -ne 0) {
    $code = if ($null -eq $LASTEXITCODE) { 1 } else { $LASTEXITCODE }
    Write-Error "$Step failed with exit code $code."
    exit $code
  }
}

function Resolve-OpenSsl {
  $candidates = @(
    "openssl",
    "C:\Program Files\Git\usr\bin\openssl.exe",
    "C:\Program Files\Git\mingw64\bin\openssl.exe"
  )
  foreach ($item in $candidates) {
    $cmd = Get-Command $item -ErrorAction SilentlyContinue
    if ($cmd) {
      return $cmd.Source
    }
    if (Test-Path -LiteralPath $item) {
      return $item
    }
  }
  throw "openssl is required to generate disposable HTTPS trial certificates."
}

$openssl = Resolve-OpenSsl
$keytool = (Get-Command keytool -ErrorAction SilentlyContinue)
if (-not $keytool) {
  throw "keytool (Java) is required to generate the trial truststore."
}

$caKey = Join-Path $certs "ca-key.pem"
$caPem = Join-Path $certs "ca.pem"
$serverKey = Join-Path $certs "trial-key.pem"
$serverCsr = Join-Path $certs "trial.csr"
$serverPem = Join-Path $certs "trial.pem"
$extFile = Join-Path $certs "san.cnf"
$idpP12 = Join-Path $certs "idp.p12"
$trust = Join-Path $certs "truststore.p12"
$pass = "trial-only-not-for-production"

@"
basicConstraints=CA:FALSE
subjectAltName=DNS:finance.trial.localhost,DNS:idp.trial.localhost
"@ | Set-Content -LiteralPath $extFile -Encoding ascii

& $openssl req -x509 -newkey rsa:2048 -days 2 -nodes -keyout $caKey -out $caPem -subj "/CN=ActionFinance HTTPS trial CA"
Assert-NativeExit "openssl CA"
& $openssl req -newkey rsa:2048 -nodes -keyout $serverKey -out $serverCsr -subj "/CN=finance.trial.localhost"
Assert-NativeExit "openssl CSR"
& $openssl x509 -req -in $serverCsr -CA $caPem -CAkey $caKey -CAcreateserial -out $serverPem -days 2 -extfile $extFile
Assert-NativeExit "openssl sign"
& $openssl pkcs12 -export -in $serverPem -inkey $serverKey -certfile $caPem -out $idpP12 -name trial -passout "pass:$pass"
Assert-NativeExit "openssl pkcs12"

if (Test-Path -LiteralPath $trust) {
  Remove-Item -LiteralPath $trust -Force
}
& $keytool.Source -importcert -noprompt -alias trial-ca -file $caPem -keystore $trust -storetype PKCS12 -storepass $pass
Assert-NativeExit "keytool truststore"

Write-Host "Generated disposable HTTPS trial certificates in ops/compose/https-trial/certs (gitignored private material)."
Write-Host "These files are exclusive to the local trial. They are not a production CA and must not enter the application image."
