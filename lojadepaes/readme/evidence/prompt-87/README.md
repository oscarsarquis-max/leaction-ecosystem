# Prompt 87 — Gigio no Fazedor de Pães

07/10/2026. Incremento depois do Prompt 86 (`prod-20261007m`). Sem migração. Sem pedido, pagamento ou e-mail real em produção.

## Produção efetiva

| Peça | Valor |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem Loja | `lojadepaes:prod-20261007o` (rollback de app: `prod-20261007m`; não usar `h` nem o `n` incompleto) |
| Bundle | `/assets/index-jO8kSabC.js` |
| Backup no host | `/opt/lojadepaes/backups/lojadepaes-20261007T231219Z.sql.gz` |
| Alembic | `f3c9a1b28e04` — sem mudança |
| Regras | `87` |
| Flags | Gigio, vitrine, complementos e pairing on |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

## Capacidades reais usadas (fonte canônica)

Não há lista paralela no prompt. `lookup_builder` e `propose_builder` leem `public_builder_catalog`.

| Campo | Slugs ativos hoje |
|---|---|
| Farinhas | `farinha-branca-strong-white`, `farinha-integral-trigo`, `farinha-integral-centeio`, `farinha-fuba` |
| Preparos | `fermentacao-natural-curta`, `maturada`, `sovada` |
| Complementos | `nozes`, `castanha-de-caju`, `granola`, `tomate-seco`, `berinjela`, `queijo-parmesao` |
| Formatos | `rustico-de-cesto`, `pao-de-forma` |

Farinha italiana existe no cadastro e permanece **inativa**. Não há opção estruturada «grãos»; granola é o cereal do contrato. Campo livre continua observação para A Loja avaliar.

## Jornadas

1. Conversa → `lookup_products` + `lookup_builder` + `propose_builder` (slugs validados) → CTA **Montar esse pão** com token assinado → Criador preenchido, editável, sem carrinho/pedido/data.
2. Composição estável no passo da forma → **Uma dica do Gigio para o seu pão** (não bloqueia). **Aplicar sugestão** só com escolha explícita. **Conversar com o Gigio** reabre o painel único.

## Prova isolada

- `tests/test_prompt87.py` — proposta, rejeição de slug, dica, restrição, falha do modelo
- `tests/test_prompt87_date_request.py` — regressão permanente: focaccia hoje, fila, outbox, aceite, reserva, pagamento, endereço incompleto, idempotência, pedido padrão, personalizado, Gigio off
- Regressão 68/67/custom_loaf/63 e frontend BreadBuilder + GigioHost

## Produção (07/10/2026, sem pedido)

Pergunta de sanduíche ao vivo (`prod/chat-sanduiche.json`): catálogo + capacidades + `propose_builder`. CTA **Montar esse pão** com token assinado. Proposta resolvida: Branca, fermentação natural curta, pão de forma, R$ 70 / 500 g. Dica da mesma composição (`prod/builder-tip.json`).

Telas (`prod/builder-proposta-1440.png`, `builder-dica-1440.png` / `390.png` / `320.png`): aviso do Gigio, escolhas preenchidas e editáveis, bloco da dica, **Conversar com o Gigio**, **Pedir nova dica**, **Combinar o encontro** visível. Sem carrinho e sem envio.

## Limitações concretas

- A dica desta sessão não trouxe CTA comercial: não havia oferta verificada compatível com a massa.
- Parmesão só entra se o cliente aplicar a sugestão; a proposta do sanduíche foi sem complemento estruturado.
- Farinha italiana continua inativa. Não existe opção «grãos»; granola é o cereal do contrato.
- A captura headless distorce a webfont; o HTML/CSS publicados não reduzem fonte nem escondem overflow.
- Pedido histórico da cliente e SES real não foram reabertos. Fechamento excepcional foi a regressão isolada, não um envio em produção.

## O que não mudou

Receitas, avaliações de guia, pedidos, pagamentos, fidelidade, endereços, calendário comercial, modelo AWS e credenciais. Sem combo marketplace. Sem cópia de banco local.

## Rollback

`LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007m` e recreate da API. Chat comum e compra permanecem.
