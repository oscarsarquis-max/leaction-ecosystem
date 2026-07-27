# Assistente de navegação (árvore + co-criação)

## O que mudou

O FAB **Enviar Ideia** (`CoCriacaoEntry`) virou o widget **Assistente** (`AssistenteChat`):

1. Árvore de decisão por botões (sem IA; conteúdo do Hub CMS ou fallback local)
2. Campo de sugestão **sempre no topo** → `POST /api/feedbacks` (fluxo de crédito intacto: status `pendente`, recompensa por revisão)

## Nomenclatura usada (validada no produto)

| Proposta genérica | Termo real na UI |
|-------------------|------------------|
| 4 Pilares | 4 estações do Dia a Dia |
| Dinâmica Rápida / Minute Paper | Atividade em campo (catálogo de dinâmicas) |
| Sprint | Ciclo da aula / continuidade·reinício EduScrum |
| Kanban genérico | Para Fazer → Fazendo → Pronto |

Limites freemium (fonte: `db.py`): **5** aulas/mês · **1** desafio IA.

## API

- `GET /api/assistente-chat` — árvore (Hub `/api/cms/assistente-chat` + cache + fallback)
- `POST /api/feedbacks` — inalterado

## Persona

**Nina** (decisão definitiva do Oscar). Tagline: Guia do inovador.

## Arquivos

- `backend/assistente_chat_routes.py`
- `backend/assistente_chat_fallback.py`
- `backend/services/hub_cms_cache.py` (`fetch_assistente_chat`)
- `frontend/src/components/AssistenteChat.jsx`
- Contrato Hub: `inove4us_docs/action-hub-briefing-cms-assistente-chat.md`
