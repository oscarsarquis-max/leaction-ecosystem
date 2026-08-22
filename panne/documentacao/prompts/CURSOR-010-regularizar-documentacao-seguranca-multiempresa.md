# CURSOR-010 — Regularizar documentação e implementar segurança multiempresa

## Estado

- Estado: aprovado para execução
- Executor: Cursor
- Dependência: CURSOR-009 aceito
- Próximo prompt: bloqueado até retorno e revisão

## Objetivo

Executar duas entregas inseparáveis:

1. incorporar em `panne/documentacao/` as decisões arquiteturais e regulatórias que estavam apenas no arquivo do Codex;
2. implementar autenticação desacoplada, autorização interna e PostgreSQL Row-Level Security antes da abertura de APIs de negócio.

Não implemente chão de fábrica, ordens de produção, relatórios, frontend ou CRUDs de negócio neste ciclo.

## Regras absolutas

1. Trabalhe somente dentro de `panne` e nos índices estritamente necessários do workspace.
2. Não leia nem reutilize documentos, código ou ADRs de `qmind` ou de qualquer aplicação irmã.
3. Não acesse FTP ou MySQL legado.
4. Não faça commit, push ou deploy.
5. Não crie recursos AWS reais.
6. Não exponha valores do `.env`, tokens, segredos ou credenciais.
7. Preserve integralmente os comportamentos dos CURSOR-001 a 009.

## Parte A — Regularização documental

Inventariar `panne/documentacao/`, criar índice mestre e pastas `decisoes/`, `regulatorio/`, `produto/`. Registrar que documentos homônimos de `qmind` pertencem a outro produto.

Documentar: grounding e fontes; IA assistiva via Bedrock; governança regulatória; mapa regulatório inicial (RDC/IN/Lei/NR, sem ativação); identidade visual (`pannebege.png`, `pannepreto.png`, sem modificar imagens); chão de fábrica como frente futura.

Reconciliar ciclos 007, 008 e 009 sem renumerar migrações ou ADRs.

## Parte B — Auditoria multiempresa

Confirmar PostgreSQL, banco `panne` e head `0008_compliance_governance`. Inventariar tabelas 0001–0008. Classificar global / organizacional / híbrida / herdada. Produzir matriz `tabela × propriedade × leitura × escrita × política RLS`.

## Parte C — Autenticação

Cognito User Pools como provedor-alvo, porta `AccessTokenVerifier`, `CognitoAccessTokenVerifier`, `FakeAccessTokenVerifier`, cache JWKS, timeout, falha fechada, sem rede nos testes comuns. Validar RS256, kid, emissor, exp, `token_use=access`, client_id, aud, scopes e formato. `sub` opaco. Sem grupos do Cognito como autorização.

## Parte D — Identidade e autorização internas

Migração `0009_identity_authorization_rls`. Vínculo único issuer+subject, estado do usuário, associação ativa, papéis, permissões, auditoria. Sem senha local. Sem autocadastro. Bootstrap explícito do primeiro proprietário.

## Parte E — Contexto organizacional

Token → identidade → usuário ativo → organização → associação → papéis/permissões → transação → `set_config` local → acesso → fim da transação. GUCs `app.current_organization_id` e `app.current_user_id`. Sem vazamento no pool.

## Parte F — PostgreSQL RLS

ENABLE + FORCE, USING e WITH CHECK, default deny, runtime sem superuser/owner/BYPASSRLS, papéis de migração e runtime separados, catálogos globais com regras explícitas.

## Parte G — Contrato HTTP mínimo

Somente `GET /api/v1/me`. 401 / 403 / 503. `/health` público. `/ready` sem bypass de negócio.

## Parte H — Testes obrigatórios

Ciclo 0008↔0009, recriação 0001→head, inventário RLS, runtime sem privilégio, isolamento A/B, imutabilidade de `organization_id`, default deny, contexto inválido, pool sem vazamento, globais, conhecimento restrito, 403 sem associação/permissão, JWT (assinatura, emissor, exp, token_use, cliente/aud, kid, JWKS, sub não UUID), sem Cognito real, regressão 129+1 skip, Python 3.12, health/ready/me.

## Parte I — Segurança e observabilidade

Não registrar JWT. Sanitizar erros. Correlação. Sem refresh token. Dependências fixadas.

## Critérios de aceite

Documentação canônica em `panne/documentacao/`; sem fonte irmã; tokens validados; autorização interna; RLS organizacional; runtime sem contorno; contexto transacional; sem segredo versionado; testes verdes; sem frontend/CRUD; sem commit/push/deploy.

Não avançar para o CURSOR-011.
