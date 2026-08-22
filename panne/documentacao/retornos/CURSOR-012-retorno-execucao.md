# CURSOR-012 — Retorno da execução

Data: 2026-08-22. Sem commit, push, deploy ou CURSOR-013. Aguarda revisão do arquiteto.

## 1. MySQL, FTP e aplicações irmãs

Não foram abertos. Nenhuma aplicação irmã foi lida ou alterada. Somente `panne/`.

## 2. Reconciliação das questões

Tabela em `decisoes/RECONCILIACAO-CURSOR-012.md`. Prompt vence a proposta documental (havia autorização para migrar). Defaults: aprovação obrigatória; liberação por `production.order.release`; técnico sem liberação; pesagem fora; pré-fermento = dependência; mudança material = nova ordem; digital conectado; ficha só contingência documental; um papel; estoque/custo/conformidade não bloqueiam.

## 3. Documento de custos

`produto/CUSTOS-E-FORMACAO-DE-PRECOS.md`. Sem implementação. Sem `costing.read`.

## 4. Banco e head

PostgreSQL 18.4, banco `panne`. Head **`0010_production_planning`**. Runtime sem fallback administrativo (ciclo 011). `setuptools` ≥83. `pip-audit` limpo. Runtime sem superuser, propriedade ou `BYPASSRLS`.

## 5. Tabelas e constraints

`production_code_counter`, `production_plan`, `production_plan_item`, `production_order`, `production_order_dependency`, `production_batch`, `production_order_material`, `production_order_step`, `production_batch_material`, `production_event`. FKs compostas de organização; códigos únicos por org; dependência sem autorreferência; gatilhos de imutabilidade.

## 6. Estados e comandos

Plano: `draft`/`scheduled`. Ordem: `draft`/`scheduled`/`released`/`on_hold`/`cancelled` + catálogo futuro. Comandos listados em `arquitetura/ESTADOS-E-COMANDOS-0010.md`. Sem pesagem, início, consumo ou conclusão.

## 7. Liberação

Transação atômica: lock, permissão, org, produto/formulação/escala, aprovação, escala compatível, ≥1 batelada, dependências acíclicas, snapshots, alocações, hashes, evento, estado `released`. Sem IA.

## 8. Snapshots e hashes

Materiais e etapas com nome/unidade/quantidades/algoritmo. SHA-256 canônico (materiais, etapas, conjunto). Independentes do cadastro vivo para leitura.

## 9. Bateladas e precisão

Divisão `equal_share_plus_remainder`, Decimal, soma exata. Sem float.

## 10. Dependências

Tipos `preferment`/`intermediate`/`other`. Mesma org. Sem autorreferência. Ciclo indireto recusado. Imutáveis após liberação.

## 11. Concorrência e idempotência

`SELECT FOR UPDATE` + `row_version`. Contador com lock. Mesma chave e comando reaplicam; chave com payload/comando diferente falha. Liberação concorrente não duplica snapshot.

## 12. Imutabilidade

Após `released`: snapshots, produto, formulação, escala, estabelecimento, alvos e dependências congelados. Cancelamento preserva snapshot. Exclusão física bloqueada.

## 13. Permissões

Oito códigos `production.*` gravados. Owner/admin e gestor de produção administram. Técnico e viewer: leitura. Padeiro: leitura de ordem/quadro, sem gestão. Sem `costing.read`. Um papel por associação.

## 14. RLS

Novas tabelas ENABLE+FORCE, USING e WITH CHECK por organização, default deny. Troca de `organization_id` bloqueada. Testes com `panne_runtime`.

## 15. Migração

`0009 → 0010 → 0009 → 0010` e `0001 → head` cobertos. Revision ≤32 caracteres.

## 16. Testes e auditoria

171 passed, 1 skipped (3.11.15 local e 3.12.14 no container). `pip-audit`: nenhuma vulnerabilidade conhecida.

## 17. Endpoints existentes

`/health`, `/ready`, `/api/v1/me` intactos. Sem rota de produção.

## 18. Arquivos e documentação

Módulo `app/modules/production_planning/`, migração `0010`, testes, ADR, modelo físico, invariantes, eventos, numeração, divisão, custos, reconciliação, `INDICE.md`.

## 19. Segredos

Nenhum valor de `.env` neste retorno.

## 20. Git

`panne/` untracked. Rastreados pré-existentes fora do alvo.

## 21. Riscos

Um papel por associação. Pesagem e execução ainda não existem. Permissões de produção residuais se 0009 antigo tiver sido aplicado com o catálogo expandido — 0010 é idempotente no seed. Descoberta com padeiros continua aberta para o próximo recorte.

## 22. Commit, push e deploy

Não houve. CURSOR-013 não foi iniciado.
