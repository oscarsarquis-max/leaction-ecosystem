# AF-ADR-007 — Idempotência persistida e concorrência otimista

## Controle

| Campo | Valor |
|---|---|
| Identificador | AF-ADR-007 |
| Versão | 0.1 |
| Status | PROPOSED |
| Data | 25/09/2026 |
| Dependências | ACTIONFINANCE_ARQ_001 §7.2–7.3 |

## Contexto

A idempotência do serviço de satélite da Spider está em `ConcurrentHashMap` e some no restart. Duas confirmações do mesmo formulário não podem criar duas obrigações. Edição concorrente não pode sobrescrever em silêncio.

## Decisão

- `request_idempotency`: empresa + escopo + chave, fingerprint semântico, referência e resultado seguro; unique composto; persistido na mesma transação da criação local.
- Mesma chave + mesmo fingerprint: mesmo resultado. Mesma chave + fingerprint diferente: conflito.
- Fingerprint inclui empresa e campos de efeito de negócio; exclui timestamps de transporte e segredos.
- `version` em obrigação para concorrência otimista.
- A UI preserva a chave até resultado conclusivo; timeout não renova a chave.

Retenção não reabre janela de duplicação sem regra documentada (PRM_003).

## Alternativas rejeitadas

1. Idempotência só na Spider ou só em memória do processo.
2. Unique só na aplicação, sem constraint.
3. Sobrescrever no conflito de versão.

## Consequências

- Testes de concorrência e retry entram no gate do domínio.
- Idempotência da Spider não substitui a do ActionFinance.
