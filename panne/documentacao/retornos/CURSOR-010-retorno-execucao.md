# CURSOR-010 — Retorno da execução

Data: 2026-08-22. Sem commit, push, deploy ou CURSOR-011. Aguarda revisão do arquiteto.

## 1. MySQL, FTP e aplicações irmãs

Não foram abertos, lidos nem reutilizados MySQL, FTP, `qmind` ou qualquer aplicação irmã. Nenhuma credencial de origem foi usada.

## 2. Documentos incorporados

Índice mestre: `documentacao/INDICE.md` e `documentacao/INDEX.md`.

- `decisoes/GROUNDING-E-FONTES.md`
- `decisoes/IA-ASSISTIVA-BEDROCK.md`
- `decisoes/GOVERNANCA-REGULATORIA.md`
- `decisoes/IDENTIDADE-VISUAL.md`
- `decisoes/AUTENTICACAO-E-AUTORIZACAO.md`
- `decisoes/CONTEXTO-E-RLS.md`
- `decisoes/MATRIZ-RLS.md`
- `decisoes/AMEACAS-E-RISCOS.md`
- `decisoes/RECONCILIACAO.md`
- `regulatorio/MAPA-REGULATORIO-INICIAL.md`
- `produto/CHAO-DE-FABRICA.md`
- `produto/BOOTSTRAP-PRIMEIRO-PROPRIETARIO.md`
- prompt e este retorno

Imagens `frontend/images/pannebege.png` e `pannepreto.png` não foram modificadas.

## 3. Conflitos documentais

ADR-011, ADR-012, ADR-014, REG-001 e REG-002 **não existiam em `panne/`**. Homônimos em outras apps são outro produto e não foram fonte. Migrações e ADRs não foram renumerados. Histórico 007–009 não foi reescrito.

## 4. Banco e head

Antes: PostgreSQL 18.4 (`leaction_db`), banco `panne`, head `0008_compliance_governance`. Papel `admin` é superusuário com `BYPASSRLS`.  
Depois: head `0009_identity_authorization_rls`.

## 5. Arquivos e tabelas

Código novo/alterado só em `panne/`: migração `0009`; modelos `auth_identity`, `permission`, `role_permission`; porta `AccessTokenVerifier`; contexto transacional; `GET /api/v1/me`; bootstrap de runtime; testes JWT/RLS/`/me`.

Tabelas novas: `auth_identity`, `permission`, `role_permission`. Demais tabelas 0001–0008 preservadas e classificadas na matriz.

Sem CRUD de negócio e sem frontend neste ciclo.

## 6. Identidade externa

Provedor-alvo: Cognito User Pools. Porta `AccessTokenVerifier`. `CognitoAccessTokenVerifier` + `FakeAccessTokenVerifier`. Vínculo único `issuer + subject` → `app_user`. `sub` é string opaca. Sem senha local. Sem grupos do Cognito como autorização. Sem autocadastro.

## 7. Papéis e permissões

Papéis existentes preservados (`owner`, `administrator`, `technical_responsible`, `production`, `commercial`, `viewer`). Acrescentados `organization_owner`, `organization_admin`, `production_manager`, `baker_operator`, `regulatory_reviewer`, `restricted`.

Permissões: `identity.read_me`, `organization.read`, `membership.read`, `compliance.review`. Associação sozinha não libera todas as ações. `restricted` não tem permissão.

## 8. Validações JWT

RS256, `kid`, emissor, expiração, `token_use=access`, `client_id`, `aud` quando presente, escopos e formato estrutural. Decode sem verificação criptográfica não é confiança. Falha fechada.

## 9. Cache de JWKS

Cache por `kid`. `kid` desconhecido provoca uma atualização. Timeout configurável. Sem cache e JWKS indisponível → 503 sanitizado. Com cache, `kid` conhecido continua válido. Testes comuns sem rede.

## 10. Matriz RLS

Ver `decisoes/MATRIZ-RLS.md`. Organizacionais e híbridas aplicáveis têm ENABLE + FORCE. Globais: leitura se autenticado, escrita negada. Conhecimento global `restricted` invisível; `released` visível. Runtime não escreve fonte global.

## 11. Papéis PostgreSQL

Migrador: `PANNE_DATABASE_URL` (admin local). Runtime: `panne_runtime` / `PANNE_RUNTIME_DATABASE_URL`. Runtime sem superuser, sem propriedade de tabelas, sem `BYPASSRLS`, sem GRANT em `alembic_version`. Papel criado por `scripts/dev/bootstrap-runtime-role.ps1` (idempotente), não pelo Alembic.

## 12. Default deny e isolamento A/B

Sem contexto ou UUID inválido: leitura e escrita bloqueadas. Organização A não lê nem altera B. `INSERT`/`UPDATE` não trocam `organization_id`.

## 13. Pool

`set_config(..., true)` local à transação. Teste de conexão reutilizada: após commit, nova transação não vê linhas da org anterior.

## 14. Contrato HTTP

- `GET /health` — público, sem banco.
- `GET /ready` — ping ao Postgres, 200/503 sanitizado; sem bypass de negócio.
- `GET /api/v1/me` — token, usuário interno, associações, papéis e permissões; sem e-mail, token ou detalhe criptográfico.
- 401 / 403 / 503 conforme o prompt.

## 15. Migração e reversibilidade

`0008 → 0009 → 0008 → 0009` e `0001 → head`. Downgrade remove políticas, funções, tabelas novas e restaura o check antigo de papéis (após apagar papéis novos residuais). Head final `0009_identity_authorization_rls`.

## 16. Testes, Python e PostgreSQL

148 passed, 1 skipped no venv local (3.11.15) e no container `python:3.12-slim-bookworm` (**3.12.14**). PostgreSQL 18.4. Testes de RLS no papel `panne_runtime`. Sem Cognito real. Sem Bedrock nos testes comuns.

## 17. Regressão do CURSOR-009

Os 129 testes anteriores + 1 skip permaneceram verdes. Acrescentados 19 testes (JWT, RLS, `/me`, inventário, ciclo 0009).

## 18. `.env` e `.env.example`

`.env` continua no `.gitignore`. `.env.example` só com placeholders (emissor, client, URL de runtime). Sem access key, secret ou session token. Nenhum valor de ambiente neste retorno.

## 19. Git

`panne/` permanece untracked. Arquivos rastreados pré-existentes (`infra/ecosystem-databases.sql`, `leaction-ecosystem.code-workspace`) não foram tocados neste ciclo.

`git status --short` (resumo): `?? panne/` e lixo pré-existente intacto. `git diff --stat` nos rastreados: vazio para este ciclo.

## 20. Riscos e pendências

- User Pool / app client Cognito ainda não existem (sem recurso AWS real).
- Guardrail Bedrock sem identificador.
- `admin` local continua superusuário com `BYPASSRLS` (só migração e regressão).
- Um papel por associação; múltiplos papéis na mesma org ficam para ciclo futuro.
- `pip-audit` no venv local apontou `setuptools 79.0.1` (PYSEC-2026-3447); não alterado para não mexer em outras apps.
- Chão de fábrica, CRUDs e frontend continuam fora.
- Não avançar ao CURSOR-011 sem revisão.

## 21. Commit, push e deploy

Não houve commit, push nem deploy.
