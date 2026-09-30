# AF-ADR-010 — UX operacional progressiva

## Controle

| Campo | Valor |
|---|---|
| Identificador | AF-ADR-010 |
| Versão | 0.1 |
| Status | PROPOSED |
| Data | 25/09/2026 |
| Dependências | ACTIONFINANCE_ARQ_001 §10 |

## Contexto

SegSense e SpiderBank têm homepage editorial. O Monitor é superfície técnica da Spider. Nenhum dos dois é ferramenta de contas a pagar.

## Decisão

A UI é ferramenta de trabalho: só funções e números que existem em persistência. Primeira fatia: Contas a pagar e cadastros necessários. Roadmap fica na documentação, não na navegação.

Não inventar dashboard, badge “Spider conectado”, IDs vazios, botão Pagar ou seleção em massa. Registrar obrigação deixa explícito que nenhum pagamento foi executado.

Identidade visual proposta: fundo cinza muito claro, superfícies brancas, texto grafite, azul-petróleo na ação principal, números tabulares. Verde só para conclusão comprovada.

## Alternativas rejeitadas

1. Copiar a homepage SegSense/SpiderBank.
2. Menus de Caixa/Conciliação/DRE vazios.
3. Total da página apresentado como saldo.

## Consequências

- Tokens e medidas finais no prompt de UX.
- Desktop prioritário; mobile em cartões; teclado e contraste são aceite, não enfeite.
