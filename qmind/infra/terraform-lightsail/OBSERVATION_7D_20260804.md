# Gate 011 — Observação operacional 7 dias (pós-liberação)

- **Status:** **ABERTA** (não bloqueante)
- **Início (UTC):** `2026-08-04` (baseline dia 0)
- **Encerramento previsto (UTC):** `2026-08-11`
- **Ambiente:** Lightsail homolog `qmind-homolog-app` / `us-east-2`
- **Hosts:** `app.homolog.qmind.com.br`, `api.homolog.qmind.com.br`

## Decisão de liberação

| Dimensão | Estado |
|---|---|
| Homologação funcional | **Aprovada** |
| Homologação técnica | **Aprovada** |
| Piloto controlado | **Autorizado** (em paralelo) |
| Observação 7 dias | **Monitoramento pós-liberação** (não bloqueia piloto) |
| Produção ampla | **Não autorizada** |

O fechamento definitivo do gate 011 ocorre ao completar os 7 dias **sem gatilho crítico aberto**, ou com dispensa formal documentada.

## Coleta automatizada diária

| Fonte | Script | Quando |
|---|---|---|
| Host (disco, memória, worker, jobs, CW metrics) | `infra/scripts/observe-homolog-host.sh` | Cron host `20 11 * * *` UTC |
| Operador/AWS (custo, LS metrics, health, HTTPS, alarmes, backup, triggers) | `infra/scripts/observe-homolog-daily.ps1` | Diário (máquina ops / CI) |

Artefatos: `infra/terraform-lightsail/observe/YYYY-MM-DD.json` + `INDEX.md`  
Métricas CW namespace `QMind/Homolog` (dimensão `Environment=homolog`):  
`WorkerHealthy`, `DiskUsedPercent`, `MemUsedPercent`, `JobQueuedCount`, `JobRunningCount`, `JobFailed24h`, `JobSucceeded24h`, `JobStuckRunning`, `JobAvgSuccessSeconds24h`, `BackupSuccess`.

### Itens registrados

1. Custo incremental com tag `Project=qmind` (MTD + projeção mensal)  
2. CPU / memória / disco (Lightsail + host/containers)  
3. Disponibilidade `/health` e `/ready`  
4. Estado do worker  
5. Falhas e tempo dos jobs PDF  
6. Backup diário (CW `BackupSuccess` + objeto S3)  
7. Alarmes AWS (CW + Lightsail)  
8. Validade HTTPS (dias até expirar)

## Gatilhos de interrupção do piloto

| Gatilho | Severidade | Detecção |
|---|---|---|
| Backup ausente ou restauração comprometida | **crítica** | CW/S3 automático; restore = processo |
| Isolamento entre organizações violado | **crítica** | processo / incidente |
| Exposição de segredo ou evidência | **crítica** | processo / incidente |
| Custo projetado QMind > **US$ 30/mês** | **crítica** | automático (Cost Explorer tag) |
| Disco > **80%** | **crítica** | automático |
| Indisponibilidade recorrente | **alta/crítica** | `/health`/`/ready` + alarmes |
| Jobs presos ou fila em crescimento contínuo | **crítica/alta** | `JobStuckRunning` / `JobQueuedCount>20` |

**Ação se interrupt recomendado:** pausar onboarding de novos usuários do piloto, preservar evidências, abrir incidente, não expandir produção.

## Escopo do piloto controlado (paralelo)

- Poucos usuários; organizações fictícias ou dados **não sensíveis**  
- Limite claro de evidências (volume/tamanho)  
- Sem conteúdo normativo sem licença; sem dados pessoais desnecessários  
- Canal único de incidentes  
- Domínio de acesso: **homolog** (`app.homolog.qmind.com.br`) — apex `qmind.com.br` não é produção

Ver também `architecture/04_Docs/013_Discovery_and_Pilot_Plan.md`.

## Baseline dia 0 (2026-08-04T14:19Z)

Gerado por:

```powershell
cd C:\Projetos\qmind
.\infra\scripts\observe-homolog-daily.ps1 -Baseline
```

Arquivo: `observe/BASELINE_2026-08-04.json`

| Sinal | Valor baseline |
|---|---|
| `/health` `/ready` app | OK (200) |
| Worker | healthy (`WorkerHealthy=1`) |
| Disco host | **9%** |
| Memória host | **~40%** |
| CPU Lightsail (max 24h) | **~56%** (pico); status check **0** |
| Jobs 24h | succeeded=3, failed=0, stuck=0, queued=0 |
| Backup | objeto `pgdump/qmind-20260804T124137Z.sql.enc` + `BackupSuccess=1` |
| HTTPS | ~89 dias até expirar (api/app) |
| Custo tag `Project=qmind` | MTD **US$ 0** (CE/tags com lag — reavaliar nos próximos dias) |
| Triggers / interrupt | **0 / false** |

Cron host: `20 11 * * *` → `/opt/qmind/bin/observe-homolog-host.sh`  
Coleta operador diária: `observe-homolog-daily.ps1` → `observe/YYYY-MM-DD.json` + `INDEX.md`
