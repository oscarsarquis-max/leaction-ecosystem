# SEGSENSE_PRM_006 — Governança, aprovação e ativação de publicação

## Controle

- Projeto: SegSense
- Identificador: SEGSENSE_PRM_006
- Versão: 1.0
- Data: 04/09/2026
- Etapa anterior: SEGSENSE_PRM_005 APROVADO COM RESSALVAS

## Prompt para o Cursor

Implemente o `SEGSENSE_PRM_006` em `C:\Projetos\segsense`, dentro do monorepo existente `leaction-ecosystem`.

Leia integralmente o índice documental e todos os documentos SegSense vigentes, em especial ARQ_001/002, ADRs, DOM_001/002, DAT_001/002, API_001/002/003, SEC_001, PLN_001, REV_005, PRM_005, `SPIDER-ARCH-017`, migrations V1–V4, código e testes atuais.

Preserve tudo o que não pertencer ao escopo. Não altere Spider, Panne ou qualquer outro produto. Não crie repositório Git aninhado, não altere remotes e não faça commit, push ou deploy.

## 1. Objetivo

Implementar a governança editorial e técnica que transforma uma revisão DRAFT de oportunidade contextual em uma revisão submetida, aprovada e com publicação autorizada, mantendo decisão humana explícita, segregação de responsabilidades, histórico imutável e rastreabilidade.

Nesta etapa, `PUBLISHED` significa somente **autorização ativa para publicação** dentro do SegSense. Não significa que exista link, página pública, distribuição, envio à Spider ou integração externa. O link contextual seguro será tratado exclusivamente no PRM_007.

Não implementar `ContextInstance`, valores dinâmicos, URL, token, assinatura, resolução pública, consentimento, IA, recomendação, produto de seguro, preço, cobertura, elegibilidade, Spider, Icatu ou provedor mock.

## 2. Correções herdadas da etapa anterior

Antes do novo escopo, corrija a interface de oportunidades sem alterar o contrato válido do PRM_005:

1. permitir marcar e desmarcar `required` em cada campo contextual;
2. permitir remover campo adicionado, preservando a ordem contínua enviada ao backend;
3. permitir informar e editar `validFrom` e `validUntil`, com conversão explícita para UTC e mensagem clara de validação;
4. após criar nova revisão, recarregar o detalhe e o histórico para que a revisão recém-criada apareça imediatamente, sem refresh manual.

Inclua testes de frontend específicos para os quatro itens. Registre a resolução em `SEGSENSE_REV_006`. Não prossiga ao novo escopo se houver regressão no PRM_005.

## 3. Princípios de governança

- Toda decisão se aplica a uma revisão exata e imutável.
- Nenhuma revisão é implicitamente aprovada por criação, edição, data ou chamada técnica.
- Submeter, decidir e ativar são comandos explícitos e auditáveis.
- A pessoa que criou ou submeteu a revisão não pode aprová-la nem rejeitá-la.
- A pessoa que aprovou não pode executar a ativação da publicação da mesma revisão.
- Identidade é obtida apenas do `Authentication` confiável já modelado; nunca de campo do payload ou header ad hoc.
- Ausência de IdP continua produzindo 401 no runtime. Não criar usuário, login, token, API key ou autenticação simulada.
- Regras desta etapa são editoriais e técnicas. Não representam análise atuarial, recomendação, elegibilidade ou decisão securitária.
- Nenhum estado ou comando local pode decidir capability, route, adapter ou plano da Spider.

Implemente segregação por `subjectId`, não apenas por authority. Nos testes, use sujeitos distintos. Não invente tenant enquanto o modelo de isolamento não estiver formalmente definido.

## 4. Ciclo de vida

Amplie o ciclo de vida da `ContextualOpportunity`:

```text
DRAFT
  -> UNDER_REVIEW        submit

UNDER_REVIEW
  -> DRAFT               return-for-changes
  -> APPROVED            approve
  -> REVOKED             reject

APPROVED
  -> PUBLISHED           activate-publication
  -> REVOKED             revoke

PUBLISHED
  -> PAUSED              pause
  -> REVOKED             revoke
  -> EXPIRED             expire

PAUSED
  -> PUBLISHED           resume
  -> REVOKED             revoke
  -> EXPIRED             expire
```

Regras obrigatórias:

- `DRAFT` é o único estado em que uma nova revisão pode ser criada.
- `submit` fixa `submittedRevision` igual à revisão corrente e cria submissão imutável.
- `return-for-changes` exige justificativa, encerra a submissão e volta a DRAFT; uma futura edição cria N+1 normalmente.
- `approve` e `reject` decidem a submissão corrente, exigem `expectedVersion` e revisão/base coerentes.
- aprovação vincula exatamente `approvedRevision`; ela não migra para revisão posterior.
- `activate-publication` exige oportunidade APPROVED, revisão aprovada ainda corrente, hierarquia efetivamente disponível e janela temporal válida.
- `pause`, `resume`, `revoke` e `expire` são comandos explícitos; idempotência por estado não deve mascarar transição inválida.
- `revoke` exige justificativa e é terminal.
- `reject` produz REVOKED e exige justificativa; não reutilize REVOKED como autorização futura.
- `expire` só é permitido quando `validUntil <= now`; antes disso retorna transição inválida.
- se `validUntil` já tiver passado, ativar ou retomar é proibido.
- se `validFrom` estiver no futuro, ativar ou retomar é proibido nesta etapa; não criar scheduler de ativação.
- suspensão de Publisher, Channel ou Environment não altera silenciosamente o estado persistido, mas torna `effectivelyPublishable=false` e impede ativação/retomada.
- uma autorização PUBLISHED com pai posteriormente suspenso permanece consultável, porém `effectivelyPublished=false`; não simular revogação automática.

Não implemente exclusão nem retorno de estados terminais.

## 5. Modelo de decisão e trilha imutável

Crie estruturas de domínio explícitas, evitando colocar toda a lógica no controller. Modele no mínimo:

- submissão da revisão, com revisão, autor e instante;
- decisão `APPROVED`, `RETURNED` ou `REJECTED`, com decisor, instante e justificativa quando exigida;
- ativação e mudanças de estado de publicação;
- evento histórico append-only para cada comando aceito;
- estado atual no aggregate para leitura e concorrência otimista.

Cada evento deve registrar:

- UUID próprio;
- oportunidade e revisão vinculada;
- tipo do evento;
- estado anterior e novo;
- `actorSubjectId`;
- instante UTC;
- justificativa normalizada quando aplicável;
- correlation ID da requisição.

Nunca registrar token, credencial, payload integral, valores de contexto de usuário ou dado pessoal. Justificativas são texto administrativo de 10 a 500 caracteres, sem HTML/script, e devem receber orientação visível de não inclusão de dados pessoais.

## 6. Persistência

Não altere V1–V4. Crie `V5__create_opportunity_governance.sql`.

A V5 deve:

- ampliar o CHECK de status de `contextual_opportunity` para todos os estados implementados;
- adicionar, de forma documentada, os campos atuais necessários para revisão submetida/aprovada e metadados de governança, ou criar tabela de estado 1:1 se tecnicamente mais seguro;
- criar tabelas append-only para submissões/decisões e eventos de ciclo de vida;
- preservar vínculo inequívoco com `(opportunity_id, revision_number)` por FK composta;
- impedir mais de uma submissão aberta para a mesma oportunidade;
- impedir mais de uma decisão para a mesma submissão;
- usar constraints nomeadas, CHECKs, UNIQUEs e índices para consulta cronológica;
- usar `TIMESTAMPTZ`, autoria técnica e correlation ID validados;
- manter `NO ACTION`, sem cascade, trigger de negócio ou deleção física;
- manter `ddl-auto=none`.

Não tente tornar um event store a fonte exclusiva do aggregate nesta etapa. O estado atual pode permanecer no aggregate, desde que atualizado na mesma transação da trilha append-only.

Documente rollback conceitual. Comprove V1–V5 em banco vazio e V5 incremental sobre o volume atual, sem apagar o volume.

## 7. Authorities

Adicione authorities distintas:

- `segsense.opportunity.submit` — submeter;
- `segsense.opportunity.review` — aprovar, rejeitar ou devolver para alterações;
- `segsense.publication.manage` — ativar, pausar, retomar, expirar e revogar;
- consultas permanecem em `segsense.opportunity.read`.

Para evitar ambiguidade, `return-for-changes` exige `segsense.opportunity.review`. `submit` exige `segsense.opportunity.submit`.

As authorities são necessárias, mas não substituem as regras de sujeito distinto. Demais métodos e rotas continuam deny-by-default.

## 8. Casos de uso e API

Mantenha a base existente:

```text
/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}/opportunities/{opportunityId}
```

Implemente comandos POST explícitos:

- `/governance/submit`;
- `/governance/return-for-changes`;
- `/governance/approve`;
- `/governance/reject`;
- `/publication/activate`;
- `/publication/pause`;
- `/publication/resume`;
- `/publication/expire`;
- `/publication/revoke`.

Implemente consultas:

- `GET /governance` — estado, revisão submetida/aprovada, decisão e ações potencialmente disponíveis;
- `GET /governance/events` — histórico com cursor opaco e ordem determinística.

Todo comando recebe `expectedVersion`. Os comandos relativos à avaliação recebem também `revisionNumber` ou `submissionId`, conforme o modelo escolhido, mas devem eliminar ambiguidade e impedir decisão sobre submissão antiga.

`availableActions` é conveniência de apresentação calculada pelo estado, datas e disponibilidade dos pais. Não representa autorização final: a API continua validando authority, sujeito, versão, revisão e estado no comando.

Consultas e comandos são sempre escopados pela hierarquia completa. Cross-scope retorna 404 sem revelar existência.

Não criar endpoint público nesta etapa.

## 9. Respostas e erros

Preserve o envelope de erro e correlation ID. Adicione no mínimo:

- `INVALID_GOVERNANCE_TRANSITION` — 422;
- `REVISION_NOT_CURRENT` — 409;
- `SUBMISSION_ALREADY_OPEN` — 409;
- `STALE_GOVERNANCE_VERSION` ou o `CONCURRENT_MODIFICATION` já padronizado — 409, escolhendo um padrão único documentado;
- `SEGREGATION_OF_DUTIES_VIOLATION` — 403;
- `JUSTIFICATION_REQUIRED` — 400;
- `NOT_EFFECTIVELY_PUBLISHABLE` — 422;
- `PUBLICATION_WINDOW_NOT_OPEN` — 422;
- `PUBLICATION_NOT_EXPIRED` — 422.

Não devolver stack, SQL, nome de constraint, credencial ou informação cross-scope.

## 10. Frontend administrativo

Após aplicar as quatro correções herdadas, acrescente ao detalhe da oportunidade:

- status atual em português claro;
- revisão corrente, submetida e aprovada, quando existirem;
- linha do tempo somente leitura;
- painel de ações de governança;
- diálogo ou campo de justificativa nas ações que a exigem;
- explicação clara quando uma ação estiver indisponível por estado, janela ou hierarquia;
- avisos de segregação de responsabilidades;
- indicação explícita de que PUBLISHED nesta etapa é autorização interna e ainda não criou link;
- estados loading, sucesso, 401, 403, 404, 409, 422 e erro inesperado;
- atualização do detalhe e histórico após cada comando aceito.

Não ocultar toda a governança apenas por inferência local de authority. O backend é a autoridade. Sem IdP, a interface deve continuar mostrando o bloqueio honesto já estabelecido, sem fixtures ou sessão falsa.

## 11. Documentação

Crie:

- `SEGSENSE_GOV_001.md` — papéis, segregação, estados, transições, invariantes e significado de PUBLISHED;
- `SEGSENSE_DAT_003.md` — V5, tabelas, constraints, índices e rollback conceitual;
- `SEGSENSE_API_004.md` — comandos, consultas, schemas, authorities e erros;
- `SEGSENSE_REV_006.md` — auditoria da etapa, correções herdadas, evidências, riscos e SAT-01 a SAT-10;
- `SEGSENSE_PRM_006.md` — cópia integral deste prompt.

Atualize DOM_002, SEC_001, ARQ_002, PLN_001, READMEs e índice documental somente onde forem afetados. Registre versões e histórico. Marque PRM_005 como aprovado com as quatro ressalvas transportadas e resolvidas nesta etapa.

Não reescreva documentos normativos externos.

## 12. Testes obrigatórios

Cubra, no mínimo:

- as quatro correções herdadas de UI;
- todas as transições válidas;
- todas as transições inválidas relevantes;
- criação de revisão proibida fora de DRAFT;
- submissão vinculada à revisão corrente;
- decisão sobre revisão ou submissão antiga rejeitada;
- uma submissão aberta e uma decisão por submissão;
- segregação entre autor/submissor, revisor e ativador;
- authorities corretas e combinações insuficientes retornando 403;
- justificativa obrigatória, tamanho, HTML/script e orientação de privacidade;
- concorrência otimista sem evento órfão;
- transação atômica entre estado atual e evento;
- hierarquia ativa/inativa e cross-scope;
- janelas `validFrom`/`validUntil`, incluindo bordas em UTC;
- ativação e retomada impedidas fora da janela;
- expiração somente após `validUntil`;
- `effectivelyPublished=false` após suspensão de pai, sem mutação silenciosa;
- trilha histórica completa, ordenada, isolada e paginada;
- correlation ID persistido no evento e devolvido no HTTP;
- constraints e FKs PostgreSQL por SQL direto;
- migrations V1–V5 em banco vazio e V5 incremental;
- 401 real sem IdP e sucessos somente com Spring Security test;
- métodos e rotas não previstos negados;
- regressões backend, frontend e ArchUnit.

Use `Clock` injetável; não torne os testes dependentes do relógio real.

## 13. Validação final

Execute:

- backend `mvnw.cmd verify`;
- frontend `npm ci`, lint, testes e build;
- validação do Compose sem remover volume;
- aplicação incremental da V5 no PostgreSQL existente;
- inspeção do histórico Flyway;
- endpoints públicos reais já existentes;
- chamada real anônima às novas rotas comprovando 401 e correlação;
- sucessos autenticados via Testcontainers e Spring Security test.

Inspecione segredos, PII, logs, erros, arquivos gerados, índice, alterações fora de `segsense/` e estado Git. Não derrube definitivamente o ambiente que já estava disponível; se precisar reiniciar processos para validar, devolva backend e frontend funcionais nas portas documentadas.

## 14. Critérios de aceite

- quatro ressalvas do PRM_005 resolvidas e testadas;
- revisão exata submetida, decidida e ativada;
- segregação real por sujeito e authority;
- transições e concorrência protegidas no domínio e na persistência;
- trilha append-only atômica e correlacionada;
- PUBLISHED definido como autorização interna, sem link fictício;
- janelas e disponibilidade efetiva respeitadas;
- nenhuma autenticação, integração ou decisão securitária inventada;
- migrations, testes, builds e documentação aprovados;
- nenhum outro produto ou configuração Git alterado.

## 15. Devolutiva obrigatória

Apresente:

1. resolução individual das quatro ressalvas herdadas;
2. arquivos criados e alterados;
3. modelo de governança e segregação;
4. máquina de estados e invariantes;
5. persistência V5 e integridade SQL;
6. endpoints, authorities e matriz de exposição;
7. interface e estados tratados;
8. testes, builds, Flyway e evidências HTTP;
9. SAT-01 a SAT-10;
10. inspeção de segurança, privacidade e segredos;
11. Git e alterações externas;
12. ausências confirmadas: link, ContextInstance, Spider, Icatu, mock, IA, produto, preço, cobertura, elegibilidade, consentimento e autenticação fictícia.

Não faça commit, push ou deploy.
