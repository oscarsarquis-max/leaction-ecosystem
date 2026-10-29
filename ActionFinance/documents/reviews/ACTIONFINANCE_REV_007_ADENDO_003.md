# ACTIONFINANCE_REV_007_ADENDO_003 — Caracteres no nome da empresa

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_007_ADENDO_003 |
| Prompt | [ADENDO_003](../prompts/ACTIONFINANCE_PRM_007_ADENDO_003_ENCODING.md) |
| Data | 30/09/2026 |
| Executor | Cursor |
| Publicação | Continua **não declarada** |
| Aceite | Não atribuído ao executor. Sem PRM_008 |
| Nova imagem | **Não.** Digest ECR permanece `sha256:7c4cc0de22350fe0f3e62873d06fca6423cc25946205b4b70756822729da5b65` |

Complementa [REV_007](ACTIONFINANCE_REV_007.md). Não reabre ingresso, identidade visual nem regras financeiras.

## Causa

O valor persistido já estava corrompido. O PostgreSQL guardava a sequência Unicode **U+00C3 U+00A3** (`Ã£`), não **U+00E3** (`ã`).

Hex UTF-8 **antes** (tenant e company, mesmos IDs):

`4c6f6a612064652050c383c2a36573` — 15 bytes — equivalente a `Loja de PÃ£es`.

Hex UTF-8 **correcto** de `Loja de Pães`:

`4c6f6a612064652050c3a36573` — 13 bytes.

O primeiro ponto em que `ã` deixa de ser U+00E3 é a leitura do JSON de *overrides* do ECS no AWS CLI do Windows: o ficheiro era UTF-8 com o byte `C3 A3`; sem escapes ASCII, o CLI interpretava esses bytes como Windows-1252 e entregava `Ã£` ao contentor Linux. O Java persistiu o argumento já corrompido. Jackson, `Content-Type: application/json;charset=UTF-8` e o cabeçalho da SPA **reproduziram** o valor persistido; não houve *replace* visual nem dupla descodificação no browser.

## Correção

1. **Dado (2 linhas):** `tenant` `4f150085-f5f0-4138-80c3-fcf06db15c3c` e `company` `624023a4-57e3-415c-b7d0-925ca1acd3b7`, ambas `code=loja-de-paes`, só quando o hex era o mojibake acima. Valor novo via `convert_from(decode('…c3a36573','hex'),'UTF8')`. IDs, códigos, vínculos, login e factos financeiros intactos.
2. **Auditoria:** 2 inserções em `access_admin_audit` (`correlation_id=prm007-adendo-003`, executor `ADMIN_CLI` / `prm007-adendo-003`, acção `PROVISION_USER`, motivo de reparo de *encoding*, metadados com hex antes/depois). Sem *update* global de tabelas.
3. **Caminho novo:** `scripts/ops/af-ecs-override-json.ps1` + `run-access-admin-ecs.ps1` — JSON só ASCII com `\uXXXX`, ficheiro UTF-8, `AWS_CLI_FILE_ENCODING=UTF-8`. Não depende só de `$OutputEncoding` / `Set-Content`.

Restantes linhas com o hex errado em `tenant`/`company`: **0**.

## Ensaio isolado (sem empresa fictícia em produção)

Texto `Padaria São João — Ação e Pães` (U+00E3, U+00E7, U+2014) pelo **mesmo** construtor de *overrides* ECS.

| Prova | Resultado |
|---|---|
| `test-ecs-override-encoding.ps1` | `\u00e3` no JSON; *round-trip* PowerShell mantém os *codepoints*; simulação 1252 do UTF-8 de U+00E3 produz U+00C3 U+00A3 |
| Fargate `probe-ecs-override-roundtrip.ps1` | hex recebido no contentor = `506164617269612053c3a36f204a6fc3a36f20e280942041c3a7c3a36f20652050c3a36573` |
| `AppShell.test.tsx` | cabeçalho renderiza o texto original; sem `Ã` |
| `CompanyNameJsonEncodingTest` | JSON Jackson de `/access/context` contém `c3a3`, não `c383c2a3` |

Nenhuma linha de tenant/empresa de ensaio foi inserida no RDS de produção.

## Destino real

| Prova | Resultado |
|---|---|
| Hex após reparo | tenant e company `4c6f6a612064652050c3a36573` (`Loja de Pães`, 13 bytes) |
| JSON SQL do nome | `{"name" : "Loja de Pães"}` hex `…50c3a36573…` |
| IDs | tenant `4f150085-…`; company `624023a4-…`; ator `3548715b-…` `ACTIVE` |
| HTTP | `GET /api/v1/access/me` e `/context` → **401**, `Content-Type: application/json;charset=UTF-8`; *readiness* **200** |
| Cabeçalho autenticado | **não** capturado: sessão humana ainda não comprovada neste ciclo. Após o próximo `GET /api/v1/access/me` (restauração OIDC / recarregar), o cabeçalho lê `company.name` sem transformação |
| Captura | [receivables-unauthenticated.png](screenshots/prm-007-adendo-003/receivables-unauthenticated.png) — sem *storage state*, sem tokens/cookies no ficheiro |

## Gates PRM_007 ainda pendentes

O analista encerrou este adendo em 30/09/2026 com a confirmação visual do proprietário: o cabeçalho autenticado mostra **Loja de Pães**. Essa confirmação **não** substitui logout/CSRF autenticados nem o restore isolado.

## Encerramento deste retorno

Defeito de *encoding* no nome da Loja de Pães **corrigido** e **aceite visual pelo proprietário**. Sem *deploy* de imagem. Sem PRM_008.
