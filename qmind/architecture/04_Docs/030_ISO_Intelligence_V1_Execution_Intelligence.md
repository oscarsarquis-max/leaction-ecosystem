# ISO Intelligence V1 — Execution Intelligence (ISOI-009)

- Status: **Implementado / baseline**
- Data: 2026-08-26
- Mecanismo OI: `execution-intelligence-rules-v1`
- Pin OI: **`34ead2e`** (`feat(oi): add execution intelligence v1`)
- Pin de entrega (Core): este commit — `feat(qmind): integrate execution intelligence`

## Fronteira

O Core continua dono de casos, planos, ações, impedimentos, dependências,
evidências, medições e observações. Ele produz um snapshot factual versionado,
com referências opacas e fingerprint determinístico. O QMind OI recebe somente
esse contrato, interpreta os fatos por regras determinísticas e devolve sinais;
não lê o banco do Core e não altera lifecycle, eficácia ou dados operacionais.

```text
Core facts ── ExecutionIntelligenceInput V1 ──► QMind OI
    ▲                                           │
    │                                           ▼
history/UI ◄── ExecutionIntelligenceResult V1 ──┘
 (append-only, RLS, stale)
```

## Fluxo e garantias

1. O Core autoriza a leitura/execução e captura todos os fatos em consultas em lote.
2. O fingerprint SHA-256 exclui apenas `request_id`, `correlation_id` e `captured_at`.
3. A transação de leitura é encerrada antes da chamada HTTP.
4. O Core valida schema, ecos, mecanismo e toda `supporting_fact_ref`.
5. O contexto é recapturado; mudança concorrente retorna
   `409 execution_context_changed` sem persistência.
6. Somente um resultado íntegro é inserido no histórico imutável. Retentativas
   podem usar `Idempotency-Key`; a chave bruta nunca é armazenada. A identidade
   da requisição inclui o fingerprint do snapshot: mesma chave com fatos
   diferentes retorna `409 idempotency_conflict`.

## Registro factual R1

Sinais citam somente referências de campo do registro canônico compartilhado
entre Core e OI. Referências de entidade são apenas prefixos internos.

- `case.status`
- `execution.plan.status`
- `execution.action:action:1:status`
- `execution.action:action:1:is_terminal`
- `execution.action:action:1:claims_execution`
- `measurement.indicator:indicator:1:baseline_status`
- `measurement.indicator:indicator:1:target_posture`
- `outcome.latest.result_direction`

O contrato de ação informa `is_terminal` segundo o lifecycle do Core
(`done`, `cancelled`, `ineffective_closed`) e `claims_execution` somente para
`done`/`ineffective_closed`. Estados `implemented` e `validated` ainda não são
terminais. O contrato de medição informa `baseline_status` como `missing`,
`recorded` ou `unavailable_justified`; baseline formalmente indisponível e
justificada não gera lacuna.

## APIs

- `POST /api/v1/organizations/current/improvement-cases/{case_id}/execution-intelligence/runs`
- `GET /api/v1/organizations/current/improvement-cases/{case_id}/execution-intelligence/runs`
- `GET /api/v1/organizations/current/improvement-cases/{case_id}/execution-intelligence/runs/{run_id}`
- `GET /api/v1/organizations/current/improvement-cases/{case_id}/execution-intelligence/latest`

Leitores do caso podem consultar o histórico. Execução é permitida para
`org_admin`, `quality_manager`, `process_owner`, `consultant_auditor` e
`platform_admin`. A tela de evolução consulta o resultado completo e o
histórico, traduz fatos e estados para linguagem humana, preserva a última
leitura quando uma atualização fica indisponível e sempre declara que meta
numérica não equivale a eficácia.

## Não objetivos

- Nenhum LLM.
- Nenhuma regra OI reimplementada no Core.
- Nenhuma automação de eficácia, encerramento ou transição de lifecycle.
- Nenhum import do pacote `qmind_oi`; compatibilidade é verificada contra os
  JSON Schemas públicos copiados para `backend/contracts/oi/v1`.
