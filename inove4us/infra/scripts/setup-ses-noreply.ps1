#Requires -Version 5.1
<#
.SYNOPSIS
  Garante identidade SES noreply@inove4us.com.br na região do SES (us-east-2).

.DESCRIPTION
  O domínio inove4us.com.br já está verificado em us-east-2 (produção SES).
  Este script cria/confirma a identidade de e-mail noreply@ e imprime o checklist
  de env do app (EMAIL_SENDER, SES_REGION, EMAIL_DEV_MODE).

  Usa credenciais do backend/.env (mesmo padrão do app).
#>
param(
  [string]$Region = "us-east-2",
  [string]$Sender = "noreply@inove4us.com.br",
  [string]$Domain = "inove4us.com.br",
  [string]$TestTo = ""
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$EnvFile = Join-Path $Root "backend\.env"
$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw "Venv ausente: $Py" }
if (-not (Test-Path $EnvFile)) { throw "Env ausente: $EnvFile" }

$tmp = Join-Path $env:TEMP ("inove-ses-setup-{0}.py" -f [guid]::NewGuid().ToString("N"))
@'
import os, sys
from dotenv import load_dotenv
import boto3

env_path, region, sender, domain, test_to = sys.argv[1:6]
load_dotenv(env_path)
ses = boto3.client("sesv2", region_name=region)
print(f"region={region}")

dom = ses.get_email_identity(EmailIdentity=domain)
print(f"domain {domain}: VerifiedForSending={dom.get('VerifiedForSendingStatus')} Dkim={(dom.get('DkimAttributes') or {}).get('Status')}")
acc = ses.get_account()
print(f"ProductionAccessEnabled={acc.get('ProductionAccessEnabled')} SendingEnabled={acc.get('SendingEnabled')}")

try:
    ses.create_email_identity(EmailIdentity=sender)
    print(f"created identity {sender}")
except ses.exceptions.AlreadyExistsException:
    print(f"identity already exists {sender}")
except Exception as e:
    # Domain-verified accounts may treat create as idempotent-ish
    print(f"create note: {type(e).__name__}: {e}")

nid = ses.get_email_identity(EmailIdentity=sender)
print(f"sender {sender}: VerifiedForSending={nid.get('VerifiedForSendingStatus')}")

print("\nApp env esperado:")
print(f"  EMAIL_SENDER={sender}")
print(f"  SES_REGION={region}")
print("  EMAIL_DEV_MODE=0")
print("  (AWS_REGION pode ficar us-east-1 se S3/Bedrock usarem outra região)")

if test_to.strip() and test_to.strip() != "-":
    classic = boto3.client("ses", region_name=region)
    classic.send_email(
        Source=sender,
        Destination={"ToAddresses": [test_to.strip()]},
        Message={
            "Subject": {"Data": "inove4us SES smoke — noreply", "Charset": "UTF-8"},
            "Body": {
                "Text": {
                    "Data": "Smoke SES inove4us: noreply@ ok.",
                    "Charset": "UTF-8",
                }
            },
        },
    )
    print(f"\nSmoke enviado para {test_to.strip()}")
'@ | Set-Content -LiteralPath $tmp -Encoding UTF8

try {
  $testArg = if ([string]::IsNullOrWhiteSpace($TestTo)) { "-" } else { $TestTo }
  & $Py $tmp $EnvFile $Region $Sender $Domain $testArg
  if ($LASTEXITCODE -ne 0) { throw "setup SES falhou" }
} finally {
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}
