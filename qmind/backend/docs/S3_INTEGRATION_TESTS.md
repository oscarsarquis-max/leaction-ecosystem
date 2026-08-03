# Testes de integração S3 (evidências)

Separados dos testes unitários/API (`STORAGE_BACKEND=memory`).

## Pré-requisitos

1. Bucket **privado** dedicado ao QMind em `us-east-2` (ADR-007).
2. Block Public Access **ligado** no bucket (todos os quatro controles).
3. Credenciais com `s3:PutObject`, `s3:GetObject`, `s3:HeadObject`, `s3:DeleteObject` apenas nesse bucket.
4. Variáveis de ambiente locais (nunca commitadas):

```powershell
$env:QMIND_S3_INTEGRATION = "1"
$env:STORAGE_BACKEND = "s3"
$env:S3_REGION = "us-east-2"
$env:S3_BUCKET = "qmind-evidences-<sua-conta>"
# Credenciais via profile/env padrão AWS — não colar no repositório
```

## Execução

```powershell
cd C:\Projetos\qmind\backend
pytest -q -m integration tests/test_storage_s3_integration.py
```

Por padrão `pytest.ini` usa `-m "not integration"` — a suíte CI/local normal **não** chama S3 real.

## Integridade (hash)

- `content_hash` é `sha256:` calculado pelo backend a partir dos bytes do objeto (`get_bytes`), **não** do ETag.
- ETag S3 em upload multipart **não** é SHA-256 nem MD5 do objeto completo.
- Metadados livres enviados pelo cliente **não** são aceitos em `receive`.

## Bucket — checklist operacional

| Controle | Esperado |
|---|---|
| Acesso público | Bloqueado (Block Public Access) |
| ACLs | Privadas / Bucket owner enforced |
| Região | `us-east-2` |
| Reutilização bucket CMS Hub | Proibida |
