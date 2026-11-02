# CURSOR-032 — Retorno: reset transacional da Loja de Pães

Data: 02/11/2026. **Parei antes de escrever o comando e antes de tocar na produção.** Não criei snapshot, não registrei task definition, não rodei `run-task`, não publiquei nada. A Loja está exatamente como estava.

## Por que parei

A regra do prompt: "Se alguma tabela append-only bloquear o delete, **pare e reporte**." O banco bloqueia o delete na quase totalidade das tabelas transacionais, e o prompt também proíbe desligar triggers. Com as duas regras juntas o reset não tem como rodar.

## Evidência

Base: banco descartável local (Postgres em Docker, porta 55432, não é produção) no schema `0031_ingredient_code_lot_expiry`, o mesmo que a produção roda (imagem `d8d22fe9`, sem migração nova desde a 0031).

1. 156 triggers de proteção em tabelas do schema `public`, todos de nível de linha. Os que cobrem delete chamam a função `panne_forbid_physical_delete`, cujo corpo é só:

   ```
   BEGIN
     RAISE EXCEPTION 'physical_delete_forbidden';
   END;
   ```

   Não há condição, exceção por papel nem variável de sessão que libere. As funções `panne_forbid_mutation`, `panne_inventory_append_only` e `panne_costing_append_only` (bloqueio de update) são do mesmo tipo.

2. Tentativa real, dentro de transação desfeita (`rollback`), conectado como `postgres` (superusuário):

   ```
   begin; delete from inventory_movement where organization_id = <uma org>; rollback;
   ERROR:  physical_delete_forbidden
   begin; delete from inventory_balance  where organization_id = <uma org>; rollback;
   ERROR:  physical_delete_forbidden
   ```

   Se nem o superusuário apaga, o papel da produção também não apaga.

3. Classificando por nome as tabelas com `organization_id` que o prompt chama de transação (proposta, ainda não codificada), **68 de 71 têm trigger que bloqueia delete**. As 3 sem bloqueio são `production_batch`, `production_order_dependency` e `production_plan_item`, que sozinhas não limpam nada porque as filhas e as irmãs ficam de pé.

   Bloqueadas (68): `calculation_evidence`, `costing_assumption`, `costing_calculation`, `costing_command`, `costing_component`, `costing_evidence`, `costing_gap`, `costing_invalidation`, `fiscal_cost_allocation`, `fiscal_document_event`, `fiscal_inbound_attachment`, `fiscal_inbound_document`, `fiscal_inbound_extraction`, `fiscal_inbound_item`, `fiscal_item_match`, `fiscal_physical_line`, `inventory_balance`, `inventory_command`, `inventory_consumption_posting`, `inventory_count_entry`, `inventory_count_review`, `inventory_count_scope`, `inventory_count_session`, `inventory_lot`, `inventory_movement`, `inventory_pick`, `inventory_pick_line`, `inventory_replenishment_item`, `inventory_replenishment_suggestion`, `inventory_reservation`, `inventory_reservation_allocation`, `practiced_price`, `pricing_simulation`, `pricing_simulation_component`, `procurement_order`, `procurement_order_item`, `procurement_order_revision`, `procurement_quotation`, `procurement_quotation_item`, `procurement_receipt`, `procurement_receipt_item`, `procurement_requisition`, `procurement_requisition_item`, `procurement_return`, `production_batch_material`, `production_dependency_override`, `production_event`, `production_material_consumption`, `production_occurrence`, `production_occurrence_event`, `production_order`, `production_order_material`, `production_order_step`, `production_plan`, `production_sheet_issue`, `production_step_execution`, `production_step_execution_event`, `production_weighing_entry`, `production_weighing_session`, `production_weighing_verification`, `production_yield_measurement`, `reporting_command`, `reporting_coverage_item`, `reporting_execution`, `reporting_export`, `reporting_snapshot`, `scale_calculation`, `scale_calculation_item`.

   Também bloqueia delete `supplier_item_price` (o histórico de preço do recebimento), que nem tem `organization_id`.

4. Duas observações que valem para a próxima tentativa:
   - O banco tem 155 tabelas com `organization_id` e 18 sem. As 18 (por exemplo `supplier_item_price`, `access_credential`, `grounding_result`, `role_permission`) também precisam de classificação, e a regra "tabela com `organization_id`" sozinha não as pega.
   - `audit_event` bloqueia update **e** delete. Pelo prompt ela não está em nenhuma das duas listas. Proponho manter, como trilha de auditoria; preciso da sua confirmação.

## O que posso fazer, e o que cada caminho custa

| Caminho | O que exige | Observação |
|---|---|---|
| **A. Liberação estreita e auditada no próprio trigger** | Uma migração que muda `panne_forbid_physical_delete` para aceitar o delete só quando a sessão traz uma variável própria do reset **e** o papel é o de migração (nunca o `panne_runtime`) | Mexe no schema, o que este ciclo proíbe. Mantém a proteção para todo o resto da aplicação. Eu recomendo. |
| **B. `session_replication_role = replica` dentro da transação do comando** | Superusuário (no RDS, `rds_superuser`) | É desligar trigger, o que o prompt proíbe. Desliga também FKs e RLS dessa sessão. Não recomendo. |
| **C. Organização nova para a Loja** | Recriar cadastro (pessoas, papéis, receitas, produtos) por cópia | Não é reset; muda IDs e quebra o vínculo com os códigos de acesso. |

Preciso que você escolha. Se for o A, o ciclo muda de escopo: sai o "sem mudança de schema", entra a migração e a revisão dela, e o comando `app.ops.reset_transactional` continua como o prompt descreve (dry-run, `--execute --confirm <slug>`, uma transação, classificação obrigatória, testes em base `*_test`).

## Estado

- Branch `feat/panne-032-reset` criada a partir de `d8d22fe9`, o commit publicado do CURSOR-031 (tag `panne-prod-2026-11-02`). Sem código novo; só este arquivo.
- Produção: sem nenhuma alteração. Sem snapshot, sem task definition nova, sem tag nova.
- Container `panne031_testdb` ainda de pé (local, descartável).

## Comandos executados

```
git worktree add C:\Projetos\_panne-032 -b feat/panne-032-reset panne-prod-2026-11-02
docker exec panne031_testdb psql -U postgres -d panne -At -c "<consultas ao catálogo: tabelas, colunas organization_id, triggers, corpo das funções>"
docker exec panne031_testdb psql -U postgres -d panne -c "begin; delete from inventory_movement where organization_id=(...); rollback;"
docker exec panne031_testdb psql -U postgres -d panne -c "begin; delete from inventory_balance  where organization_id=(...); rollback;"
```

Todas as consultas foram contra o banco local descartável. Nenhum comando AWS.
