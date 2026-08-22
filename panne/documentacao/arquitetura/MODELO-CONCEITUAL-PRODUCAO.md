# Modelo conceitual de produção

Proposta sem tabelas físicas. Estoque, compras, custos e manutenção ficam fora.

Convenções: identidade UUID; `organization_id` obrigatório; `establishment_id` na ordem e no plano; RLS organizacional; exclusão lógica no máximo (preferir cancelamento); eventos críticos append-only.

## `ProductionPlan`

- Identidade: plano do recorte.
- Relação: 1 estabelecimento; N `ProductionPlanItem`.
- Campos: data operacional, turno, status, notas.
- Fonte: o próprio plano.
- Mutável só antes de `locked`. Sem exclusão física.
- Eventos: composição, trava, reabertura.
- Permissão: `production.plan`.

## `ProductionPlanItem`

- 1 plano : N itens; 0..1 ordem gerada.
- Campos: produto técnico, quantidade demandada, prioridade, dependência (pré-fermento).
- Fonte: demanda consolidada.
- Mutável até a ordem ser liberada.

## `ProductionOrder`

- 1 item de plano : 0..1 ordem (ou 1 demanda direta).
- 1 produto, 1 versão de formulação **aprovada**, 1 estabelecimento, N bateladas.
- Campos: código visível, estado, alvo (peças/massa), horários previstos, responsável.
- Fonte de verdade do chão: **a ordem**.
- Snapshot anexado na liberação. Depois disso a ordem não herda mudanças da formulação viva.
- Cancelamento com motivo. Sem exclusão física.
- RLS: `organization_id`. Permissões por transição.

## `ProductionBatch`

- N bateladas : 1 ordem.
- Campos: sequência, alvo da batelada, estação/equipamento previsto, estado próprio.
- Fonte: partição executável da ordem.
- Mutável em estado e apontamentos; alvo congelado na criação após liberação.

## Snapshot da formulação

- Cópia da `formulation_version` aprovada (itens, etapas, notas, hashes).
- 1:1 com a ordem na liberação (ou 1:N se bateladas compartilharem o mesmo snapshot de ordem).
- Imutável. Exclusão proibida.
- Permite reconstruir a ficha sem ler a versão atual do lab.

## Snapshot da escala

- Resultado de `scale_calculation` no ato da liberação (fator, massas, linhas, algoritmo e versão do motor).
- Imutável. Determinístico e reconstruível (invariantes 2 e 3).
- Não é recalculado na execução.

## Materiais planejados

- Linhas do snapshot de escala + unidade + sequência operacional.
- Imutáveis. Consumo real **não** sobrescreve.

## Separação e conferência

- 1 ordem/batelada : N conferências.
- Campos: material, lote informado, peso conferido, operador, horário, resultado (ok/falta/substituição).
- Mutável só por novo evento, não por update destrutivo.

## Etapas planejadas

- Cópia de `process_step` no snapshot: sequência, instrução, tempo e temperatura previstos.
- Imutáveis.

## Execução da etapa

- 1 etapa planejada : N execuções (pausa/retomada).
- Campos: início, fim, estação real, operador, estado.
- Eventos append-only.

## Consumo real / rendimento / desvio

- Consumo: material, quantidade, lote, batelada. Não altera planejado.
- Rendimento: previsto (snapshot) vs vendável apontado.
- Ocorrência: tipo (falta, quebra, descarte, retrabalho, atraso), motivo, gravidade.

## Evento de produção

- Envelope append-only: tipo, agregado (plano/ordem/batelada), ator, correlação, payload.
- Alimenta quadro, ficha (versão emitida) e relatórios.
- RLS organizacional. Sem update/delete.

## Emissão da ficha

- Registro: ordem, batelada opcional, número da emissão, hash do snapshot, emitente, instante.
- Reimpressão gera nova emissão com o **mesmo** snapshot, novo número.
- Cancelamento da ordem invalida emissões posteriores (código curto recusado).

## Recurso / equipamento / área / estação

- Cadastro mínimo (código, tipo, estabelecimento, capacidade declarada).
- Não é CMMS. Manutenção completa fica fora.
- Usado para filtro do quadro e para dimensionar bateladas.

Cardinalidades-resumo: Plano 1—N Itens; Item 0..1 Ordem; Ordem 1—N Bateladas; Ordem 1—1 Snapshot formulação; Ordem 1—1 Snapshot escala; Ordem 1—N Eventos; Ordem 1—N Emissões.
