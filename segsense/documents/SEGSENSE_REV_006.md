# SEGSENSE_REV_006 — Revisão de aderência do PRM_006

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_REV_006 |
| Título | Revisão de aderência do PRM_006 |
| Categoria | REV — revisão |
| Versão | 1.1 |
| Status | Concluída nesta execução |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_PRM_006; SEGSENSE_PRM_006_COR_001; SEGSENSE_GOV_001; SEGSENSE_DAT_003; SEGSENSE_API_004; SEGSENSE_REV_005 |
| Escopo revisado | Correções de UI herdadas do PRM_005; governança editorial; V5+V6; submissão imutável; PUBLISHED interno; sem IdP, link, Spider, Icatu ou IA |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Revisão da etapa PRM_006. |
| 1.1 | 04/09/2026 | Achado de integridade SQL, corretivo V6 e provas. |

## 1. Correções herdadas do PRM_005

O PRM_005 foi **aprovado com ressalvas**. As quatro pendências de interface foram resolvidas **antes** do novo escopo, sem alterar o contrato válido da oportunidade:

1. **required** — cada campo contextual tem checkbox para marcar e desmarcar obrigatoriedade.
2. **Remover campo** — botão por campo; a ordem enviada ao backend permanece contínua (reindexação pelo array).
3. **validFrom / validUntil** — `datetime-local` interpretado explicitamente como UTC (`…000Z`), com mensagem “A validade final (UTC) deve ser posterior ao início.”
4. **Reload após revisão** — `reloadDetail()` busca detalhe e histórico após criar revisão; a revisão N+1 aparece sem refresh manual.

Testes: `OpportunityAdmin.test.tsx`.

## 2. SAT-01 a SAT-10

| ID | Situação | Comentário |
|---|---|---|
| SAT-01 | PARCIAL | Identidade local `SEGSENSE`; sem registro na Spider |
| SAT-02 | PARCIAL | Manifesto DRAFT |
| SAT-03 | NÃO IMPLEMENTADO | Sem Satellite Contract |
| SAT-04 | PARCIAL | BFF; catálogo, oportunidade e governança locais; sem sessão de usuário nem client Spider |
| SAT-05 | PARCIAL | Correlação local em HTTP e persistida no evento de ciclo de vida |
| SAT-06 | NÃO APLICÁVEL NESTA ETAPA | Sem submissão de objetivo |
| SAT-07 | NÃO APLICÁVEL NESTA ETAPA | Sem execução para projetar |
| SAT-08 | PARCIAL | Deny-by-default, SOD por `subjectId` e authorities distintas; **sem** IdP |
| SAT-09 | ATENDIDO | Sem knowledge de routes/adapters |
| SAT-10 | ATENDIDO | Autorização interna local; nenhum envio à Spider |

O satélite permanece **não certificável**. SAT-08 não está atendido integralmente.

## 3. Evidências desta execução

- Domínio: transições, SOD, janela UTC, revisão só em DRAFT (`OpportunityGovernanceTest`).
- HTTP/Testcontainers: sujeitos `author` / `reviewer` / `activator`, 401 anônimo, 403 de authority, constraints SQL, cursor isolado, pai suspenso sem mutar `PUBLISHED` (`OpportunityGovernanceIT`).
- Flyway V1–V6 em banco vazio; V6 incremental no volume local (sem `-v`).
- Frontend: quatro ressalvas + painel de governança, 401 honesto, justificativa e 422.
- ArchUnit inalterado em espírito: domínio sem Spring/JPA/HTTP; sem clients Spider/Icatu.

## 4. Achado do corretivo único (SEGSENSE_PRM_006_COR_001)

A governança HTTP funcionava, mas a V5 não fechava no PostgreSQL as identidades que documentava:

1. `open_submission_id` referenciava só `opportunity_submission(id)` — SQL podia ligar a oportunidade A à submissão de B.
2. FKs independentes em `opportunity_decision` — a decisão podia citar a submissão A e a oportunidade/revisão B.
3. A aplicação fazia `UPDATE opportunity_submission.status` de `OPEN` para `DECIDED`, contradizendo a trilha imutável. O índice parcial `opportunity_open_submission_unique` dependia desse `status` mutável e bloquearia ressubmissão se as linhas permanecessem `OPEN`.

V1–V5 não foram reescritas. A V6 aborta se o volume já estiver inconsistente; caso contrário adiciona a chave candidata `(id, opportunity_id, revision_number)`, FKs compostas nomeadas e remove o índice parcial. A coluna `status` foi preservada e deprecada. A aplicação passou a inserir a submissão uma vez (`EntityManager.persist`) e a localizar a aberta pelo ponteiro do aggregate.

Provas em `OpportunityGovernanceIT.sqlRejectsCrossIdentitiesAndKeepsFirstSubmissionImmutable` e no teste de concorrência sem órfãos. Nenhum arquivo fora de `segsense/` foi alterado neste corretivo. `.cursor/rules/ecosystem-focus.mdc` havia sido modificado na execução original do PRM_006; este corretivo não o restaura, apaga nem edita.

## 5. Riscos e débitos

- Sem IdP, a UI administrativa real permanece 401; sucessos só em teste.
- `availableActions` pode listar comando que o sujeito corrente não pode executar (SOD/authority); o backend recusa.
- Não há scheduler: `validFrom` futuro impede ativar até comando posterior.
- `PUBLISHED` pode ser lido como “já no ar”; a UI e `publishedMeans` deixam explícito que não há link.

## 6. Conclusão

O PRM_006, após o corretivo único, adere ao recorte: ressalvas de UI resolvidas, revisão exata submetida/decidida/ativada, identidades SQL compostas, submissão/decisão/evento append-only e `PUBLISHED` como autorização interna. Nenhuma autenticação fictícia, link, ContextInstance, Spider, Icatu, IA, produto, preço, cobertura, elegibilidade ou consentimento foi introduzido.
