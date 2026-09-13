# SEGSENSE_PRM_004 — Publicadores, canais e ambientes

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_PRM_004 |
| Título | Primeiro módulo funcional local — catálogo administrativo |
| Categoria | PRM — prompt de desenvolvimento |
| Versão | 1.0 |
| Status | Em execução |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_ARQ_001 v0.3; SEGSENSE_PLN_001; SEGSENSE_PRM_001 a 003 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Cópia integral do prompt original desta etapa. |

## Prompt integral

Implemente o `SEGSENSE_PRM_004` em `C:\Projetos\segsense`, no monorepo existente `leaction-ecosystem`.

Leia todo o índice documental, documentos arquiteturais, ADRs, revisões, código, migrations e testes. Preserve o trabalho existente. Não execute `git init`, não altere remotes ou outros produtos e não faça commit, push ou deploy.

### 1. Objetivo

Criar o primeiro módulo funcional local do SegSense para administrar:

- publicadores;
- canais digitais pertencentes a um publicador;
- ambientes contextualizados pertencentes a um canal.

O módulo será exclusivamente local ao SegSense. Não enviará dados à Spider, não consultará Icatu e não implementará oportunidade contextual, link de publicação, jornada, intent, capability ou execução.

Como ainda não existe IdP, os endpoints administrativos permanecerão protegidos no runtime. Testes poderão usar autenticação somente no classpath de teste. Não crie login ou credenciais para contornar essa limitação.

### 2. Atualização arquitetural herdada

Antes do escopo funcional:

1. Compare a fonte `C:\Users\Oscar Sarquis\Documents\Codex\2026-09-04\contextualize-se-sobre\outputs\SEGSENSE_ARQ_001.md` com `documents\SEGSENSE_ARQ_001.md`.
2. Atualize o workspace para `SEGSENSE_ARQ_001` v0.3, preservando o histórico e o §26.9.
3. Registre claramente três aplicações fisicamente independentes: SegSense; Spider; Insurance Provider Mock futuro.
4. “Satellite” significa padrão de integração; não significa incorporação do SegSense à Spider.
5. Nenhum código, módulo, banco, runtime ou deployment do SegSense ou do mock pertence à Spider.
6. O projeto SegSense não modificará a Spider.
7. O mock futuro terá runtime, configuração, endpoints e ciclo de vida próprios.
8. Atualize `SEGSENSE_ARQ_002`, `SEGSENSE_ADR_001`, `SEGSENSE_REV_003`, `README.md`, READMEs de services e índice documental.
9. Eleve as versões dos documentos alterados e registre o histórico.
10. Copie e reconcilie a versão atualizada de `SEGSENSE_PLN_001` da área de saída, sem apagar registros de execução já feitos no workspace.

### 3. Linguagem do domínio

Publisher, Channel e ContextualEnvironment conforme `SEGSENSE_DOM_001`: UUID, `key` imutável, nome 3–120, status `DRAFT|ACTIVE|SUSPENDED`, versionamento, timestamps UTC e autoria técnica. Sem CNPJ, CPF, endereço, e-mail, telefone ou dados contratuais. Canal com tipo `WEBSITE|WEB_APPLICATION|MOBILE_APPLICATION|PARTNER_PORTAL`. Ambiente com tipo `ARTICLE|PAGE|APPLICATION_SCREEN|EMBEDDED_COMPONENT` e `canonicalUrl` HTTPS opcional sem query, fragment, userinfo ou credencial. Sem conteúdo editorial, perfil de usuário ou contexto inferido.

### 4. Regras determinísticas

- `key` é normalizada para minúsculas antes da validação e depois permanece imutável.
- Nomes têm espaços externos removidos; vazio é rejeitado.
- Não existe exclusão física nem endpoint DELETE.
- Ativação de Channel exige Publisher `ACTIVE`.
- Ativação de ContextualEnvironment exige Publisher e Channel `ACTIVE`.
- Suspender pai não altera silenciosamente o status persistido dos filhos; sua disponibilidade efetiva torna-se falsa.
- Reativação não reativa filhos automaticamente.
- Toda busca de Channel valida `publisherId`.
- Toda busca de ContextualEnvironment valida `publisherId` e `channelId`.
- Recurso de outro escopo retorna 404, nunca 403 revelando existência.
- Atualização exige versão esperada; conflito retorna 409 `CONCURRENT_MODIFICATION`.
- Violação de unicidade retorna 409 com código estável, sem SQL.
- Transição inválida retorna 422 `INVALID_STATE_TRANSITION`.
- Validação de entrada retorna 400 `VALIDATION_ERROR`.

Matriz mínima:

```text
DRAFT → ACTIVE
ACTIVE → SUSPENDED
SUSPENDED → ACTIVE
```

Não permitir retorno para `DRAFT`.

### 5. Persistência

Migration Flyway V2 com tabelas separadas no schema `segsense`, constraints, chaves estrangeiras, índices, unicidades e `TIMESTAMPTZ`. UUID, optimistic locking, CHECKs de status e type, autoria textual sem FK de usuário, nenhuma exclusão em cascata, índices hierárquicos, reversível conceitualmente sem script destrutivo automático. `ddl-auto=none`. Não alterar a V1.

### 6. Arquitetura de aplicação

Aggregates, casos de uso e portas. JPA e Spring em infrastructure; controllers em inbound HTTP; domínio puro. Requests e responses próprios. Regras de transição fora de controllers e repositories. Casos de uso: criar, consultar, listar com cursor, atualizar nome, transição de status. Autoria obrigatória nos casos de uso. Sem adapter de identidade no runtime. Testes: adapter ou fixture só no classpath de teste.

### 7. API administrativa

Base `/api/v1/admin`. Recursos `/publishers`, `/publishers/{publisherId}/channels`, `/publishers/{publisherId}/channels/{channelId}/environments`. POST, GET individual, GET coleção com cursor, PATCH de nome, POST de transição. Sem PUT completo, DELETE ou atualização de `key`. Paginação `page[size]` 1–100 e `page[after]`, ordem `createdAt,id`. Leitura `segsense.catalog.read`; escrita `segsense.catalog.write`. Sem IdP, chamadas reais 401. Testes com autenticação mockada. Correlation ID em sucesso e erro.

### 8. Frontend

Estrutura administrativa para Publicadores, Canais e Ambientes. Ao 401, “Autenticação ainda não configurada”. Sem login, token, usuário local, fixtures de runtime ou cadastros falsos. Listas, formulários, vazio, erro e carregamento. Testes podem injetar HTTP. Navegação hierárquica. Acessibilidade. Documentar o bloqueio sem IdP.

### 9. Documentação

Criar `SEGSENSE_DOM_001`, `SEGSENSE_DAT_001`, `SEGSENSE_API_002`, `SEGSENSE_REV_004`, `SEGSENSE_PRM_004`. Atualizar ARQ_001, ARQ_002, ADR_001, API_001, SEC_001, README, índice e planejamento. Registrar versões e históricos.

### 10. Testes obrigatórios

Invariantes e transições; normalização e imutabilidade de key; `canonicalUrl`; ativação bloqueada por pai inativo; disponibilidade efetiva; isolamento hierárquico e 404 cross-scope; unicidade e concorrência; V2 em PostgreSQL real; CRUD e paginação com Testcontainers; 401 anônimo; 403 sem authority; sucesso com authority de teste; correlação; ausência de DELETE e alteração de key; ArchUnit; frontend honesto; regressão dos testes anteriores.

### 11. Validações finais

Backend `verify`; frontend `npm ci`, lint, testes e build; Compose sem remover volumes; V2 no PostgreSQL; chamadas públicas reais; administrativas anônimas 401; inspeção de segredos, dados pessoais e SQL em erros; Git limitado a `segsense/`; integridade do índice. Sem credencial temporária.

### 12. Critérios de aceite

Decisão de independência das três aplicações documentada. ARQ_001 v0.3 vigente. Aggregates, regras e persistência. Isolamento hierárquico. API deny-by-default. Nenhum usuário ou IdP fictício. Frontend sem simular dados nem acesso. Migrations e testes em PostgreSQL real. Documentação indexada. Nenhuma integração Spider, Icatu ou mock. Nenhum outro produto alterado.

### 13. Devolutiva

Apresentar atualização arquitetural herdada; arquivos; modelo; transições; endpoints; segurança e paginação; migration; frontend; testes; SAT-01 a SAT-10; Git; ressalvas; confirmação de ausência de dados pessoais, credenciais e integrações fictícias. Não fazer commit, push ou deploy.
