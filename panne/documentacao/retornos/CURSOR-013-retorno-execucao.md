# CURSOR-013 — Retorno de execução

## 1. Isolamento

Somente `panne/`. Sem MySQL, FTP, apps irmãs, Bedrock/Cognito reais, commit, push ou deploy.

## 2. Banco e head

PostgreSQL **18.4**, banco `panne`. Head **`0011_production_execution`**. Runtime sem fallback administrativo. `panne_runtime` sem superuser/BYPASSRLS/ownership.

## 3. Tabelas

`production_execution_policy`, `production_weighing_session`, `production_weighing_entry`, `production_weighing_verification`, `production_material_consumption`, `production_step_execution`, `production_step_execution_event`, `production_yield_measurement`, `production_occurrence`, `production_occurrence_event`, `production_dependency_override`, `production_sheet_issue`.

## 4. Política

Snapshot por ordem, definida antes da liberação, congelada e hasheada em `release_order`. Sem backfill de pesagem.

## 5. Pesagem e conferência

Uma sessão aberta por batelada. Ledger append-only. Conferência em segunda pessoa sem autoconferência. Rejeição exige correção.

## 6. Consumo

Ledger separado. Pesado ≠ consumido. Sem baixa de estoque.

## 7. Etapas

Estado atual + histórico. Sequência respeitada. Parâmetros planejados intocados.

## 8. Dependências

`preferment`/`intermediate`: predecessor `completed`, ou `short_closed` com override auditável. Cancelado bloqueia.

## 9. Rendimento

Medições append-only; projeção `deterministic_yield` / `1`. Sem preço.

## 10. Ocorrências

Categorias e bloqueio conforme o contrato. Resolução por novo evento.

## 11. Conclusão e short_closed

`completed` determinístico e autorizado. `short_closed` distinto, com motivo e permissão.

## 12. Emissão e hashes

Número sequencial, payload canônico, SHA-256, reemissão, bloqueio após cancelamento. Sem PDF/HTML.

## 13. Eventos e concorrência

Schemas fechados, idempotência, `row_version`/`FOR UPDATE`. Dois operadores não concluem a mesma etapa.

## 14. Permissões

Onze códigos novos. Padeiro opera; gestor conclui/encerra/emite; técnico lê. Sem custos. Um papel por associação documentado.

## 15. RLS

ENABLE+FORCE, default deny, `USING`/`WITH CHECK`, FK composta, teste A/B com `panne_runtime`.

## 16. Migração

`0010 → 0011 → 0010`, reaplicação e `0001 → head` cobertos.

## 17. Testes

185 passed, 1 skipped (3.11.15 local e **3.12.14** no container). `pip-audit` limpo.

## 18. Endpoints

`/health`, `/ready`, `/api/v1/me` intactos. Sem rota de produção.

## 19. Documentação

ADR, modelo 0011, política, ledgers, máquinas, eventos, conclusão, ocorrências, rendimento, ficha, permissões, RLS, fronteiras, questões, prompt e este retorno. `INDICE.md` atualizado.

## 20. Git e segredos

Nenhum segredo registrado. Nenhum valor de `.env` neste retorno.

## 21. Riscos

Ordens 0010 sem política não executam. Um papel impede modelar conferente distinto. `scrapped` sem comando. Sem conversão g↔kg.

## 22. Ausência de commit, push e deploy

Nenhum commit, push ou deploy foi feito. CURSOR-014 não iniciado.
