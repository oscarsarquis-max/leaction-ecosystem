# SEGSENSE_DAT_003 — Persistência da governança (V5 + V6)

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_DAT_003 |
| Título | Flyway V5/V6, identidade composta e trilha append-only |
| Categoria | DAT — dados |
| Versão | 1.1 |
| Status | Vigente nesta etapa |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_DAT_002; SEGSENSE_GOV_001; Flyway V1–V6 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | V5: status ampliado, submissão, decisão e eventos. |
| 1.1 | 04/09/2026 | V6: FKs compostas de identidade; submissão imutável; `status` depreçado. |

## 1. Política

V1–V5 não foram reescritas. `ddl-auto=none`. Sem `CASCADE`, trigger de negócio ou deleção física. FKs usam `NO ACTION`. O estado corrente permanece no aggregate `contextual_opportunity` e é atualizado na mesma transação da trilha append-only. O event store **não** é a fonte exclusiva nesta etapa. Não há correção automática de dados.

Arquivos:

- `database/migrations/V5__create_opportunity_governance.sql` (já aplicada; imutável)
- `database/migrations/V6__harden_opportunity_governance_integrity.sql`

A V6 é preventiva e incremental. Se a pré-validação encontrar inconsistência, o `DO` inicial aborta com `RAISE EXCEPTION` **antes** de qualquer `ALTER`/`DROP`, sem mutação parcial.

## 2. Aggregate

`contextual_opportunity.status` admite `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, `PAUSED`, `REVOKED`, `EXPIRED` (`opportunity_status_chk`).

Colunas de governança (V5):

| Coluna | Uso |
|---|---|
| `submitted_revision` | revisão da submissão aberta, ou última submetida após aprovação |
| `approved_revision` | revisão exatamente aprovada |
| `open_submission_id` | ponteiro da submissão atualmente aberta; `NULL` quando não há submissão em aberto |
| `submitted_by` | `subjectId` do submissor |
| `approved_by` | `subjectId` do aprovador |

FKs compostas `(id, submitted_revision)` e `(id, approved_revision)` apontam para `contextual_opportunity_revision (opportunity_id, revision_number)`. Nulas são permitidas.

A inserção da submissão precede o preenchimento de `open_submission_id` (FK circular resolvida na mesma transação).

### Ponteiro aberto (V6)

`opportunity_open_submission_identity_fk`:

```text
contextual_opportunity (open_submission_id, id, submitted_revision)
  → opportunity_submission (id, opportunity_id, revision_number)
```

`MATCH SIMPLE` (padrão): se `open_submission_id` é nulo, a FK não é exigida — após decidir, o ponteiro é limpo e `submitted_revision` pode permanecer. `opportunity_open_submission_identity_chk` impede ponteiro aberto sem revisão.

Índice parcial `opportunity_open_submission_lookup_idx` em `open_submission_id` (não nulo) substitui o papel de busca do índice único parcial da V5. A unicidade de “uma aberta agora” é o próprio ponteiro do aggregate (uma coluna por linha), não um `UPDATE` de `status`.

A FK simples `opportunity_open_submission_fk` da V5 foi removida.

## 3. Tabelas append-only

A aplicação **não** executa `UPDATE` nem `DELETE` em submissão, decisão ou evento. A única mutação permitida é o estado corrente do aggregate na mesma transação das novas linhas.

### `opportunity_submission`

Fato imutável: revisão, autor, instante UTC, correlation ID. Novas linhas nascem com `status = 'OPEN'` por compatibilidade com o CHECK da V5.

A coluna `status` (`OPEN`/`DECIDED`) é **histórica e deprecada**. Não é atualizada. “Aberta agora” deriva de `contextual_opportunity.open_submission_id` **e** da ausência de `opportunity_decision` para esse `id`.

Chave candidata `opportunity_submission_identity_unique (id, opportunity_id, revision_number)` — necessária para as FKs compostas. A PK continua sendo `id`. FK composta para a revisão permanece a da V5.

O índice único parcial `opportunity_open_submission_unique` (`WHERE status = 'OPEN'`) foi **removido** na V6: com linhas imutáveis que permanecem `OPEN`, ele bloquearia a ressubmissão após retorno para alterações.

### `opportunity_decision`

Fato distinto que encerra uma submissão. Uma decisão por `submission_id` (`opportunity_decision_submission_unique`, V5).

`opportunity_decision_submission_identity_fk`:

```text
opportunity_decision (submission_id, opportunity_id, revision_number)
  → opportunity_submission (id, opportunity_id, revision_number)
```

As FKs independentes da V5 (`opportunity_decision_submission_fk` e `opportunity_decision_revision_fk`) foram substituídas. A revisão continua referenciada indiretamente pela identidade da submissão (e pela FK da própria submissão à revisão).

Outcomes `APPROVED`, `RETURNED`, `REJECTED`. `APPROVED` exige `justification IS NULL`. `RETURNED`/`REJECTED` exigem texto de 10 a 500 caracteres.

### `opportunity_lifecycle_event`

UUID próprio, oportunidade, revisão, tipo, status anterior/novo, `actor_subject_id`, `occurred_at`, justificativa opcional, `correlation_id`. Índice de cursor `(opportunity_id, occurred_at, id)`.

Tipos: `SUBMITTED`, `RETURNED`, `APPROVED`, `REJECTED`, `ACTIVATED`, `PAUSED`, `RESUMED`, `EXPIRED`, `REVOKED`.

## 4. Concorrência

`version` do aggregate permanece o lock otimista. Falha de versão aborta a transação: não permanece decisão nem evento órfão. Conflito HTTP usa o código já padronizado `CONCURRENT_MODIFICATION` (não se adicionou `STALE_GOVERNANCE_VERSION`).

## 5. Rollback conceitual

Não há script destrutivo automático nem reparo de dados. Rollback conceitual, nesta ordem:

1. remover `opportunity_open_submission_identity_fk` e `opportunity_open_submission_identity_chk`;
2. remover `opportunity_decision_submission_identity_fk` e `opportunity_submission_identity_unique`;
3. restaurar, se necessário, a FK simples e o índice parcial da V5 (somente em volume que ainda dependa desse contrato);
4. remover linhas de `opportunity_lifecycle_event`;
5. remover `opportunity_decision`;
6. anular `open_submission_id` e remover `opportunity_submission`;
7. remover colunas de governança de `contextual_opportunity`;
8. restaurar `opportunity_status_chk` somente `DRAFT`.

Só é seguro se nenhuma oportunidade tiver saído de `DRAFT`, ou após migração de dados explícita fora desta etapa.

## 6. Comprovação

- Banco vazio (Testcontainers): Flyway aplica V1–V6.
- Volume local existente: V6 incremental sobre V5, sem `docker compose down -v`.
- SQL direto: cruzamento de ponteiro e de identidade da decisão rejeitados; decisão coerente aceita; segunda decisão rejeitada; primeira submissão inalterada após decisão e ressubmissão.
