# SEGSENSE_PRM_007 — Link contextual seguro e resolução controlada

## Controle

- Projeto: SegSense
- Identificador: SEGSENSE_PRM_007
- Versão: 1.0
- Data: 04/09/2026
- Etapa anterior: SEGSENSE_PRM_006 e corretivo único APROVADOS

## Prompt para o Cursor

Implemente o `SEGSENSE_PRM_007` em `C:\Projetos\segsense`, no monorepo existente `leaction-ecosystem`.

Leia integralmente o índice documental, todos os documentos SegSense vigentes, `SPIDER-ARCH-017`, migrations V1–V6, código e testes atuais. Dê atenção especial a ARQ_001/002, DOM_002, GOV_001, DAT_002/003, API_003/004, SEC_001, PLN_001 e REV_006.

Preserve o PRM_006 aprovado, inclusive a V6, a imutabilidade das submissões e a segregação de responsabilidades. Não altere V1–V6. Não altere Spider, Panne, `.cursor/` ou qualquer outro produto/caminho externo a `segsense/`. Não crie Git aninhado, não altere remotes e não faça commit, push ou deploy.

O logo oficial existente está em `C:\Projetos\segsense\frontend\images\segsense logo.png`. Preserve esse ativo. Use-o somente se houver identificação visual administrativa nesta etapa; não crie outro logo, não substitua o arquivo e não antecipe a experiência pública completa do PRM_008.

## 1. Objetivo

Implementar a emissão administrativa, consulta, resolução e revogação de **links contextuais seguros** vinculados a uma oportunidade com autorização interna PUBLISHED e à sua revisão aprovada exata.

O caso de referência é um artigo sobre quebra de safra que contém um link para iniciar futuramente uma jornada de proteção. O endereço público não deve carregar `riskType=quebra-safra`, IDs internos, objetivo, dados pessoais ou JSON. Ele conterá somente um token aleatório opaco. O contexto editorial não pessoal ficará associado ao link no banco e será recuperado após resolução controlada.

Nesta etapa:

- há publicação concreta do identificador/link;
- há associação opcional de valores contextuais fornecidos pelo publicador;
- há resolução pública para um envelope seguro e mínimo;
- ainda não há formulário público, coleta de valores do usuário, consentimento, renderização completa da jornada, envio de objetivo, Spider, Icatu ou provedor mock.

## 2. Limites arquiteturais

SegSense continua projeto independente. Spider é apenas integração futura e não deve ser alterada nem chamada.

Não implementar:

- frontend chamando Spider;
- client, endpoint ou contrato fictício da Spider;
- integração direta ou indireta com Icatu;
- aplicação mock de provedor dentro do SegSense ou da Spider;
- IA, recomendação, produto, cobertura, prêmio, preço ou elegibilidade;
- dados pessoais, identificação do usuário final ou fingerprinting;
- login público, sessão, cookie de rastreamento ou token de autenticação;
- consentimento ou valores de campos com origem exclusivamente `USER`;
- materialização/envio de `objectiveTemplate`.

## 3. Aggregate PublishedContextLink

Crie um aggregate com identidade estável e ciclo próprio, separado da `ContextualOpportunity`:

- `id`: UUID interno, nunca exposto na URL pública;
- `publisherId`, `channelId`, `environmentId`, `opportunityId`;
- `revisionNumber`: obrigatoriamente a revisão aprovada e corrente na emissão;
- `placementKey`: identificador administrativo imutável, `^[a-z][a-z0-9-]{2,79}$`, único por oportunidade/revisão;
- `label`: nome administrativo de 5 a 120 caracteres;
- `tokenDigest`: SHA-256 do token aleatório; nunca persistir o token bruto;
- `tokenHint`: no máximo os primeiros 8 caracteres ou identificador não secreto para suporte;
- `status`: `ACTIVE` ou `REVOKED`; expiração é efetiva pela data, sem scheduler;
- `issuedAt`, `issuedBy`, `expiresAt`, `revokedAt`, `revokedBy`, `revocationReason`;
- `version`: concorrência otimista;
- correlation IDs de emissão e revogação;
- bindings contextuais imutáveis do publicador.

Invariantes:

- emitir somente quando a oportunidade estiver `PUBLISHED`, `effectivelyPublished=true`, a revisão aprovada for a corrente e a janela estiver aberta;
- `expiresAt` é obrigatório, UTC, futuro e nunca posterior ao `validUntil` da revisão quando ele existir;
- adote prazo máximo configurável, com padrão local de 30 dias e limite absoluto documentado de 90 dias;
- o link não prolonga nem substitui a validade da oportunidade;
- revogação é explícita, terminal, exige `expectedVersion` e justificativa administrativa de 10 a 500 caracteres;
- pausar, revogar, expirar ou tornar indisponível a oportunidade impede a resolução, ainda que o link permaneça `ACTIVE` no seu registro;
- retomada da oportunidade não ressuscita link revogado ou expirado;
- múltiplos links são permitidos para placements diferentes;
- não reutilizar token, não reativar nem editar link emitido; para mudança, revogar e emitir outro.

## 4. Token e URL

Gere o token com CSPRNG, no mínimo 256 bits, codificado em Base64 URL-safe sem padding.

Requisitos:

- token bruto aparece somente uma vez, na resposta de emissão;
- banco, logs, eventos, erros, métricas e respostas posteriores nunca contêm token bruto;
- persistir somente `SHA-256(token)` em formato binário ou hexadecimal canônico, com UNIQUE;
- comparação e resolução não devem percorrer tokens nem produzir diferença evitável de comportamento;
- não usar UUID simples, ID sequencial, slug previsível, JWT ou payload autocontido;
- não colocar assinatura, contexto ou metadados legíveis na URL;
- não aceitar token por query string; usar um único segmento de path;
- limitar formato e tamanho antes de calcular digest;
- aplicar `Cache-Control: no-store`, `Pragma: no-cache`, `Referrer-Policy: no-referrer` e `X-Content-Type-Options: nosniff` na emissão e resolução;
- nunca logar o path público completo; sanitize/redact o segmento do token em access/application logs controlados pelo projeto.

A URL deve ser construída exclusivamente a partir de configuração validada, por exemplo `SEGSENSE_PUBLIC_BASE_URL`, e nunca a partir de `Host`, `Forwarded` ou `X-Forwarded-*` da requisição.

No ambiente local, documente valor seguro coerente com as portas atuais. A configuração deve:

- exigir `https` fora do profile local/test;
- rejeitar userinfo, fragment, query, path inesperado e host vazio;
- remover barra final de forma determinística;
- permitir origem local explícita apenas em desenvolvimento/teste.

Formato público:

```text
{configuredPublicBaseUrl}/c/{opaqueToken}
```

## 5. Binding contextual do publicador

Na emissão, aceite coleção `publisherContext` com pares `fieldKey` e valor escalar tipado. Não aceite objeto arbitrário ou chave desconhecida.

Regras:

- somente campos declarados na revisão aprovada com `source=PUBLISHER` ou `source=EITHER` podem receber binding;
- campos `source=USER` nunca recebem valor nesta etapa;
- cada chave aparece uma vez;
- valores obedecem rigorosamente ao tipo declarado:
  - `TEXT`: string normalizada, 1 a 200 caracteres;
  - `NUMBER`: número JSON finito, faixa documentada e representação canônica; não aceitar string numérica;
  - `BOOLEAN`: boolean JSON; não aceitar string;
  - `DATE`: string ISO `YYYY-MM-DD`, validada como data real;
  - `ENUM`: correspondência exata com um `allowedValue` da revisão;
- rejeitar arrays, objetos, null, HTML, script e JSON serializado como texto;
- aplicar a proibição já vigente de dados pessoais;
- todos os campos obrigatórios cuja origem seja `PUBLISHER` devem estar vinculados;
- campo obrigatório `EITHER` pode permanecer sem binding para preenchimento futuro pelo usuário;
- não aceitar binding em oportunidade `STATIC`;
- o binding é snapshot imutável do link e não altera a revisão.

Exemplo administrativo conceitual, nunca convertido em query string:

```json
{
  "placementKey": "artigo-quebra-safra-2026",
  "label": "Artigo — quebra de safra",
  "expiresAt": "2026-10-01T00:00:00Z",
  "publisherContext": {
    "riskType": "quebra-safra",
    "cropType": "soja"
  }
}
```

Se o contrato HTTP usar lista tipada em vez de objeto, documente a escolha e preserve rejeição de chaves duplicadas. Não renderize `objectiveTemplate` nesta etapa.

## 6. Persistência V7

Crie `V7__create_published_context_links.sql`. Não altere V1–V6.

Modele:

- `published_context_link` com aggregate, escopo completo, revisão, digest único, estado, validade, auditoria e version;
- `published_context_link_binding` com link, field key, tipo declarado e colunas de valor tipadas ou representação canônica segura;
- `published_context_link_event` append-only para `ISSUED` e `REVOKED`, sem token bruto;
- vínculo composto da oportunidade/revisão à mesma revisão aprovada;
- FKs compostas que preservem Publisher, Channel, Environment e Opportunity no mesmo escopo;
- unicidade `(opportunity_id, revision_number, placement_key)`;
- unicidade de field key por link;
- CHECKs de formato, status, datas, digest, hint e justificativa;
- índices para resolução pelo digest, listagem administrativa e expiração;
- `NO ACTION`, sem cascade, delete ou trigger de negócio;
- `TIMESTAMPTZ`, nomes explícitos e `ddl-auto=none`.

Antes de criar FKs, adicione somente as chaves candidatas necessárias, documentando-as. Não enfraqueça as constraints anteriores.

Estado do link e evento devem ser persistidos atomicamente. Entidades de binding e evento são insert-only/imutáveis. A revogação pode atualizar somente o aggregate do link e inserir o evento correspondente.

## 7. API administrativa

Base administrativa:

```text
/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}/opportunities/{opportunityId}/links
```

Implemente:

- `POST /links` — emitir; devolve 201 e o token/URL uma única vez;
- `GET /links` — listar metadados sem token/URL secreta, com cursor opaco;
- `GET /links/{linkId}` — consultar metadados, bindings e efetividade, sem token bruto;
- `POST /links/{linkId}/revoke` — revogar com `expectedVersion` e justificativa;
- `GET /links/{linkId}/events` — trilha append-only paginada.

Authorities:

- `segsense.link.read` — consultas administrativas;
- `segsense.link.manage` — emissão e revogação.

Além da authority, a emissão deve exigir sujeito diferente do autor da aprovação/ativação somente se essa segregação já estiver formalmente estabelecida no GOV_001; não invente um novo quarto papel. Documente a decisão adotada. Mantenha deny-by-default e 401 real sem IdP.

Cross-scope retorna 404. PUT, PATCH, DELETE, reativação, rotação in-place e recuperação de token são proibidos.

## 8. Resolução pública

Implemente:

```text
GET /api/v1/public/context-links/{opaqueToken}
```

Esse endpoint é público e não cria sessão nem altera estado. Ele devolve somente um envelope mínimo para o futuro PRM_008:

- `applicationId=SEGSENSE`;
- `resolutionId`: novo UUID de correlação da resolução, não persistido como identidade de usuário;
- título e CTA da revisão aprovada;
- `contextMode`;
- resumo contextual **não materializado** ou estrutura segura que diferencie template de valores;
- bindings não pessoais do publicador;
- campos ainda requeridos do usuário apenas como definições (`key`, `label`, `type`, `required`, `allowedValues`), sem valores;
- validade efetiva;
- indicação de que nenhuma cotação, elegibilidade ou recomendação foi realizada.

Não devolver:

- IDs internos de Publisher, Channel, Environment, Opportunity, Revision ou Link;
- `objectiveTemplate`;
- autores, revisores, justificativas, correlation IDs internos ou trilha;
- digest, hint ou token;
- metadados Spider/Icatu;
- qualquer dado pessoal.

Comportamento:

- token inexistente ou malformado: 404 `CONTEXT_LINK_NOT_FOUND`, resposta uniforme;
- link revogado: 410 `CONTEXT_LINK_REVOKED`;
- link vencido ou oportunidade expirada: 410 `CONTEXT_LINK_EXPIRED`;
- oportunidade pausada ou hierarquia indisponível: 503 `CONTEXT_LINK_TEMPORARILY_UNAVAILABLE`, com `Retry-After` conservador e sem revelar a causa interna;
- oportunidade não mais autorizada por razão terminal: 410 `CONTEXT_LINK_UNAVAILABLE`;
- sucesso: 200 com headers de não cache e correlação.

Não atualize contador, `lastAccessedAt` ou evento por resolução nesta etapa. Métricas e atribuição pertencem a etapa posterior. Assim, GET permanece sem mutação de negócio.

## 9. Proteções operacionais

- limite o tamanho do token e rejeite formato inválido antes do hash;
- limite payload administrativo e quantidade de bindings a no máximo 20;
- configure limite básico de requisições para resolução pública usando mecanismo local simples e testável somente se já houver componente adequado; não adicione infraestrutura distribuída fictícia;
- se rate limiting não puder ser corretamente implementado nesta arquitetura, documente-o como requisito obrigatório de gateway/hardening, sem simular proteção;
- use respostas de tempo e formato razoavelmente uniformes para token inválido;
- não inclua token em exceções;
- não faça redirect aberto;
- não aceite `returnUrl`, callback ou destino fornecido pelo cliente;
- CORS público deve ser explicitamente definido; não ampliar o CORS administrativo com curinga. Como o consumo inicial é navegação por link, não habilite `*` sem necessidade demonstrada.

## 10. Frontend administrativo

Acrescente ao detalhe da oportunidade PUBLISHED:

- painel “Links contextuais”;
- formulário de emissão com placement, label, expiração e bindings permitidos;
- campos tipados derivados da revisão, nunca input JSON livre;
- explicação de que valores `USER` não são coletados aqui;
- confirmação explícita de que o endereço não contém os valores informados;
- exibição do link completo uma única vez após emissão, com ação de copiar;
- aviso inequívoco de que ele não poderá ser recuperado depois;
- lista e detalhe sem token, com ACTIVE/REVOKED/EXPIRED efetivo;
- revogação com justificativa e confirmação;
- estados loading, vazio, sucesso, 401, 403, 404, 409, 410, 422 e erro;
- atualização após emissão/revogação.

Não criar ainda a página pública final do usuário. Para testes manuais, a resolução pode continuar sendo JSON. O PRM_008 usará o contrato de resolução para construir a experiência.

Use o logo existente somente no shell administrativo se isso respeitar o padrão visual atual. Preserve nome, proporção e arquivo de origem.

## 11. Erros mínimos

Preserve envelope e correlation ID. Adicione/documente:

- `OPPORTUNITY_NOT_PUBLISHED` — 422;
- `APPROVED_REVISION_MISMATCH` — 409;
- `LINK_PLACEMENT_CONFLICT` — 409;
- `LINK_EXPIRY_INVALID` — 422;
- `INVALID_PUBLISHER_CONTEXT` — 400;
- `REQUIRED_PUBLISHER_CONTEXT_MISSING` — 422;
- `CONTEXT_LINK_NOT_FOUND` — 404;
- `CONTEXT_LINK_REVOKED` — 410;
- `CONTEXT_LINK_EXPIRED` — 410;
- `CONTEXT_LINK_UNAVAILABLE` — 410;
- `CONTEXT_LINK_TEMPORARILY_UNAVAILABLE` — 503;
- `CONCURRENT_MODIFICATION` — 409.

Erros nunca expõem token, digest, SQL, constraint, stack ou existência cross-scope.

## 12. Documentação

Crie:

- `SEGSENSE_LNK_001.md` — arquitetura do link, token, ameaça, emissão, resolução e revogação;
- `SEGSENSE_DAT_004.md` — V7, relacionamentos, constraints, índices e rollback conceitual;
- `SEGSENSE_API_005.md` — APIs administrativas e resolução pública;
- `SEGSENSE_SEC_002.md` — threat model do link, exposição, logs, headers, configuração e riscos residuais;
- `SEGSENSE_REV_007.md` — evidências, riscos, decisões e SAT-01 a SAT-10;
- `SEGSENSE_PRM_007.md` — cópia integral deste prompt.

Atualize ARQ_002, DOM_002, GOV_001, SEC_001, PLN_001, READMEs e índice somente onde afetados. Registre PRM_006 e seu corretivo como aprovados. Não altere `SPIDER-ARCH-017`.

Inclua diagrama textual do fluxo:

```text
Operador -> BFF SegSense -> token CSPRNG -> digest no PostgreSQL
                                   |
                                   +-> token bruto mostrado uma vez

Visitante -> /c/{token} -> BFF SegSense -> digest -> vínculo contextual interno
                                             |
                                             +-> envelope público mínimo
```

## 13. Testes obrigatórios

Cubra no mínimo:

- emissão somente para oportunidade PUBLISHED e efetiva;
- vínculo exato à revisão aprovada/corrente;
- expiração obrigatória, futura, limite máximo e limite da revisão;
- token com 256 bits, Base64URL, unicidade e digest persistido;
- token bruto ausente do banco, logs, eventos e consultas posteriores;
- URL criada apenas da configuração, independentemente de Host/Forwarded malicioso;
- validação da configuração em local/test e fora deles;
- placement único e múltiplos placements válidos;
- bindings TEXT, NUMBER, BOOLEAN, DATE e ENUM;
- rejeição de tipo coercivo, chave desconhecida, duplicada, objeto, array, null, HTML/script, JSON textual e dado pessoal;
- regra de source PUBLISHER, USER e EITHER;
- obrigatórios do publicador e máximo de 20 bindings;
- resolução válida e envelope mínimo;
- ausência de IDs internos e `objectiveTemplate` na resposta pública;
- token inválido/malformado uniforme;
- revogado, expirado, pausado, hierarquia suspensa e estado terminal;
- retomada não ressuscita link revogado/expirado;
- revogação concorrente, terminal e com evento atômico;
- nenhum evento ou contador criado por GET público;
- headers `no-store`, `no-referrer`, `nosniff` e correlação;
- nenhum CORS administrativo ampliado indevidamente;
- 401/403 e authorities administrativas;
- endpoint público acessível sem autenticação apenas na rota exata;
- cross-scope e métodos proibidos;
- FKs compostas, CHECKs e unicidades por SQL direto;
- V1–V7 em banco vazio e V7 incremental sobre volume existente;
- interface administrativa, exibição única, cópia e impossibilidade de recuperação;
- regressões backend, frontend e ArchUnit.

Use `Clock`, gerador de token e configuração injetáveis para testes determinísticos, sem enfraquecer o gerador de produção.

## 14. Validação final

Execute:

- `backend\mvnw.cmd verify`;
- frontend `npm ci`, lint, testes e build;
- Compose sem remover volume;
- aplicação incremental da V7 no volume atual;
- histórico Flyway V1–V7;
- endpoints públicos existentes;
- resolução real com token inválido;
- 401 real nas rotas administrativas;
- sucessos completos em Testcontainers/Spring Security test.

Faça inspeção específica por token bruto e segredos nos logs, banco, respostas e arquivos. Inspecione alterações fora de `segsense/`. Preserve o ambiente operacional nas portas documentadas após a validação.

## 15. Critérios de aceite

- URL contém apenas token opaco de alta entropia;
- token bruto é irrecuperável após a resposta inicial;
- contexto editorial não pessoal fica no servidor, validado contra a revisão aprovada;
- link se torna inutilizável com revogação, expiração ou perda de efetividade;
- resolução pública é mínima, não mutante e sem vazamento interno;
- nenhuma experiência, consentimento, objetivo ou integração externa é simulada;
- V7, testes, builds e documentos aprovados;
- logo oficial preservado;
- nenhuma alteração fora de `segsense/`.

## 16. Devolutiva obrigatória

Apresente:

1. arquivos criados e alterados;
2. aggregate, estados e invariantes do link;
3. geração, armazenamento e exposição única do token;
4. configuração e construção segura da URL;
5. binding contextual do publicador, tipos e validações;
6. V7, FKs, constraints e aplicação incremental;
7. APIs, authorities e matriz de exposição;
8. resolução pública e respostas por estado;
9. frontend administrativo e uso/preservação do logo;
10. testes, builds, Flyway e evidências HTTP;
11. inspeção de token, logs, PII, segredos e CORS;
12. SAT-01 a SAT-10;
13. Git e alterações externas;
14. ausências confirmadas: página pública final, valor USER, consentimento, objetivo materializado, Spider, Icatu, mock, IA, produto, preço, cobertura e elegibilidade.

Não faça commit, push ou deploy.
