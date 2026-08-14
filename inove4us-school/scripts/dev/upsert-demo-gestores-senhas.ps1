# Upsert local das senhas dos gestores demo (School).
# NAO grava senha no git — leia de env ou parametros.
#
# Uso:
#   $env:SCHOOL_DEMO_PASSWORD = 'DemoSchool2026!'
#   $env:SCHOOL_SYSADMIN_PASSWORD = 'TourSchool2026!'
#   .\scripts\dev\upsert-demo-gestores-senhas.ps1
#
# Ou:
#   .\scripts\dev\upsert-demo-gestores-senhas.ps1 -DemoPassword '...' -SysadminPassword '...'

param(
    [string]$DemoPassword = $env:SCHOOL_DEMO_PASSWORD,
    [string]$SysadminPassword = $env:SCHOOL_SYSADMIN_PASSWORD,
    [string]$DbHost = '127.0.0.1',
    [int]$DbPort = 5434,
    [string]$DbName = 'inove4us_school',
    [string]$DbUser = 'admin',
    [string]$DbPass = $(if ($env:DB_PASS) { $env:DB_PASS } else { 'password123' })
)

$ErrorActionPreference = 'Stop'

if (-not $DemoPassword -or -not $SysadminPassword) {
    Write-Host "Defina SCHOOL_DEMO_PASSWORD e SCHOOL_SYSADMIN_PASSWORD (ou -DemoPassword / -SysadminPassword)." -ForegroundColor Yellow
    exit 2
}

$venvPy = Join-Path $PSScriptRoot '..\..\backend\.venv\Scripts\python.exe'
if (-not (Test-Path $venvPy)) {
    throw "Venv ausente: $venvPy"
}

$env:SCHOOL_UPSERT_DEMO = $DemoPassword
$env:SCHOOL_UPSERT_SYSADMIN = $SysadminPassword
$env:SCHOOL_UPSERT_DB_HOST = $DbHost
$env:SCHOOL_UPSERT_DB_PORT = "$DbPort"
$env:SCHOOL_UPSERT_DB_NAME = $DbName
$env:SCHOOL_UPSERT_DB_USER = $DbUser
$env:SCHOOL_UPSERT_DB_PASS = $DbPass

& $venvPy -c @'
from werkzeug.security import generate_password_hash, check_password_hash
import os, psycopg2
from psycopg2.extras import RealDictCursor

demo = os.environ["SCHOOL_UPSERT_DEMO"]
tour = os.environ["SCHOOL_UPSERT_SYSADMIN"]
conn = psycopg2.connect(
    host=os.environ["SCHOOL_UPSERT_DB_HOST"],
    port=int(os.environ["SCHOOL_UPSERT_DB_PORT"]),
    dbname=os.environ["SCHOOL_UPSERT_DB_NAME"],
    user=os.environ["SCHOOL_UPSERT_DB_USER"],
    password=os.environ["SCHOOL_UPSERT_DB_PASS"],
)
cur = conn.cursor(cursor_factory=RealDictCursor)
mapping = {
    "admin@i4uschool.com.br": tour,
    "admin@horizonte.edu.br": demo,
    "pedagogico@horizonte.edu.br": demo,
    "ana@horizonte.edu.br": demo,
    "operacional@horizonte.edu.br": demo,
}
for email, pw in mapping.items():
    h = generate_password_hash(pw, method="scrypt")
    cur.execute(
        """
        UPDATE public.school_gestores
           SET senha_hash = %s, updated_at = CURRENT_TIMESTAMP
         WHERE lower(email) = %s
     RETURNING email
        """,
        (h, email.lower()),
    )
    row = cur.fetchone()
    print(("OK  " if row else "MISS"), email)
conn.commit()
cur.execute("SELECT email, senha_hash FROM public.school_gestores ORDER BY email")
for row in cur.fetchall():
    expect = tour if row["email"] == "admin@i4uschool.com.br" else demo
    print("verify", row["email"], check_password_hash(row["senha_hash"], expect))
'@

Write-Host "Senhas demo/sysadmin aplicadas no banco local." -ForegroundColor Green
