# AF-ADR-005 — Dinheiro inteiro exato e API decimal em string

## Controle

| Campo | Valor |
|---|---|
| Identificador | AF-ADR-005 |
| Versão | 0.2 |
| Status | PROPOSED |
| Data | 25/09/2026 |
| Dependências | ACTIONFINANCE_ARQ_001 §7.3 |

## Contexto

JavaScript e JSON number perdem precisão em valores financeiros. “Saldo disponível” derivado da soma de títulos mistura projeção com fato.

## Decisão

- Persistência: unidades mínimas inteiras (`numeric(19,0)` proposto) e código de moeda explícito.
- API: string decimal inteira (unidades mínimas). Backend com representação exata.
- UI não calcula dinheiro com ponto flutuante.
- Primeira fatia: BRL, escala 2, valor positivo. Teto de negócio **não definido** neste ADR (não inventar). ISO-4217 com três letras não autoriza outras moedas.
- Não persistir saldo bancário como soma de obrigações.

## Alternativas rejeitadas

1. `double` / `float` / JSON number.
2. Aceitar qualquer `currency` de três letras.
3. Campo “saldo” na lista de a pagar.

## Consequências

- Formatação BRL é apresentação, não aritmética.
- Projeção de caixa, saldo informado e saldo conciliado terão fontes distintas quando existirem.
