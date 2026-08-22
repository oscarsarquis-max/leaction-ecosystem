# Relatórios como projeções

Não há cadastro paralelo de “relatório”. Tudo deriva de ordem, snapshot e eventos.

## Eventos necessários

| Pergunta | Eventos / dados |
|---|---|
| Planejado vs produzido | snapshot de escala + `yield.recorded` / `order.completed` |
| Consumo previsto vs real | materiais planejados + `consumption.recorded` |
| Rendimento e perda | previsto no snapshot + rendimento/descarte |
| Atrasos | horários previstos na ordem + `step.started` / `finished` |
| Interrupções | `order.held` / `resumed` |
| Ocorrências e causas | `occurrence.recorded`, `material.short`, `batch.scrapped` |
| Rastreio ordem/batelada/lote | conferências + consumo com lote |
| Produtividade por produto/período/estação | agregação de conclusões — **sem ranking individual de padeiro** |
| Histórico da versão | `order.released` aponta snapshot; lab continua em `formulation_version` |
| Necessidade e desvio de ingredientes | soma dos snapshots do plano vs consumos |

## Três camadas

| Camada | Público | Conteúdo |
|---|---|---|
| Projeção operacional | quadro e ficha | estado, próxima ação, alertas |
| Relatório gerencial | gestores | totais do recorte, perdas, atrasos — sem custo no mesmo ecrã do padeiro |
| Trilha de auditoria | `audit_event` + eventos de produção | quem, quando, comando, motivo |

Evitar métricas por pessoa que incentivem pressa insegura ou avaliação injusta. Produtividade é do **produto / estação / período**, não do indivíduo.
