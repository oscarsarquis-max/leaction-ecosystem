# Relatório de Implementação — Integração eSIM / Base Mobile → Framework LeAction

**Projeto:** PanelDX  
**Módulo:** `LeAction_SysF/integrations/basemobile/`  
**Última atualização:** junho/2026  
**Princípio arquitetural:** alto desacoplamento — backlog separado, **sem impacto na integração Action Hub**

---

## 1. Resumo executivo

Foi entregue uma **esteira preditiva completa** que recebe telemetria de chips inteligentes (eSIM) da Base Mobile, valida eventos contra um **catálogo fechado LeAction**, aciona a **IA Master Executiva (Bedrock/Claude)** com contexto CTDI restrito, persiste domínio/bloco associados para o **Kanban**, e materializa **alertas visuais** na Mesa de Inovação Organizacional.

**Teste local validado:** `scripts/simulador_esim.py` → HTTP **201**, `ia_processada: true`, `bloco_associado` e `dominio_associado` gravados (com `ia_fallback: true` quando Bedrock indisponível em dev).

---

## 2. Arquitetura

```
Base Mobile (eSIM / operadora)
        │  POST /api/webhooks/basemobile
        ▼
routes.py  →  service.processar_webhook_basemobile
        │
        ├─► schemas.py          validação + codigo_evento_padrao
        ├─► event_catalog.py    EVENT_LEACTION_CATALOG (catálogo fechado)
        ├─► repository.py       eventos + backlog + post-it Mesa
        └─► telemetry_agent.py  Bedrock Claude + fallback blindado
                │
                ▼
        basemobile_eventos ──► basemobile_mesa_backlog ──► inov_agenda_notas
                │                      │
                dominio_associado      bloco_associado  →  Kanban / Mesa Org
```

**Isolamento Action Hub:** rotas `/api/hub/*`, `HUB_JWT_SECRET` e `hub-checkout.js` **não foram alterados**.

---

## 3. Inventário de arquivos

### Backend — módulo Base Mobile (`integrations/basemobile/`)

| Arquivo | Responsabilidade |
|---------|------------------|
| `__init__.py` | Doc do pacote + nota de isolamento Action Hub |
| `event_catalog.py` | **Catálogo fechado** `EVENT_LEACTION_CATALOG` (3 códigos) |
| `schemas.py` | Validação payload + `LeactionEventBinding` |
| `routes.py` | Webhook + API backlog + `register_basemobile_routes()` |
| `service.py` | Orquestração webhook → catálogo → IA → persistência |
| `telemetry_agent.py` | Prompt LeAction restrito + `bloco_escolhido` + fallback |
| `repository.py` | DDL, inserts, `dominio_associado` / `bloco_associado` |

### Outros backend

| Arquivo | Alteração |
|---------|-----------|
| `app.py` | Registro `register_basemobile_routes(app)` |
| `routes/inovador_routes.py` | `_mesa_org_serializar_nota()` expõe domínio/bloco/código |
| `ai_engine/agents/assessment_master_agent.py` | Ponte `analisar_telemetria_basemobile()` |

### Frontend

| Arquivo | Alteração |
|---------|-----------|
| `views/mesa-inovacao.ejs` | Templates post-it manual vs telemetria |
| `public/js/mesa-inovacao.js` | Cards `.post-it-telemetria` + CTA sprint |
| `public/css/mesa-inovacao.css` | Estilo emergência + animação pulse |
| `server.js` | Cache bust JS v8 / CSS v4 |

### Dados & QA

| Arquivo | Função |
|---------|--------|
| `migrations/007_basemobile_telemetry.sql` | Tabelas base |
| `migrations/008_basemobile_dominio_bloco.sql` | Colunas domínio/bloco CTDI |
| `scripts/simulador_esim.py` | Simulador QA v2 (catálogo LeAction) |
| `docs/basemobile/BACKLOG.md` | Backlog de produto |
| `.env.example` | `BASEMOBILE_WEBHOOK_SECRET`, `BASEMOBILE_MATERIALIZAR_MESA` |

---

## 4. Catálogo LeAction (`EVENT_LEACTION_CATALOG`)

| Código | Dimensão | Domínio | Blocos candidatos restritos |
|--------|----------|---------|----------------------------|
| `QDA_ACESSO_PEDAG` | Aprendizagem em Ação (LA) | Plataformas Digitais (dp) | Portal de Integração dos Aprendizes, Ambientes AVA/LMS, Programas Híbridos |
| `GARGALO_ADMN_SEC` | Arquitetura Digital (DA) | Governança Digital (dg) | Segurança e Redundância, Identidade e Autenticação, Privacidade |
| `LENTIDAO_TI_SIST` | Arquitetura Digital (DA) | Plataformas Digitais (dp) | Conectividade e Nuvem, Mapa de Tecnologia, Interoperabilidade |

Somente códigos registrados no catálogo são aceitos (`codigo_evento_padrao` **obrigatório**).

---

## 5. Contrato do webhook (unificado)

**Endpoint:** `POST /api/webhooks/basemobile`  
**Porta dev:** `5002`

### Campos obrigatórios

- `cliente_id`
- `codigo_evento_padrao` — ex: `QDA_ACESSO_PEDAG`
- `grupo_acesso`
- `dominio_acessado`
- `status_anomalia`

### Campos recomendados / opcionais

- `titulo_alerta`, `descricao_evento` (auto-gerados se omitidos)
- `trafego_mb_7dias`, `variacao_percentual`

### Exemplo (cenário pedagógico)

```json
{
  "cliente_id": 1,
  "codigo_evento_padrao": "QDA_ACESSO_PEDAG",
  "grupo_acesso": "Pedagógico",
  "dominio_acessado": "lms.escola.com.br",
  "titulo_alerta": "Queda crítica de acesso pedagógico ao LMS/LXP",
  "descricao_evento": "Queda de 40% no tráfego eSIM dos docentes… Portal de Integração, AVA/LMS, Programas Híbridos.",
  "trafego_mb_7dias": 45,
  "status_anomalia": "queda_critica",
  "variacao_percentual": -40
}
```

### Resposta esperada (201)

```json
{
  "status": "success",
  "ia_processada": true,
  "codigo_evento_padrao": "QDA_ACESSO_PEDAG",
  "dimensao_fixada": "Aprendizagem em Ação (LA)",
  "dominio_fixado": "Plataformas Digitais (dp)",
  "dominio_associado": "Plataformas Digitais (dp)",
  "bloco_escolhido": "Portal de Integração dos Aprendizes",
  "bloco_associado": "Portal de Integração dos Aprendizes",
  "hipotese": "...",
  "subtasks": ["...", "...", "..."],
  "id_evento": 1,
  "id_item_backlog": 1,
  "id_nota_mesa": 1,
  "ia_fallback": false
}
```

---

## 6. Orquestração IA (Bedrock / Claude)

### Prompt restrito (telemetry_agent.py)

A IA Master recebe:
- `codigo_evento`, `dimensao_fixada`, `dominio_fixado`
- `descricao_evento` técnica
- Lista fechada `blocos_candidatos_restritos`

**Saída JSON obrigatória:** `hipotese`, `subtasks`, `bloco_escolhido`

### Fallback blindado

Se Bedrock falhar (`ia_fallback: true`):
- Hipótese gerada localmente com contexto LeAction
- **`bloco_escolhido` = primeiro bloco da lista restrita** (nunca fica sem bloco)
- Resposta fora da lista é corrigida por `_resolver_bloco_escolhido()`

---

## 7. Persistência (banco de dados)

### Tabelas

**`basemobile_eventos`** — log bruto + vínculo CTDI  
Colunas-chave: `dominio_associado`, `bloco_associado`, `payload_bruto`

**`basemobile_mesa_backlog`** — backlog preditivo separado  
Flags: `origem='telemetria'`, `is_alerta=true`, `status='pendente'`

**`inov_agenda_notas`** — post-it Mesa Org (`tipo_observacao='Telemetria_BaseMobile'`)

### Migrations

| Arquivo | Conteúdo |
|---------|----------|
| `007_basemobile_telemetry.sql` | CREATE tabelas base + índices |
| `008_basemobile_dominio_bloco.sql` | ALTER `dominio_associado`, `bloco_associado` |

Schema também auto-aplicado via `ensure_basemobile_schema()` no primeiro webhook.

### Fluxo de gravação

1. `inserir_evento` → domínio do catálogo (bloco null)
2. IA → `bloco_escolhido`
3. `atualizar_associacoes_evento` → completa evento
4. `inserir_backlog_mesa` + `materializar_postit_mesa` → backlog + Mesa

---

## 8. Mesa de Inovação Organizacional (UI)

- Cards **`.post-it-telemetria`**: fundo avermelhado, borda esquerda vermelha, animação pulse
- Título **🚨** + hipótese IA no corpo
- CTA **Transformar em Sprint** no rodapé → `/api/sprints/importar`
- API `/api/mesa-inovacao/notas` serializa: `dominio_associado`, `bloco_associado`, `codigo_evento_padrao`, `dimensao_fixada`

---

## 9. Ferramenta de QA — `simulador_esim.py` (operadora externa)

O simulador **não importa** módulos do PanelDX e **não conhece** o Framework LeAction.
Envia apenas telemetria bruta; a correlação é 100% interna (`event_catalog.py` + webhook).

```powershell
cd C:\Projetos\PanelDX
python scripts/simulador_esim.py
python scripts/simulador_esim.py --codigo-evento GARGALO_ADMN_SEC
python scripts/simulador_esim.py --codigo-evento LENTIDAO_TI_SIST --cliente-id 1
python scripts/simulador_esim.py --listar-codigos
```

**Campos enviados pelo simulador (contrato operadora):**
`cliente_id`, `codigo_evento`, `iccid`, `timestamp`, `grupo_acesso`, `dominio_acessado`,
`status_anomalia`, `trafego_mb_7dias`, `variacao_percentual`, `titulo_alerta`, `descricao_evento`

**Campos proibidos no webhook** (rejeitados em `schemas.py`):
`dimensao_fixada`, `dominio_fixado`, `blocos_candidatos*`, `bloco_associado`, `dominio_associado`

---

## 10. Resultado do teste local (referência)

| Campo | Valor observado |
|-------|-----------------|
| Status HTTP | **201 CREATED** |
| `codigo_evento_padrao` | `QDA_ACESSO_PEDAG` |
| `ia_processada` | `true` |
| `ia_fallback` | `true` (Bedrock off em dev) |
| `bloco_escolhido` | `Portal de Integração dos Aprendizes` |
| `id_evento` / `id_item_backlog` / `id_nota_mesa` | criados |

---

## 11. Epics — status

| Epic | Descrição | Status |
|------|-----------|--------|
| E1 | Ingestão webhook + tabelas + auth | ✅ Concluído |
| E2 | Orquestração IA Bedrock + fallback | ✅ Concluído |
| E3 | Backlog separado → Mesa Org | ✅ Concluído |
| E4 | UI alertas telemetria + CTA sprint + painel eSIM | ✅ Concluído |
| E5 | Hardening produção + deploy | ⏳ Pendente (sem deploy prod) |
| **E6** | **Catálogo LeAction + codigo_evento_padrao** | ✅ Concluído |
| **E7** | **Prompt restrito + bloco_escolhido** | ✅ Concluído |
| **E8** | **Persistência dominio/bloco (008) + serialização Kanban** | ✅ Concluído |
| **E9** | **Simulador QA v2 (contrato unificado)** | ✅ Concluído |

---

## 12. Pendências

- [ ] Deploy produção (backend + migrations 007 + 008)
- [ ] Configurar `BASEMOBILE_WEBHOOK_SECRET` em ECS
- [x] Painel lateral “Backlog Preditivo (eSIM)” na Mesa Org
- [x] Marcar item `consumido` em `basemobile_mesa_backlog` ao lapidar/incubar
- [x] CloudWatch / dead-letter Bedrock (`integrations/basemobile/observability.py`)
- [x] Rate limit no webhook (`integrations/basemobile/rate_limit.py`, HTTP 429)
- [ ] Frontend Kanban: consumir `bloco_associado` na criação de sprint a partir de telemetria

---

## 13. Como testar (dev)

```powershell
# Terminal 1 — Backend
cd LeAction_SysF
python app.py

# Terminal 2 — Simulador
cd C:\Projetos\PanelDX
python scripts/simulador_esim.py

# UI
http://localhost:3000/projeto/mesa-inovacao
```

---

## 14. Localização no Explorer

```
C:\Projetos\PanelDX\LeAction_SysF\integrations\basemobile\
```

Documentação: `C:\Projetos\PanelDX\docs\basemobile\`
