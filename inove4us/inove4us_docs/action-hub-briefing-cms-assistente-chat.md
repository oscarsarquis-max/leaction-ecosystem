# Briefing Action Hub — CMS Assistente Chat (inove4us)

Contrato para o Headless CMS servir a árvore do assistente de navegação.
O BFF do inove4us chama este endpoint com cache local (mesmo padrão de notícias).

## Endpoint Hub

```
GET /api/cms/assistente-chat?sistema_destino=inove4us
```

Autenticação: igual aos posts CMS (S2S / público publicado — a definir na implementação Hub).

## Resposta JSON

```json
{
  "tree": {
    "avatar_name": "Nina",
    "avatar_tagline": "Guia do inovador",
    "avatar_candidates": ["Nina"],
    "root_id": "inicio",
    "nodes": {
      "inicio": {
        "message": "Texto da mensagem…",
        "options": [
          { "label": "Aulas do Dia a Dia (rápido)", "next": "dia_a_dia" },
          { "label": "Abrir Dia a Dia", "next": "dia_a_dia", "href": "/dia-a-dia" },
          { "label": "Como assinar?", "next": "planos_assinar", "action": "open_upgrade" }
        ]
      }
    }
  }
}
```

### Campos

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `avatar_name` | sim | Nome da persona — definitivo: **Nina** |
| `root_id` | sim | ID do nó inicial |
| `nodes` | sim | Mapa id → nó |
| `nodes[].message` | sim | Texto (aceita `{{FREEMIUM_AULAS}}` e `{{FREEMIUM_DESAFIOS}}`) |
| `nodes[].options[].label` | sim | Texto do botão |
| `nodes[].options[].next` | recomendado | Próximo nó |
| `nodes[].options[].href` | não | Rota interna (`/desafio`, `/dia-a-dia`, …) |
| `nodes[].options[].action` | não | Ação FE: `open_upgrade` |

### Placeholders dinâmicos

O backend inove4us substitui antes de devolver ao FE:

- `{{FREEMIUM_AULAS}}` → `FREEMIUM_AULAS_MES` (hoje 0 — só navegação no Dia a Dia)
- `{{FREEMIUM_DESAFIOS}}` → `CREDITO_IA_FREEMIUM_DEFAULT` (hoje 1)

## Nomenclatura do produto (não inventar termos)

Use estes termos — são os da UI real:

- **Dia a Dia** — 4 estações: Alinhamento · Entrega do dia · Atividade em campo · Retro do ciclo
- **Desafios** / plano **EduScrum**
- **Kanban**: colunas **Para Fazer · Fazendo · Pronto** (não “Sprint”)
- Limites freemium: **1 desafio** (crédito IA); Dia a Dia **sem registro** (só navegação)

## Fallback

Se o Hub falhar, o inove4us serve `assistente_chat_fallback.py` (árvore mínima local).

## Fora de escopo

- IA na árvore
- Crédito automático por sugestão (continua `POST /api/feedbacks` → status `pendente`)
