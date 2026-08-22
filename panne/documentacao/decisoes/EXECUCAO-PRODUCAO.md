# ADR — Execução e apontamentos de produção

Ciclo CURSOR-013. Head `0011_production_execution`.

## Decisão

A execução real da ordem é um domínio de **fatos separados e rastreáveis**: política imutável na liberação, pesagem, conferência, consumo, etapas, rendimento, ocorrências, conclusão/`short_closed` e registro auditável da ficha. Nada disso baixa estoque, calcula custo ou gera PDF.

## Por quê

O 0010 só planeja e congela snapshots. O chão de fábrica precisa registrar o que aconteceu sem sobrescrever o planejado e sem misturar pesado com consumido.

## Consequências

- Correção = novo registro (reversão/correção). Sem exclusão física.
- Projeções (quantidade efetiva, rendimento) são determinísticas a partir dos ledgers.
- `completed` e `short_closed` são estados distintos; o segundo exige permissão, motivo e política que o permita.
- Emissão da ficha não altera a ordem.
- Um papel por associação permanece. Conferência em segunda pessoa é regra de ator, não segundo papel.
