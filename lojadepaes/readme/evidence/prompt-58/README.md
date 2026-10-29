# Prompt 58 — formulário de sugestão de data sempre visível

Alteração só de apresentação no bloco verde da home. Sem mudança de endpoint, agenda, preço ou flags.

O formulário abre na primeira carga, abaixo do calendário. O link «Sugerir uma data» foi removido. Texto único: «Sugira uma data, inclusive para hoje. A Loja avalia a possibilidade e responde por e-mail. Esta solicitação ainda não confirma a fornada.» Instruções do calendário ficam acima da solicitação.

| Tipo | Onde |
|---|---|
| Isolada (RTL) | `frontend/src/shop/DateRequestForm.test.tsx`, `BakeCalendar.test.tsx` |
| Isolada navegador | `isolated-1440.png`, `isolated-768.png`, `isolated-390.png`, `isolated-320.png` |
| Produção | `prod-1440.png`, `prod-390.png` |

Publicado `lojadepaes:prod-20261001c`, bundle `/assets/index-DJDU60Wy.js`. Rollback de app: `prod-20261001b`. Alembic inalterado.
