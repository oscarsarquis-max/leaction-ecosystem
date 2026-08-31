# Regras de resolução — caminho crítico

## Entrada

- `mode`: `org` | `product`
- `evidence`: contagens/summaries org-scoped já existentes
- `product` (quando `product`): código público, `supply_mode`, receita/ordens vinculadas, `mixedOrigin`
- `hasPermission` / perfil: foco e ocultação (etapa 8)

## Ordem do cálculo

1. Filtrar etapas ocultas (`hideWithoutAccess` + sem custos → remove 8)
2. Resolver situação estrutural por etapa (org ou produto)
3. Marcar aplicabilidade (modalidade)
4. `criticalPositionId` = primeira etapa aplicável com acesso cujo estado ≠ Pronto / Não se aplica / Sem acesso
5. `mapLabel` = “Você está aqui” só na posição crítica; senão o estado estrutural
6. `focusId` vem da URL (`etapa`); independente da posição

## Org (preparação)

| Etapa | Pronto / atenção (exemplos) |
|-------|-----------------------------|
| 1 | fiscal.total / pendências de conferência |
| 2 | ingredientes ou saldos |
| 3 | products summary |
| 4 | recipesTotal |
| 5–6 | ordersTotal |
| 7 | estrutura disponível (consulta) |
| 8 | custos (não inventa pronto de produto único) |

“Pronto” estrutural **não** elimina bloqueio anterior.

## Produto

Ver tabela de modalidades no README. Pendência sem entrada: frase humana (“Nenhuma entrada…”), nunca `0 entrada(s) · 0…` como mensagem principal do bloqueio.
