# Gate 011 — V7b Worker PDF real (homolog)

- **Resultado:** **PASS**
- **Quando:** `2026-08-04T14:06Z` (UTC)
- **API:** `https://api.homolog.qmind.com.br`
- **Evidência JSON:** `WORKER_PDF_V7b_evidence.json` (sem senhas/tokens/URLs assinadas)
- **Imagem:** `qmind-api:mvp-fullstack-v0` (API + worker)
- **Migração:** `20260804_0006` (lease/attempts/next_run_at/output_ref)

## O que foi entregue

| Item | Detalhe |
|---|---|
| Serviço Compose | `worker` → `python -m app.worker` (não mais `sleep infinity`) |
| Recursos | `mem_limit=384m`, `cpus=0.50` |
| Healthcheck | `GET http://127.0.0.1:8010/health` |
| Estados | `queued → running → succeeded \| failed` (+ retry → `queued`) |
| Claim | `FOR UPDATE SKIP LOCKED` (admin DSN) |
| Retry | limite (`max_attempts=5`) + backoff progressivo |
| Reinício | lease recovery de jobs `running` abandonados |
| PDF | ReportLab fora do request HTTP |
| S3 | `org/{org_id}/reports/{report_id}/v{version}.pdf` (SSE-S3) |
| Download | `GET /api/v1/reports/{id}/export-pdf/download-url` com membership + RLS |
| UI | ReportPanel: enfileira, faz poll do job, botão Baixar PDF |
| Logs | `job_id` + `correlation_id`; audit sem URL assinada / Bearer |

## Gate de aprovação (homolog)

| Check | Resultado |
|---|---|
| Relatório publicado | PASS |
| Enqueue idempotente | PASS |
| Worker processa → `succeeded` | PASS (`bytes=2283`) |
| Storage key por org/report/versão | PASS |
| Download PDF válido (`%PDF`, HTTP 200) | PASS |
| Org B → 404 sem leak | PASS |
| Audit sem tokens/URLs assinadas | PASS (`secret_hits=0`) |
| Restart worker → healthy | PASS (verificado no host) |

## Scripts / testes

- Homolog E2E: `infra/scripts/worker-pdf-e2e-homolog.ps1`
- Unit/integration: `backend/tests/test_worker_pdf.py` (sucesso, retry→fail, lease recover, cross-org)

## Próximo

Observação operacional e financeira de **sete dias** (custo/CPU/disco/backup/alarmes).
