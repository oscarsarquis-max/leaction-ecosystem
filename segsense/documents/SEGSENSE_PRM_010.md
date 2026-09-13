# SEGSENSE_PRM_010 — Preparação do contrato SegSense–Spider sem interface fictícia

## Controle

- Projeto: SegSense
- Identificador: SEGSENSE_PRM_010
- Versão: 1.0
- Data: 12/09/2026
- Etapa anterior: `SEGSENSE_PRM_009` aprovado com ressalvas após `SEGSENSE_PRM_009_COR_001`
- Execução: Cursor, somente `C:\Projetos\segsense`

## Prompt para o Cursor

Execute o `SEGSENSE_PRM_010` exclusivamente em `C:\Projetos\segsense`, produto independente no monorepo `leaction-ecosystem`. Não altere Spider, Panne, `.cursor/` ou outro produto. Não faça commit, push nem deploy.

Leia integralmente os documentos vigentes do SegSense, sobretudo `SEGSENSE_ARQ_001`, `SEGSENSE_ARQ_002`, `SEGSENSE_ADR_001`, `SEGSENSE_ADR_002`, `SEGSENSE_PLN_001`, `SEGSENSE_FUN_002`, `SEGSENSE_DAT_005`, `SEGSENSE_API_006`, `SEGSENSE_SEC_003`, `SEGSENSE_REV_009`, `SEGSENSE_PRM_009_COR_001` e `documents/references/SPIDER-ARCH-017.md`. Inspecione **somente para leitura** a documentação e os schemas existentes em `C:\Projetos\spider`, especialmente `spider/docs/architecture/SPIDER-ARCH-017-satellite-architecture.md`, contratos canônicos, Intent Contract e eventuais endpoints públicos. Cite caminhos, versões, status e trechos relevantes no relatório; não altere nenhum desses arquivos.

**Constatação inicial a confirmar no workspace:** o `SPIDER-ARCH-017` atualmente em `spider/docs/architecture` descreve Satellite Contract como ideal **não implementado** e distingue o Contextual Link e o SpiderBank desse contrato. A cópia em `segsense/documents/references/SPIDER-ARCH-017.md` é uma baseline arquitetural `PROPOSED`, mais extensa, não evidência de contrato executável. Schemas canônicos do Data Plane e `intent-contract-v1.schema.json` não se tornam automaticamente um Satellite Contract público. Se essa constatação permanecer verdadeira, siga o ramo **B** abaixo. Não tente preencher lacunas com convenções inventadas.

## 1. Correções herdadas da etapa anterior — executar antes do novo escopo

### 1.1 Imutabilidade do conjunto de campos aprovado

V10 impede UPDATE/DELETE em `consent_notice_field`, mas não demonstra que um `INSERT` SQL direto não possa acrescentar um campo a snapshot já aprovado. Investigue e prove o comportamento. Se o INSERT for possível, crie **V11 incremental**, sem alterar V1–V10, para impedir acréscimo de campos em snapshot associado a notice aprovado ou retirado. A regra deve permitir apenas criação legítima de campos de um novo snapshot DRAFT durante a transação apropriada. Não use uma proteção que torne impossível editar DRAFT/versionar notice.

Teste, por SQL direto no Testcontainers:

- INSERT de campo novo em snapshot APPROVED: rejeitado;
- INSERT em snapshot RETIRED: rejeitado;
- UPDATE/DELETE de campo/snapshot protegido: rejeitados;
- criação de novo snapshot DRAFT com seus campos: permitida;
- relacionamento de campo, revisão e classificação NON_PERSONAL permanece íntegro;
- hash do conteúdo aprovado continua representando o conjunto efetivamente aprovado.

Se encontrar outra possibilidade de alterar o conjunto efetivo por SQL direto, feche-a na mesma V11. Pré-valide dados existentes antes das constraints/triggers, sem reparo silencioso. Preserve volume e histórico Flyway.

### 1.2 Auditoria visual da jornada de sucesso

O PRM_009 não teve browser de sucesso por ausência de IdP. **Não** crie login fictício, bypass de segurança em runtime, seeded credential ou mock de produção para contornar isso.

Monte uma verificação isolada no classpath/ambiente de teste, usando o BFF real com fixture administrativa de teste e dados estritamente NON_PERSONAL, capaz de emitir link e notice sem alterar o perfil `local` de produção. Registre como a prova é executada e desmontada. Não grave token ou credencial em screenshot, log, arquivo permanente ou documentação. Se a ferramenta de browser continuar indisponível, execute testes de componentes e HTTP equivalentes, declare explicitamente **não verificado visualmente** e deixe o aceite visual para auditoria humana; não alegue cumprimento por inferência.

Valide, quando houver browser: público em 1440×900, 390×844 e 320×568; admin em 1440×900 e 768×1024; zoom 200%; fluxo de sucesso com BOOLEAN, DATE, NUMBER e ENUM; erros, Voltar, Corrigir informações, autorização, retirada, foco por teclado, sem rolagem horizontal. Use fixtures anônimas sem PII.

### 1.3 Dependências do frontend

O `npm ci` reportou duas vulnerabilidades high. Inspecione o relatório com versões e cadeia transitiva, sem presumir exploração do runtime. Se houver atualização compatível e reproduzível, aplique somente dentro de `segsense/frontend`, rode lint/test/build e documente. Se exigir major ou risco de regressão, preserve o lockfile, registre mitigação e decisão fundamentada para PRM_017. Não faça `npm audit fix --force` indiscriminado.

Registre as três correções/ressalvas em `SEGSENSE_REV_010` com evidência, não apenas declaração.

## 2. Objetivo contratual desta etapa

Determinar, com evidência do código e documentos atuais, se existe um **Satellite Contract executável, público e versionado** que o SegSense possa implementar sem invenção. Separar quatro camadas que não são equivalentes:

1. ideal arquitetural de satélite;
2. Intent Contract interno/contextual;
3. contrato canônico de execução no Data Plane;
4. contrato externo Satellite → Spider, incluindo identidade, autenticação, autorização, preview, confirmação, assincronia, erro e idempotência.

Não copiar classes internas da Spider para o SegSense. Não usar schema interno apenas porque ele contém campos semanticamente semelhantes. Não transformar Contextual Link ou DEMO SpiderBank em implementação do Satellite Contract.

## 3. Matriz de evidência obrigatória

Crie `SEGSENSE_INT_001.md` com matriz para cada capacidade abaixo. Colunas mínimas: requisito, evidência exata (arquivo/versão/endpoint/teste), status (`PUBLIC_EXECUTABLE`, `INTERNAL_ONLY`, `PROPOSED`, `ABSENT`), implicação para SegSense, bloqueio e responsável pela definição.

- identidade de aplicação e registro de satélite;
- autenticação do satélite e do usuário/ator;
- autorização/catálogo de solicitações permitidas;
- schema de entrada versionado e semântica do objetivo;
- contexto, origem/canal, constraints e referências;
- correlação local versus `requestId`, `decisionId`, `planId`, `executionId`, `interactionId`;
- preview de compreensão, sem execução;
- confirmação explícita e ligação ao preview;
- submissão, idempotência e proteção contra replay;
- estados assíncronos, consulta e/ou callback;
- erros canônicos, indisponibilidade e timeouts;
- transporte seguro, TLS, trust e segredos;
- retenção e minimização dos valores consentidos;
- versão/compatibilidade/evolução;
- testes contratuais publicados pela Spider.

Para qualquer item sem artefato executável, marque `PROPOSED` ou `ABSENT`; não invente valores de exemplo para fazê-lo parecer completo.

## 4. Gate binário de implementação

### Ramo A — contrato executável realmente existente

Use este ramo **somente** se houver artefato verificável da Spider com schema externo, versão, endpoint, autenticação/autorização, exemplos válidos e testes de contrato. Cite tudo antes de implementar.

Nesse caso, implemente **somente** tipos/validadores e um mapper interno SegSense → contrato publicado, sem client HTTP, credenciais, chamadas, submissão de objetivo ou UI que finja preview/execução. O mapper deve:

- partir de ContextInstance `AUTHORIZED`, não expirada/não retirada, vinculada ao link/revisão/notice exatos;
- levar apenas campos autorizados e permitidos pela finalidade;
- distinguir contexto do publicador de informação fornecida pelo usuário;
- representar ator anônimo apenas se o contrato publicado o permitir; nunca inventar identidade pessoal;
- não escolher route, adapter, executor, Icatu, produto, capability ou Execution Plan;
- preservar correlação como campos distintos, sem fabricar IDs da Spider;
- falhar fechado diante de ausência de campo obrigatório, versão incompatível ou consentimento retirado;
- ser testado contra fixtures oficiais do contrato, não fixtures inventadas.

Documente a implementação em `SEGSENSE_ARQ_003.md` e `SEGSENSE_API_007.md`. Mesmo no ramo A, PRM_011 continua sendo o limite para qualquer integração HTTP real.

### Ramo B — contrato executável ausente/incompleto (esperado)

Não implemente payload, DTO denominado Satellite Contract, mapper, client, endpoint, tabela, migration ou botão de continuidade à Spider. A entrega contratual será **documental e verificável**:

- `SEGSENSE_INT_001.md`: matriz de evidência e lacunas;
- `SEGSENSE_ARQ_003.md`: fronteira preparada, sem diagrama que sugira conexão operacional;
- `SEGSENSE_ADR_003.md`: decisão de bloquear implementação executável até a Spider publicar contrato externo;
- `SEGSENSE_REQ_002.md`: lista precisa do que a Spider precisa fornecer para desbloquear PRM_011, sem redigir um contrato em nome da Spider;
- `SEGSENSE_REV_010.md`: revisão da etapa e SAT-01 a SAT-10.

O SegSense permanece funcional localmente. A UI de autorização continua terminando honestamente no SegSense: nada foi enviado à Spider ou seguradora. Não exponha CTA de preview, confirmação, envio ou resultado que não existe.

## 5. Reconciliação documental obrigatória

Compare a cópia `segsense/documents/references/SPIDER-ARCH-017.md` com a versão atualmente presente no projeto Spider. Registre que são artefatos distintos, seus status, datas/versões quando houver e possível divergência de escopo. Não substitua nem edite a cópia íntegra; não declare que a versão PROPOSED foi aceita pela Spider. Atualize `SEGSENSE_ARQ_001`/`ARQ_002` e PLN apenas onde necessário para explicitar a realidade executável sem apagar o ideal arquitetural.

Registre também a decisão comercial já dada pelo usuário: uma futura seção de apresentação dedicada à Icatu Seguros deverá identificar claramente a simulação. A integração inicial será mockada a partir de informações públicas verificadas em `https://portal-api.icatuseguros.com.br/apis`, por **aplicação independente**, jamais incorporada ao SegSense ou à Spider. Isto é **planejamento**, não escopo de implementação do PRM_010. PRM_012/013 continuam responsáveis por levantamento/contrato e mock; não acesse o portal nem crie seção comercial nesta etapa.

## 6. Segurança e limites

- Não modificar Spider, inclusive documentação, schemas, APIs, banco, runtime ou testes.
- Não declarar SAT-03 atendido por documentação conceitual.
- Não declarar autenticação de satélite, usuário, Guard ou Policy implementada.
- Não criar identidade fictícia, token, URL, client secreto, callback, rota ou resposta da Spider.
- Não exportar valores coletados ou evidência de autorização para arquivos de fixture/log.
- Não usar dados pessoais/sensíveis em exemplos.
- Não alterar autorização/admin para viabilizar demonstração fora de testes isolados.
- Não implementar Icatu nem provider mock agora.
- Não tocar V1–V10; V11 é permitida somente para a correção herdada SQL, se necessária.

## 7. Testes e validação

Após as correções herdadas:

- backend `mvnw.cmd verify` completo, Testcontainers com V1–V11 quando houver V11, Flyway validate no volume existente sem apagar dados;
- frontend `npm ci`, lint, testes e build;
- testes negativos de INSERT/UPDATE/DELETE de campos/snapshots aprovados e preservação do fluxo DRAFT;
- testes de HTTP local, 401/403 e CORS sem ampliar superfície pública;
- inspeção do código por qualquer client/endpoint/payload Spider/Icatu novo;
- inspeção do Git por alterações apenas em `segsense/`;
- hash do logo oficial antes/depois;
- ambiente local preservado em Postgres `:5437`, backend `:8088` profile `local`, frontend `:5178`.

Se ramo A for excepcionalmente justificado, acrescente testes de compatibilidade com os artefatos oficiais da Spider. Se ramo B, teste que não foram criados endpoints, DTOs ou chamadas operacionais.

## 8. Documentação e índice

Crie cópia integral deste prompt em `documents/SEGSENSE_PRM_010.md`. Crie os documentos do ramo escolhido e `SEGSENSE_REV_010.md`. Atualize índice, PLN, READMEs e documentos afetados com versão/histórico. O status correto no ramo B é **preparado documentalmente / implementação bloqueada por contrato externo ausente**, não “Satellite Contract implementado”.

## 9. Critérios de aceite

- ressalva SQL comprovadamente fechada por V11, se a lacuna existir;
- auditoria visual executada ou lacuna registrada sem afirmação falsa;
- vulnerabilidades high investigadas e tratadas ou justificadamente transportadas;
- matriz de evidência distingue contrato externo de schemas internos/ideais;
- ramo A ou B escolhido por artefato verificável, não por expectativa;
- nenhuma interface executável inventada;
- nenhum envio à Spider, Icatu ou mock;
- nenhum comportamento falso na UI;
- testes/builds/Flyway/HTTP e Git validados;
- logo preservado;
- nenhum commit, push ou deploy.

## 10. Devolutiva obrigatória

Apresente:

1. documentos/arquivos efetivamente lidos, com caminho e status;
2. correção SQL herdada, V11 e provas negativas/positivas;
3. auditoria visual por viewport/teclado ou lacuna explícita;
4. resultado do `npm audit`, versão/cadeia/risco e decisão;
5. matriz-resumo dos 14 requisitos do Satellite Contract;
6. evidência para a escolha do ramo A/B;
7. arquivos criados/alterados e documentação indexada;
8. limites preservados no SegSense e ausência de código Spider/Icatu/mock;
9. testes, builds, Flyway, HTTP real, ambiente e logo;
10. SAT-01 a SAT-10;
11. Git, alterações externas e ausência de commit/push/deploy;
12. riscos residuais e condições objetivas para desbloquear PRM_011.

Não faça commit, push ou deploy.
