# Inventário — linguagem técnica na Panne Demo 026 (R026-004)

Auditoria contextual (não substituição cega). Decisão: [LINGUAGEM-HUMANA-E-DIVULGACAO-TECNICA.md](../decisoes/LINGUAGEM-HUMANA-E-DIVULGACAO-TECNICA.md).

**Estado geral R026-004:** **validada integralmente pelo Cortex no navegador**.

## Validados pelo Cortex

| Item | Status |
|---|---|
| Isolamento visual Panne → Horizonte → Panne | **validado** |
| Limpeza imediata + loading na troca | **validado** |
| Proteção contra resposta atrasada | **validado** |
| Conteúdo líquido `50 g` | **validado** |
| Plural estoque (`6 posições`) | **validado** |
| Totais estoque coerentes | **validado** |
| Detalhe da ordem (passagem anterior) | **validado** — não regredir |
| Perfil: Sim / Não / Não informado | **validado** |
| Perfil: `Varejo`, `Sólido` | **validado** |
| Achado: `Lactose — evidência insuficiente` | **validado** |
| Superfície sem `true`/`false`/`retail`/`solid`/`Código técnico não catalogado` | **validado** |

## Status por bloco

| Bloco | Status |
|---|---|
| Detalhe da ordem | **validado** (Cortex) |
| Isolamento org + qty líquida + plural | **validado** (Cortex) |
| Perfil booleanos/enums + achado `lactose` | **validado** (Cortex) |
| Cancelamento / plano / estoque agregação / dossiê lista | **validado** (passagens anteriores + final) |
| R026-004 geral | **validada integralmente pelo Cortex** |

## Tratamentos aplicados (perfil / achados)

| Superfície | Achado original | Tratamento |
|---|---|---|
| Perfil de aplicabilidade | `true`/`false`/`null` | select Sim / Não / Não informado |
| Perfil | `retail`, `solid` | catálogos `SALES_CHANNEL_LABEL` / `PHYSICAL_STATE_LABEL` |
| Achados | `Código técnico não catalogado` | código real `lactose` → rótulo humano |

## Mapeamento enums (perfil)

### Canal de venda

| Código | Linguagem |
|---|---|
| retail | Varejo |
| own_store | Loja própria |
| food_service | Serviço de alimentação |
| wholesale | Atacado |
| e_commerce | Comércio eletrônico |
| online | Venda online |
| other | Outro canal |
| (desconhecido) | Opção ainda não catalogada (+ auditoria) |

### Estado físico

| Código | Linguagem |
|---|---|
| solid | Sólido |
| semisolid | Semissólido |
| liquid | Líquido |
| powder | Pó |
| gas | Gasoso |
| other | Outro estado físico |
| (desconhecido) | Opção ainda não catalogada (+ auditoria) |

### Categoria regulatória

| Código | Linguagem |
|---|---|
| pao | Pães |
| bolo | Bolos e similares |
| biscoito | Biscoitos e cookies |
| massa | Massas e similares |

## Achado lactose

| Campo | Valor |
|---|---|
| `rule_code` | `lactose` |
| Origem | `warnings.py` → finding em `evaluate.py` |
| Rótulo | Lactose — evidência insuficiente |

## Evidências

- `documentacao/evidencias/cursor-026/revisao-proprietario/R026-004-linguagem-humana.md`
- `documentacao/evidencias/cursor-026/revisao-proprietario/R026-004-isolamento-org.md`
- `documentacao/evidencias/cursor-026/revisao-proprietario/R026-004-perfil-humano.md`
- `documentacao/evidencias/cursor-026/revisao-proprietario/R026-004-scanner.md`
