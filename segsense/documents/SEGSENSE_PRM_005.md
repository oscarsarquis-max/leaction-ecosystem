# SEGSENSE_PRM_005 — Oportunidade contextual e versionamento

## Controle

- Projeto: SegSense
- Identificador: SEGSENSE_PRM_005
- Versão: 1.0
- Data: 04/09/2026
- Etapa anterior: SEGSENSE_PRM_004 APROVADO COM RESSALVA

## Prompt para o Cursor

Implemente o `SEGSENSE_PRM_005` em `C:\Projetos\segsense`, no monorepo existente `leaction-ecosystem`.

Leia integralmente o índice documental, ARQ_001/002, ADRs, DOM_001, DAT_001, API_001/002, SEC_001, REV_004, migrations e código atual. Preserve tudo o que não pertencer ao escopo. Não altere outros produtos, Git ou remotes e não faça commit, push ou deploy.

## 1. Objetivo

Implementar a criação, consulta, edição versionada e histórico de **oportunidades contextuais** vinculadas a ambientes cadastrados.

Nesta etapa, uma oportunidade é apenas um rascunho editorial e funcional local. Não publicar links, não interpretar contexto com IA, não recomendar seguro, não integrar Spider/Icatu/mock, não coletar consentimento e não implementar aprovação ou publicação.

## 2. Correção herdada obrigatória

Antes do novo escopo, corrigir a integridade relacional do catálogo.

A tabela `contextual_environment` possui atualmente FKs independentes para `publisher_id` e `channel_id`, permitindo no banco uma combinação contraditória entre Publisher A e Channel B.

Não altere V1 ou V2. Crie `V3__enforce_environment_catalog_scope.sql` que:

1. detecte previamente ambientes cujo `publisher_id` difira do publisher do canal;
2. falhe explicitamente se houver inconsistência, sem alterar ou apagar dados;
3. adicione UNIQUE em `channel(id, publisher_id)`;
4. substitua a FK simples do canal por FK composta `(channel_id, publisher_id) → channel(id, publisher_id)`;
5. mantenha a FK direta do publisher;
6. preserve `NO ACTION`, sem cascade ou trigger;
7. use constraints nomeadas e índices adequados.

Adicione teste PostgreSQL direto provando que uma combinação coerente é aceita e uma combinação cross-publisher é rejeitada pelo banco. Confirme aplicação incremental da V3 sobre o volume atual. Atualize DAT_001, DOM_001 e REV_004, com versões e histórico.

Não prossiga ao novo escopo se essa correção falhar.

## 3. Conceito de oportunidade contextual

Crie o aggregate `ContextualOpportunity`, pertencente a exatamente um `ContextualEnvironment` e, por consequência, ao mesmo Channel e Publisher.

Identidade estável:

- `id`: UUID;
- `publisherId`, `channelId`, `environmentId`;
- `key`: minúscula, imutável, única dentro do ambiente, regra `^[a-z][a-z0-9-]{2,49}$`;
- `status`: somente `DRAFT` nesta etapa;
- `currentRevision`: inteiro positivo;
- `version`: concorrência otimista do aggregate;
- timestamps e autoria técnica.

Conteúdo versionado:

- `title`: 5 a 140 caracteres;
- `contextMode`: `STATIC`, `DYNAMIC` ou `HYBRID`;
- `contextSummaryTemplate`: 10 a 1.000 caracteres, podendo usar placeholders declarados;
- `objectiveTemplate`: 10 a 1.000 caracteres, a ser materializado futuramente antes do envio à Spider;
- `callToActionLabel`: 3 a 80 caracteres;
- `validFrom`: opcional, UTC;
- `validUntil`: opcional, UTC e posterior a `validFrom` quando ambos existirem.

Esses textos são declarados por operador. Não são inferidos, classificados ou tratados como entendimento da Spider.

Não incluir produto, seguradora, route, adapter, intent, execution plan, capability, preço, cobertura, elegibilidade, dados pessoais ou identificador de usuário final.

### Contrato versionado de contexto dinâmico

Cada revisão pode declarar `contextFields`, coleção ordenada de zero a 20 campos permitidos:

- `key`: `^[a-z][a-zA-Z0-9]{1,39}$`;
- `label`: 3 a 80 caracteres;
- `type`: `TEXT`, `NUMBER`, `BOOLEAN`, `DATE` ou `ENUM`;
- `required`: boolean;
- `source`: `PUBLISHER`, `USER` ou `EITHER`;
- `allowedValues`: obrigatório somente para ENUM, de 1 a 50 valores;
- `classification`: nesta etapa, somente `NON_PERSONAL`.

Regras:

- `STATIC` exige zero campos;
- `DYNAMIC` exige ao menos um campo;
- `HYBRID` admite campos e conteúdo estático;
- placeholders usam `{{fieldKey}}` e só referenciam campos declarados;
- placeholder desconhecido e chave duplicada são rejeitados;
- nenhum campo aceita objeto, HTML, script ou JSON arbitrário;
- CPF, nome, e-mail, telefone, localização precisa e outros dados pessoais são proibidos;
- a definição integra o snapshot imutável da revisão.

Exemplo conceitual:

```text
objectiveTemplate:
  "Quero avaliar proteção para {{cropType}} diante do risco de {{riskType}}."

contextFields:
  cropType — ENUM — PUBLISHER — NON_PERSONAL
  riskType — ENUM — PUBLISHER — NON_PERSONAL
```

Implemente e versione somente a definição. Não receba valores dinâmicos em runtime, não gere link, não renderize o template e não envie objetivo à Spider nesta etapa.

## 4. Versionamento imutável

- Criar oportunidade gera revisão 1.
- Editar conteúdo gera nova revisão N+1.
- Revisões anteriores são imutáveis.
- Não sobrescrever, atualizar ou apagar conteúdo histórico.
- Somente a revisão corrente pode originar nova revisão.
- Edição exige `expectedVersion` do aggregate e `baseRevision` igual à revisão corrente.
- Concorrência retorna 409 `CONCURRENT_MODIFICATION`.
- Base desatualizada retorna 409 `STALE_OPPORTUNITY_REVISION`.
- Conteúdo idêntico ao vigente não cria revisão e retorna 422 `NO_CONTENT_CHANGE`.
- `key`, hierarquia e autoria histórica nunca mudam.
- Não implementar estados `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, `PAUSED`, `EXPIRED` ou `REVOKED`; pertencem às próximas etapas.

## 5. Integridade hierárquica

Uma oportunidade só pode ser criada quando Publisher, Channel e Environment:

- existem na mesma hierarquia;
- estão `ACTIVE`;
- resultam em `effectivelyAvailable=true`.

Após criada, a oportunidade continua consultável se um pai for suspenso, mas seu campo calculado `effectivelyAvailable` se torna falso. Não altere silenciosamente o status do rascunho.

Toda consulta deve ser escopada por `publisherId`, `channelId` e `environmentId`. Cross-scope retorna 404.

## 6. Persistência

Após V3, crie `V4__create_contextual_opportunity_tables.sql` com:

- `contextual_opportunity`: identidade, hierarquia, key, status, revisão corrente, optimistic version, timestamps e autoria;
- `contextual_opportunity_revision`: PK própria UUID ou composta documentada, `opportunity_id`, número da revisão, snapshot completo do conteúdo, timestamps e autoria;
- `contextual_opportunity_revision_field`: definições tipadas e ordenadas pertencentes à revisão;
- unicidade da key por ambiente;
- unicidade `(opportunity_id, revision_number)`;
- unicidade `(opportunity_revision_id, field_key)` e da posição do campo;
- FKs compostas que garantam coerência da hierarquia até o ambiente;
- CHECKs de status, comprimentos, revisão positiva e validade temporal;
- nenhuma exclusão em cascata;
- índices para listagem por ambiente e histórico ordenado.

V1, V2 e V3 são imutáveis depois de aplicadas. JPA continua com `ddl-auto=none`.

## 7. Casos de uso e API

Casos de uso:

- criar oportunidade com revisão inicial;
- consultar oportunidade e revisão corrente;
- listar oportunidades do ambiente com cursor;
- criar nova revisão;
- listar histórico de revisões;
- consultar revisão específica.

Base HTTP:

```text
/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}/opportunities
```

Implemente:

- `POST /opportunities`;
- `GET /opportunities`;
- `GET /opportunities/{opportunityId}`;
- `POST /opportunities/{opportunityId}/revisions`;
- `GET /opportunities/{opportunityId}/revisions`;
- `GET /opportunities/{opportunityId}/revisions/{revisionNumber}`.

Não implementar PUT, PATCH destrutivo, DELETE, status transition ou publicação.

Authorities:

- consultas: `segsense.opportunity.read`;
- criação e nova revisão: `segsense.opportunity.write`.

Runtime sem IdP continua 401. Sucessos autenticados somente em testes com Spring Security test.

Listagens seguem cursor opaco, `page[size]` de 1 a 100 e ordem determinística. O cursor de histórico deve preservar a ordem de revisão sem permitir troca de opportunity por manipulação.

## 8. Respostas e erros

Respostas devem distinguir:

- identidade estável da oportunidade;
- metadados do aggregate;
- revisão corrente;
- snapshot de conteúdo;
- disponibilidade efetiva calculada.

Erros devem seguir API_001, conter correlação e nunca expor SQL, constraint, stack ou existência cross-scope.

Códigos mínimos:

- `OPPORTUNITY_KEY_CONFLICT` — 409;
- `STALE_OPPORTUNITY_REVISION` — 409;
- `CONCURRENT_MODIFICATION` — 409;
- `INVALID_PARENT_STATE` — 422;
- `NO_CONTENT_CHANGE` — 422;
- `VALIDATION_ERROR` — 400;
- `NOT_FOUND` — 404.

## 9. Frontend

Acrescente Oportunidades após a seleção de Environment:

- lista real pela API;
- estado vazio, loading, 401, 403 e erro;
- formulário de criação;
- detalhe com revisão corrente;
- formulário de nova revisão;
- histórico somente leitura;
- editor da definição de contexto com modo, campos, origem e valores de ENUM;
- preview dos placeholders declarados, sem solicitar valores de runtime;
- indicação clara de DRAFT e disponibilidade efetiva.

Sem IdP, mostrar bloqueio honesto. Não usar fixtures ou dados falsos no runtime, não criar login/token e não fingir publicação.

## 10. Documentação

Crie:

- `SEGSENSE_DOM_002.md`: oportunidade, conteúdo, invariantes e versionamento;
- `SEGSENSE_DAT_002.md`: V3/V4, modelo relacional e FKs compostas;
- `SEGSENSE_API_003.md`: endpoints e schemas implementados;
- `SEGSENSE_REV_005.md`: evidências, riscos e SAT;
- `SEGSENSE_PRM_005.md`: cópia integral deste prompt.

Atualize documentos afetados, README, índice e PLN_001. Marque PRM_004 como aprovado com ressalva transportada e depois resolvida pela V3. Registre versões e históricos.

## 11. Testes obrigatórios

- prova SQL direta da correção V3;
- migrations V1–V4 em banco vazio e V3/V4 incrementais;
- criação de revisão 1;
- nova revisão imutável;
- histórico preservado;
- rejeição de base e versão desatualizadas;
- nenhuma revisão em conteúdo idêntico;
- validações textuais e temporais;
- modos STATIC, DYNAMIC e HYBRID;
- campos, ENUMs, origens e placeholders;
- rejeição de campo pessoal, duplicado ou arbitrário;
- imutabilidade da definição entre revisões;
- pais inexistentes, cross-scope, suspensos ou não ativos;
- disponibilidade efetiva após suspensão do pai;
- unicidades e FKs compostas no PostgreSQL;
- cursor e isolamento do histórico;
- 401, 403 e authorities corretas;
- correlação em sucesso e erro;
- ausência de métodos proibidos;
- frontend e regressões completas;
- ArchUnit.

## 12. Validações finais

Execute backend verify, frontend npm ci/lint/test/build, Compose sem apagar volume, aplicação real V3/V4, histórico Flyway, endpoints públicos reais e admin anônimo 401.

Comprove sucessos administrativos em Testcontainers/test security. Inspecione segredos, PII, SQL em erros, alterações externas e índice documental.

## 13. Critérios de aceite

- ressalva do PRM_004 resolvida no PostgreSQL;
- hierarquia da oportunidade protegida no banco e aplicação;
- revisões imutáveis e concorrência segura;
- somente DRAFT implementado;
- APIs e UI não simulam autenticação nem publicação;
- migrations e testes passam;
- documentação indexada;
- nenhuma integração, IA, produto ou regra de cobertura inventada;
- nenhum outro produto alterado.

## 14. Devolutiva

Apresente:

1. correção herdada e prova SQL;
2. arquivos;
3. domínio e persistência;
4. versionamento;
5. endpoints e authorities;
6. interface;
7. migrations e Flyway;
8. testes e evidências;
9. SAT-01 a SAT-10;
10. Git e ressalvas;
11. confirmações de ausência de integrações, PII e publicação fictícia.

Não faça commit, push ou deploy.
