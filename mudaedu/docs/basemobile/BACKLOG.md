# Backlog — Esteira Base Mobile (eSIM) → Mesa de Inovação Preditiva

Módulo **desacoplado** em `LeAction_SysF/integrations/basemobile/`.  
Não altera fluxos pedagógicos, Kanban legado nem **integração Action Hub**.

Relatório completo: [IMPLEMENTACAO.md](./IMPLEMENTACAO.md)

## Epics

### E1 — Ingestão de telemetria ✅
- [x] Webhook `POST /api/webhooks/basemobile`
- [x] Tabelas `basemobile_eventos` + `basemobile_mesa_backlog`
- [x] Secret opcional `BASEMOBILE_WEBHOOK_SECRET` + header `X-BaseMobile-Token`
- [x] Migration `007_basemobile_telemetry.sql`

### E2 — Orquestração IA ✅
- [x] Agente `telemetry_agent.analisar_anomalia_telemetria` (Bedrock / fallback)
- [x] Saída JSON: `hipotese`, `subtasks`, `bloco_escolhido`
- [x] Fallback blindado: 1º bloco da lista restrita se Bedrock falhar

### E3 — Backlog separado → Mesa ✅
- [x] Persistência `origem=telemetria`, `is_alerta=true`
- [x] Materialização em `inov_agenda_notas` (`Telemetria_BaseMobile`)
- [x] API `GET /api/basemobile/mesa-backlog?id_clie=&id_matu=`

### E4 — UI Mesa Org ✅
- [x] Post-its `.post-it-telemetria` (pulse, borda vermelha, 🚨)
- [x] CTA "Transformar em Sprint" no rodapé do card
- [x] Painel lateral “Backlog Preditivo (eSIM)”
- [x] Marcar item como `consumido` ao lapidar/incubar

### E5 — Hardening produção ⏳
- [ ] Deploy backend + migrations 007 + 008
- [x] CloudWatch / dead-letter Bedrock (`observability.py`)
- [x] Rate limit no webhook (`rate_limit.py`, HTTP 429)

### E6 — Catálogo LeAction ✅
- [x] `event_catalog.py` — `EVENT_LEACTION_CATALOG` (3 códigos)
- [x] `codigo_evento_padrao` obrigatório em `schemas.py`
- [x] Vínculo dimensão / domínio / blocos restritos

### E7 — Persistência CTDI para Kanban ✅
- [x] Colunas `dominio_associado`, `bloco_associado` (migration 008)
- [x] `repository.py` — insert/update + meta no post-it Mesa
- [x] Serialização API Mesa: `dominio_associado`, `bloco_associado`, `codigo_evento_padrao`

### E8 — QA / Simulador ✅
- [x] `scripts/simulador_esim.py` v2
- [x] `--codigo-evento`, `--listar-codigos`, cenários por código

## Contrato do webhook (atual)

```json
POST /api/webhooks/basemobile
{
  "cliente_id": 1,
  "codigo_evento_padrao": "QDA_ACESSO_PEDAG",
  "grupo_acesso": "Pedagógico",
  "dominio_acessado": "lms.escola.com.br",
  "titulo_alerta": "Queda crítica de acesso pedagógico ao LMS/LXP",
  "descricao_evento": "Queda de 40% no tráfego eSIM… Portal de Integração, AVA/LMS, Programas Híbridos.",
  "trafego_mb_7dias": 45,
  "status_anomalia": "queda_critica",
  "variacao_percentual": -40
}
```

**Obrigatórios:** `cliente_id`, `codigo_evento_padrao`, `grupo_acesso`, `dominio_acessado`, `status_anomalia`

## Arquitetura

```
Base Mobile (eSIM)
       │ POST webhook + codigo_evento_padrao
       ▼
schemas.py → event_catalog.py (catálogo fechado)
       ▼
service.py → telemetry_agent.py (Bedrock + bloco_escolhido)
       ▼
repository.py → basemobile_* + inov_agenda_notas
       │ dominio_associado + bloco_associado
       ▼
Mesa Org / Kanban
```
