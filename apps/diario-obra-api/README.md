# Diário de Obra API (RDO — Gemba)

Micro-serviço satélite **mobile-first** para Relatório Diário de Obra.  
100% desacoplado do Chamelleon (:5010), Gateway (:4001) e Marketplace (:4012).

| Serviço | Porta | Base de dados |
|---------|-------|----------------|
| Gateway | 4001 | — |
| Marketplace | 4012 | — |
| Chamelleon | 5010 | — |
| **Diário de Obra** | **6010** | **`diario-obra`** (PostgreSQL dedicado) |

## Setup

```powershell
cd C:\Projetos\apps\diario-obra-api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Na primeira execução: cria a base `diario-obra` (se não existir) e todas as tabelas via `db.create_all()`.

## Modelos (Gemba)

- `ProjectSite` — canteiro de obra
- `DailyLog` — RDO principal (clima manhã/tarde, status, assinatura)
- `Workforce` — mão de obra (própria / terceirizada)
- `EquipmentStatus` — maquinário
- `ExecutedService` — avanço físico
- `Occurrence` — eventos críticos / segurança / fotos
- `ProjectDirectives` — integração Chamelleon (webhook)

## API RDO

```http
POST /api/rdo/logs
GET  /api/rdo/logs/<project_id>
GET  /health
```

### Exemplo — criar rascunho

```http
POST http://localhost:6010/api/rdo/logs
Content-Type: application/json

{
  "project_id": "<uuid-do-canteiro>",
  "date": "2026-07-07",
  "weather_morning": "SOL",
  "weather_afternoon": "CHUVA",
  "technical_comments": "Fiscalização municipal às 14h",
  "workforce": [
    {"role": "Pedreiro", "headcount": 8, "type": "Propria"},
    {"role": "Eletricista", "headcount": 3, "type": "Terceirizada", "company_name": "EletroXYZ"}
  ],
  "equipment_statuses": [
    {"equipment_name": "Betoneira", "status": "Operando"}
  ],
  "executed_services": [
    {"description": "Concretagem de pilares", "location_on_site": "Bloco A, 2º pavimento"}
  ],
  "occurrences": [
    {"type": "Falta_Material", "description": "Atraso na entrega de aço", "safety_ppe_notes": "EPIs OK"}
  ]
}
```

## Integração Chamelleon (desacoplada)

```http
POST /api/integration/framework-directives
X-Integration-Key: <INTEGRATION_API_KEY>
```
