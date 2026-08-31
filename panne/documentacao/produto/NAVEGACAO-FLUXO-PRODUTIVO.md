# Navegação — Fluxo produtivo

**Ciclo:** CURSOR-028-A.  
**Entrega alvo:** 028-B (página e shell; sem novo domínio pesado).

## Objetivo

Página persistente **Fluxo produtivo** — imediatamente visível no desktop e acessível no mobile — que orquestra a jornada em 8 etapas, reutiliza telas existentes, mostra estado (concluído / pendente / bloqueado), próxima ação, anterior/próximo, “Voltar ao fluxo”, e respeita perfil (sem custos na cozinha).

## Posição no shell

| Superfície | Comportamento |
|---|---|
| Desktop | Item de 1º nível **Fluxo produtivo** no cabeçalho (fora do hambúrguer); trilha 1→8 nas páginas relacionadas |
| Mobile | Pin persistente **Fluxo** no cabeçalho + entrada no menu; indicador `Etapa N de 8` |
| Deep link | `/fluxo` — redirect pós-login e pós-seleção de org (substitui `/producao` como entrada) |
| Quadro | Continua em `/producao`, acessível pelo menu Produção |
| Retorno | `?from=fluxo&step=N` nas telas filhas; **Voltar ao fluxo** |

Não confundir com a visão do quadro “Fluxo por estado” (status de OP).

## Decisões de domínio (028-B)

Ver `ESPINHA-DORSAL-FLUXO-PRODUTIVO.md` § Decisões fechadas.

## Oito passos

| Step | Rótulo | Destino reuso (hoje) | Gate típico |
|---|---|---|---|
| 1 | Compras e recebimentos | `/gestao/compras`, recebimentos | procurement.* |
| 2 | Ingredientes e estoque | `/componentes/ingredientes`, estoque, lotes | catalog / inventory |
| 3 | Produtos | **placeholder** até 028-C → depois `/produtos` | product.* (novo) |
| 4 | Receitas | `/receitas` | formula.* |
| 5 | Planejamento e ordens | `/planejamento`, `/ordens`, `/producao` | production.plan/order |
| 6 | Preparo e execução | `/producao/ordens/:id/executar` | production.execute |
| 7 | Produto acabado e rotulagem | rotulagem / conformidade | labeling.*; FG TBD |
| 8 | Custos e preços | `/gestao/custos/*` | costing.* / pricing.* — **oculto** se sem permissão |

## Estados por passo

| Estado | Significado UX |
|---|---|
| Concluído | Há evidência mínima no contexto (ex.: recebimento recente, receita aprovada) — regras leves na 028-B |
| Pendente | Passo acessível, sem evidência |
| Bloqueado | Sem permissão **ou** dependência (ex.: OP sem receita vigente) |
| Atual | Passo em foco |

028-B: estados heurísticos + permissões. 028-I: critérios reais por perfil/demo.

## Comportamentos obrigatórios

- Anterior / Próximo entre steps visíveis ao perfil.
- Drill-down para tela existente; breadcrumb ou chip **Voltar ao fluxo**.
- Próxima ação textual (ex.: “Receber PO #…”, “Aprovar versão da receita”).
- Perfil cozinha: steps 8 oculto; impressões sem valores.
- Não esconder o Fluxo apenas no menu mobile.

## Wireframe textual — desktop

```
┌─ Shell ──────────────────────────────────────────────────────────┐
│ [Logo]  Fluxo  Produção  Componentes  Receitas  …  [Conta]       │
├──────────────────────────────────────────────────────────────────┤
│ Fluxo produtivo                          Org · Estabelecimento   │
│                                                                  │
│ (1)Compras → (2)Estoque → (3)Produtos → (4)Receitas →            │
│ (5)Ordens → (6)Execução → (7)Acabado → (8)Custos                 │
│      ●concluído  ◐atual  ○pendente  ■bloqueado                   │
│                                                                  │
│ ┌─ Passo 4 · Receitas ─────────────────────────────────────────┐ │
│ │ Status: pendente                                              │ │
│ │ Próxima ação: Vincular receita vigente ao Bolo de chocolate   │ │
│ │ [Abrir receitas]  [Anterior]  [Próximo]                       │ │
│ │ Resumo: 3 rascunhos · 12 aprovadas                            │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ Atalhos do passo: listagem embutida ou iframe-rota / link cards  │
└──────────────────────────────────────────────────────────────────┘
```

## Wireframe textual — mobile

```
┌────────────────────┐
│ Panne ≡  Fluxo     │
│ Org · …            │
├────────────────────┤
│ Passo 4/8 Receitas │
│ ○○○●○○○○           │
│ Pendente           │
│ Próxima: Vincular… │
│ [Abrir]            │
│ [< Ant] [Próx >]   │
│                    │
│ Voltar ao fluxo    │
│ (sempre visível    │
│  ao sair do passo) │
├────────────────────┤
│ [Fluxo][Prod][…]   │  ← tab bar opcional
└────────────────────┘
```

## Adaptação por perfil

| Perfil | Steps visíveis | Custos |
|---|---|---|
| Padeiro / execução | 5–7 (2 leitura limitada) | Não |
| Estoque / compras | 1–2 (+7 leitura) | Não (salvo permissão) |
| P&D | 3–4–5 | Não |
| Gestão / owner | 1–8 | Sim |
| Demo multi-perfil | conforme persona 025/026 | conforme persona |

## Situações (028-B)

Somente comprováveis: **Disponível**, **Requer atenção**, **Em andamento**, **Bloqueado**, **Estrutura em preparação**, **Sem acesso**.  
Não usar “Concluído” sem evidência — na dúvida, **Disponível**.

## Critério de aceite da navegação (028-B)

1. `/fluxo` acessível em ≤2 cliques no desktop sem abrir hambúrguer.
2. Mobile: pin **Fluxo** persistente no cabeçalho.
3. Cada step abre tela existente (ou placeholder honestamente marcado).
4. “Voltar ao fluxo” restaura step de origem.
5. Step 8 ausente sem `costing.read` / `pricing.read` / `pricing.review`.
6. Redirect inicial (`/`, login, org, callback) → `/fluxo`; Quadro permanece em `/producao`.
