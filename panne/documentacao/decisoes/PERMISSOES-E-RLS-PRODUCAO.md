# Permissões e RLS futuras de produção

Ciclo 012 gravou as permissões abaixo. Não implementa múltiplos papéis. `costing.read` continua inexistente.

## Permissões propostas

| Código | Ação |
|---|---|
| `production.board.read` | Ver quadro |
| `production.plan` | Montar/trancar plano |
| `production.order.release` | Liberar (snapshot) |
| `production.order.run` | Iniciar, pausar, retomar |
| `production.consumption.record` | Apontar consumo |
| `production.yield.record` | Apontar resultado |
| `production.occurrence.record` | Ocorrência |
| `production.order.complete` | Concluir / short close |
| `production.order.cancel` | Cancelar |
| `production.order.reopen` | Reabrir via nova ordem |
| `production.ticket.issue` | Emitir ficha |
| `production.trace.read` | Rastreio |
| `costing.read` | Ver custos — **nunca** no papel de padeiro por padrão |

Mapeamento inicial (sem gravar):

- `baker_operator`: quadro, run, consumo, ocorrência, emitir ficha da própria estação, yield se política permitir.
- `production` / `production_manager`: plano, liberar, concluir, cancelar, rastreio, quadro.
- `technical_responsible`: rastreio e, se política, coparticipar da liberação.
- `viewer`: quadro e rastreio sem comandos.
- `commercial`: só demanda, sem quadro de execução.
- `costing.read`: owner/admin ou papel futuro de custos — não `baker_operator`.

## Um papel por associação

O modelo atual (`organization_membership.role` único) **não cobre** bem o padeiro que também planeja no mesmo estabelecimento. Opções futuras (não implementar agora):

1. múltiplos papéis por associação;
2. duas associações (rejeitada: unique org+user);
3. permissões avulsas além do papel.

Questão aberta de prioridade alta.

## RLS

Tabelas futuras de produção: organizacionais, ENABLE+FORCE, `organization_id = panne_current_org_id()`, default deny. Estabelecimento é atributo da linha, não tenant. Emissões e eventos herdam a org da ordem. Sem política ampla. Runtime continua sem `BYPASSRLS`.
