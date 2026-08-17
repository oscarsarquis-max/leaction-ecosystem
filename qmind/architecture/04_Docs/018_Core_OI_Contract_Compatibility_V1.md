# 018 — Core OI Contract Compatibility V1

- Status: Approved
- Date: 2026-08-17
- Sprint: **OI-011** (Core side)

## Objetivo

Proteger a integração Core ↔ OI contra:

1. **drift** acidental do contrato wire v1;
2. **respostas OI** com `core_organization_id` diferente do `OrgContext` da chamada.

Não altera semanticamente o contrato OI-001.

## Ownership

| Artefato | Owner |
|----------|--------|
| Contrato público v1 (JSON Schema) | **QMind OI** |
| DTOs wire locais | QMind Core (independência física) |
| Check de compatibilidade | QMind Core (consome snapshots públicos) |

Sem import runtime de `qmind_oi`, sem package compartilhado, sem path obrigatório no runtime da API.

## Estratégia de compatibilidade

1. OI exporta schemas com `qmind-oi-export-schemas` → `qmind-oi/schemas/v1/*.json`.
2. Core mantém **snapshots** commitados em `backend/contracts/oi/v1/` (cópia dos schemas públicos).
3. Core gera JSON Schema a partir dos DTOs Pydantic (`OrganizationContextInput`, `OrganizationalInsights`).
4. Comparador estrutural verifica required, tipos, enums, nesting e `additionalProperties` (ignora title/description/ordem/metadata).

## Schemas utilizados

- `organization-context-input.schema.json`
- `organizational-insights.schema.json`

## Como executar

```powershell
cd C:\Projetos\qmind\backend
# opcional: atualizar snapshots a partir do sibling qmind-oi
python scripts/sync_oi_contract_schemas.py
python scripts/check_oi_contract_compatibility.py
pytest -q tests/test_oi_contract_guard.py
```

`QMIND_OI_SCHEMAS_DIR` pode apontar para `qmind-oi/schemas/v1` em vez dos snapshots.

## Organization response guard

Antes de persistir / devolver sucesso:

`response.core_organization_id == ctx.organization_id`

Mismatch → `AppError` `oi_organization_mismatch` (HTTP 502), **sem** persistir e **sem** reescrever o ID.

## TD — Contract Drift Core ↔ OI

**Mitigada** nesta Sprint: check automatizado + snapshots + testes de detecção de drift.  
Ainda **não** há pipeline CI único entre repositórios separados — limitação documentada abaixo.

## Limitações

- Repositórios Git separados: o CI do Core valida contra **snapshots**; sync manual/periodico via `sync_oi_contract_schemas.py` após mudanças OI.
- Não é um engine genérico de semver / registry.
- Comparação focada no contrato v1 em uso (dois envelopes).
