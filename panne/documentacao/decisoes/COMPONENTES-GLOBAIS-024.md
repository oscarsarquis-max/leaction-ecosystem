# Componentes globais — CURSOR-024

Unificação visual sem trocar contrato.

## Ações

- Primário: `.primary` — ação principal do recorte.
- Secundário/ghost: `.ghost` — troca de contexto, minimizar, limpar.
- Destrutivo: permanece no fluxo existente de cancelamento, com confirmação.
- Contextual: chips e cartões de situação.

## Entrada

Campo, busca, autocomplete (`datalist`), select de catálogo e grupo segmentado (visões do quadro). Cardinalidade baixa usa select; busca cobre código ou texto.

## Feedback

- Badge com tom e rótulo textual (`StatusBadge`).
- Cartão de resumo clicável no quadro.
- Tabela densa sempre que houver visão gráfica.
- Painel vazio com próxima ação.
- Gaveta da ordem e do assistente, com Escape seguro.
- Confirmação ao trocar contexto com ordem aberta.
- 409 permanece no `ErrorState` existente.
- Skeleton só nas laterais do login.
- Toast continua reservado a mensagens transitórias; erro persistente usa painel.
