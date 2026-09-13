# SEGSENSE_PRM_007_COR_001 — Correção única do vínculo aprovado e HTTPS

## Controle

- Projeto: SegSense
- Identificador: SEGSENSE_PRM_007_COR_001
- Versão: 1.1
- Data: 11/09/2026
- Corrige: SEGSENSE_PRM_007
- Natureza: único corretivo permitido para esta etapa

## Prompt para o Cursor

Aplique o único corretivo do `SEGSENSE_PRM_007` em `C:\Projetos\segsense`.

Leia integralmente PRM_007, LNK_001, DAT_004, API_005, SEC_002, REV_007, GOV_001, migrations V1–V7 e a implementação atual. Preserve as entregas aprovadas: token CSPRNG, persistência exclusiva do digest, exposição única, bindings tipados, resolução pública mínima, headers, revogação, frontend e logo oficial.

Não altere V1–V7 já aplicadas. Não amplie o escopo. Não altere `.cursor/`, Spider, Panne ou qualquer caminho fora de `segsense/`. Não faça commit, push ou deploy.

## 1. Motivos da correção

### 1.1 Revisão existente não equivale a revisão aprovada

A V7 possui:

- FK do link para o escopo da oportunidade;
- FK `(opportunity_id, revision_number)` para uma revisão existente.

Ela não garante no PostgreSQL que `published_context_link.revision_number` seja igual a `contextual_opportunity.approved_revision`. SQL direto ainda pode inserir um link para uma revisão histórica válida, porém não aprovada. Isso diverge do requisito de vínculo inequívoco à revisão aprovada.

### 1.2 Profile default foi relaxado indevidamente

`ContextLinkConfiguration` trata `default` e também ausência de profile ativo como ambientes relaxados. O PRM_007 autorizou HTTP apenas em `local/test` e exigiu HTTPS fora deles. O comportamento atual pode aceitar HTTP em uma execução sem profile explicitamente local.

## 2. Migration corretiva V8

Crie `V8__bind_context_links_to_approved_revision.sql`. Não modifique V1–V7.

Antes de qualquer DDL, faça pré-validação e aborte explicitamente, sem corrigir ou apagar dados, se existir link cujo:

- `opportunity_id` não exista;
- `revision_number` seja diferente de `approved_revision` da oportunidade;
- revisão vinculada não exista;
- escopo Publisher/Channel/Environment seja incoerente.

Depois:

1. adicione em `contextual_opportunity` uma chave candidata nomeada sobre `(id, approved_revision)`;
2. adicione em `published_context_link` uma FK composta nomeada `(opportunity_id, revision_number) → contextual_opportunity(id, approved_revision)`;
3. preserve a FK da revisão e a FK completa de escopo, pois cumprem garantias diferentes;
4. mantenha `NO ACTION`, sem cascade, delete, correção automática ou trigger de negócio;
5. documente índices e rollback conceitual.

Considere que `approved_revision` é nullable em oportunidades ainda não aprovadas: isso não enfraquece a FK para links, pois `published_context_link.revision_number` é `NOT NULL`.

Adicione teste SQL direto demonstrando:

- link para a revisão aprovada é aceito;
- link para outra revisão existente da mesma oportunidade é rejeitado pelo PostgreSQL;
- link cross-scope continua rejeitado;
- a nova constraint existe com as colunas e destino corretos.

## 3. Endurecimento opcional dos bindings, condicionado ao modelo atual

Audite a V7 e a leitura pública para confirmar se SQL direto pode inserir em `published_context_link_binding` uma `field_key` que não pertence à revisão do link ou um `field_type` diferente do declarado.

Se isso for possível, corrija na mesma V8, sem reescrever V7:

- crie somente as chaves candidatas necessárias na revisão e no campo;
- acrescente ao link ou binding a identidade técnica da revisão, preenchida por relação inequívoca e validada antes do DDL;
- crie FK composta que obrigue `field_key`, `field_type` e, se mantido no binding, `field_source` a corresponderem à definição imutável da revisão vinculada;
- restrinja source persistido a `PUBLISHER` ou `EITHER`;
- preserve as colunas de valor tipadas e todos os CHECKs existentes.

Não faça preenchimento silencioso de dado inconsistente. Dados válidos existentes podem receber a identidade técnica derivada por migration somente se a derivação for unívoca e for documentada como evolução estrutural, não como reparo. Caso haja qualquer inconsistência, aborte antes da mutação.

Se concluir tecnicamente que essa FK não deve ser criada, registre em DAT_004 e REV_007 a justificativa concreta e mantenha testes de aplicação que impeçam binding desconhecido, tipo divergente e source USER. Não invente uma solução frágil apenas para satisfazer a forma.

## 4. HTTPS e profiles explícitos

Corrija `ContextLinkConfiguration`:

- somente profiles ativos `local` e `test` podem relaxar HTTPS;
- remova `default` da lista relaxada;
- ausência de profile ativo não é local e deve exigir HTTPS;
- profile desconhecido ou produtivo exige HTTPS;
- HTTP relaxado continua restrito a loopback;
- múltiplos profiles só relaxam quando a política documentada considerar explicitamente `local/test` e não houver profile incompatível; prefira fail-closed;
- preserve rejeição de userinfo, query, fragment, path inesperado, esquema inválido e host vazio.

Para manter o ambiente local funcional, configure explicitamente `spring.profiles.active=local` pelo mecanismo local já existente, sem gravar segredo e sem impor profile local à produção. Atualize `.env.example`, Compose, README ou configuração equivalente conforme necessário.

Adicione testes para:

- `local` com HTTP loopback: aceito;
- `test` com HTTP loopback: aceito;
- sem profile com HTTP: rejeitado;
- `default` com HTTP: rejeitado;
- `prod` com HTTP: rejeitado;
- profile desconhecido com HTTP: rejeitado;
- combinação `local,prod` com HTTP: rejeitada;
- qualquer profile com HTTPS válido: aceito.

## 5. Preservações obrigatórias

- Token bruto continua aparecendo somente no POST 201.
- Banco, logs, eventos e GETs continuam sem token bruto.
- URL continua independente de Host e Forwarded.
- Resolução GET continua read-only, sem métricas ou evento.
- Respostas 404, 410 e 503, headers e correlação permanecem.
- Bindings continuam fora da URL e sem dados pessoais.
- Logo `frontend\images\segsense logo.png` permanece byte a byte idêntico.
- Não criar `/c/{token}` no frontend, `ContextInstance`, valor USER ou consentimento.
- Não materializar objetivo nem integrar Spider, Icatu ou mock.

## 6. Documentação

Crie `SEGSENSE_PRM_007_COR_001.md` com cópia integral deste prompt.

Atualize:

- `SEGSENSE_DAT_004` para incluir V8 e a FK da revisão aprovada;
- `SEGSENSE_SEC_002` para política fail-closed de profiles e HTTPS;
- `SEGSENSE_LNK_001` e `SEGSENSE_API_005` onde afetados;
- `SEGSENSE_REV_007` com os achados, correções e provas;
- PLN_001, índice e README com histórico e situação da etapa.

Registre novamente que `.cursor/rules/ecosystem-focus.mdc` foi alterado na execução original apesar da proibição expressa. Não tente restaurá-lo ou editá-lo sem conhecer seu estado anterior. Este corretivo deve gerar zero alterações novas fora de `segsense/`.

Não altere `SPIDER-ARCH-017`.

## 7. Testes e validação

Execute:

- testes SQL da FK para revisão aprovada;
- testes dos bindings após a auditoria do item 3;
- testes completos de configuração HTTPS e profile;
- regressões de token, emissão, resolução, revogação, estados e CORS;
- `backend\mvnw.cmd verify`;
- frontend `npm ci`, lint, testes e build;
- Flyway V1–V8 em banco vazio;
- V8 incremental sobre o volume atual, sem `down -v`;
- `flyway:validate` e histórico V1–V8;
- HTTP real: `system/info` 200, token inválido 404 com headers, admin 401 com correlação;
- inspeção de token bruto, segredos, PII, logs e arquivos externos.

Após reinícios necessários, devolva PostgreSQL, backend e frontend funcionais nas portas documentadas.

## 8. Critérios de aceite

- PostgreSQL rejeita link para revisão existente mas não aprovada;
- FK da revisão aprovada convive com FKs de revisão e escopo;
- configuração sem profile, default, produção ou desconhecida exige HTTPS;
- somente local/test explícitos admitem HTTP em loopback;
- ambiente local declara seu profile explicitamente;
- proteção de binding foi endurecida ou recebeu justificativa técnica verificável;
- nenhuma regressão funcional ou de segurança;
- V1–V7 intactas e V8 incremental;
- logo preservado;
- nenhuma alteração nova fora de `segsense/`.

## 9. Devolutiva obrigatória

Apresente:

1. confirmação dos dois desvios;
2. desenho e prova da FK para revisão aprovada;
3. resultado da auditoria e eventual endurecimento dos bindings;
4. política final de profiles e HTTPS;
5. declaração explícita do profile local;
6. migrations V1–V8 e aplicação incremental;
7. testes, builds e evidências HTTP;
8. inspeção de token, logs, PII, CORS e segredos;
9. arquivos e documentos alterados;
10. hash do logo preservado;
11. Git e confirmação de zero novas alterações externas;
12. ausências preservadas.

Não faça commit, push ou deploy.
