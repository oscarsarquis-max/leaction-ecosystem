# Prompt 78 — Precisão comercial da curadoria contextual

07/10/2026. Correção pontual. Sem redesign, pedido, e-mail, cobrança ou compra externa.

## Publicado

| Peça | Estado |
|---|---|
| Hub marketplace | plugin Flask em `actionhub.com.br` (PM2 `marketplace-api`) |
| Rollback Hub | `/var/lib/leaction-platform/rollback-prompt78-20261007T140649Z` |
| Loja | `lojadepaes:prod-20261007c` (rollback de app: `prod-20261007b`; bundle `/assets/index-zwbhWtVP.js`) |
| Alembic Loja | `b8e4c1d93f50` (inalterado) |
| Hub FE / gateway / pagamentos | não republicados |

## O que estava errado

A busca do Hub era `q=` no Mercado Livre + filtro de substring no título. «Vinho» no título bastava. Havia passo relaxado quando a prateleira ficava curta. Amazon entrava sem o mesmo filtro. `domain_id` oficial não era lido.

Por isso passaram: gravata «cor vinho», livro/3drose «vinho tinto», copa Mikasa e chaveiro da Copa do Mundo na prateleira de frios.

## Correção na fonte (Hub)

1. Recuperação de candidatos: mesmos termos curados do perfil A Loja.
2. Validação de natureza (`offer_relevance.py`): categoria/domínio oficiais do provedor quando existem + regras configuráveis de inclusão/exclusão por prateleira. Sem IA.
3. Ambíguo → revisão, fora da recomendação publicada.
4. Exceção humana auditável em `marketplace_offer_decisions` (aprovar/rejeitar com motivo).
5. Diagnóstico editorial: `GET /api/marketplace/diagnosis?origin=lojadepaes&category=vinhos`.
6. Sem passo relaxado nas prateleiras culinárias. Amazon passa pela mesma validação.
7. Cache do plugin limpo no restart / ao gravar regra.

A Loja só recusa o que foge do contrato (`offer_contract.py`). Não há catálogo paralelo.

## Antes / depois

**Antes (Hub ao vivo, frios):** «Copa Italiana de Campo Mikasa…» e «Kit 3 Chaveiros Troféu Taça Copa Do Mundo…» junto com presunto. Vitrine da Loja (Prompt 77) chegou a servir gravata e livro na prateleira de vinhos quando o termo sorteado era «vinho tinto mesa».

**Depois (Hub público, mesma origem):**

| Prateleira | Itens | Ruído (gravata/livro/chaveiro/Mikasa) |
|---|---|---|
| vinhos | 7 | 0 |
| queijos | 6 | 0 |
| frios | 7 | 0 |
| azeites | 8 | 0 |

Consulta reproduzida `q=vinho tinto mesa`: 11 vinhos/espumantes reais; 1 rejeição (não publicada). Gravata e 3drose não reaparecem pelo mesmo caminho: falham natureza (roupa/tema) mesmo com «vinho» no título.

Itens válidos não foram zerados. Vitrine da Loja após o contrato: **28** itens (7 vinhos, 6 queijos, 7 frios, 8 azeites). Capturas em `readme/evidence/prompt-78/prod/`.

Ainda pode aparecer alimento em mais de uma prateleira (ex.: salame com gorgonzola na lista de queijos). Não é gravata nem livro.

## Flags Loja

Vitrine pública on; complementos do Gigio on. Pedidos/pagamentos/fidelidade intactos.

## Medição comercial — só fundação (não implantada)

O plugin de marketplace **não** registra clique hoje. O CRM do gateway cobre fornada/checkout da Loja, não oferta contextual.

Esquema mínimo proposto (etapa seguinte, sem pixel externo nem chat/CPF/pedido):

| Campo | Uso |
|---|---|
| `profile` | `lojadepaes` |
| `surface` | `generic` \| `gigio` |
| `context` | `cats`/`tipo` normalizados, sem restrição alimentar |
| `offer_id` | ID do Hub já publicado |
| `event` | `impression` \| `click` |
| `dest` | host permitido (ML/Amazon) |

Clique ≠ venda. Comissão só quando o mecanismo oficial do afiliado confirmar. Sem rastreamento individual nesta correção.

## Rollback

- Hub: restaurar `$RB/backend` e `pm2 restart marketplace-api`.
- Loja: `LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007b`.
- Só a jornada Gigio: flag de complementos em false (independente desta curadoria).
