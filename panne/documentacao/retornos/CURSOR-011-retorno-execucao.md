# CURSOR-011 — Retorno da execução

Data: 2026-08-22. Sem commit, push, deploy ou CURSOR-012. Aguarda revisão do arquiteto.

## 1. Runtime e pip-audit

Não há workers (Celery/RQ/Dramatiq) na Panne. Backend: `configured_runtime_url` em `app/db_urls.py`. Placeholder ou URL vazia devolve `None` — **nunca** a URL administrativa. Papel idêntico ao admin levanta `RuntimeUrlError` e o runtime fica indisponível (503), sem usar `PANNE_DATABASE_URL`. `/me` depende de `get_runtime_session`. Alembic continua só com `settings.database_url`. `/ready` faz ping administrativo de saúde; não é fallback de negócio.

`setuptools` 79.0.1 no ciclo 010 era **PYSEC-2026-3447 = CVE-2026-59890 = GHSA-h35f-9h28-mq5c** (CVSS 6.1, *sdist* em APFS/HFS+, correção `>=83`). **Não é CVE-2025-47273**. Piso do *build-system* elevado a `setuptools>=83`. Venv local: **84.0.0**. `pip-audit` no venv e no container 3.12 (após elevar o `pip` da imagem): **nenhuma vulnerabilidade conhecida**. O `pip 25.0.1` da imagem oficial é ferramenta do *container*, não dependência da Panne, e não foi adicionado ao `pyproject.toml`.

## 2. FTP e aplicações irmãs

FTP não foi aberto. Nenhuma aplicação irmã foi lida ou alterada. Trabalho restrito a `panne/`.

## 3. MySQL somente leitura

Conexão segura **não disponível** neste processo (sem `PANNE_MYSQL` / `MYSQL_HOST` / `MYSQL_URL` / `LEGACY_MYSQL`; sem `mysqld` visível). **Credenciais não foram procuradas no computador.** Nenhuma sessão MySQL. Nenhuma linha de negócio. Nenhuma escrita. Ver `legado/DDL-PRODUCAO-LIMITACAO.md`.

## 4. Consultas estruturais

Nenhuma neste ciclo (sem sessão). Ciclos 002–004 já haviam inventariado metadados do núcleo (80 tabelas).

## 5. Estruturas do legado (já documentadas)

Núcleo: empresa, usuário, produto, ingrediente, ficha, nutrição. Periferia sem detalhe de produção (`tbl_pop*`, lançamentos, “planos”). **Nenhuma tabela de ordem, batelada, pesagem, quadro ou apontamento** nos inventários. A ficha impressa hoje deriva da `tbl_ficha_tecnica` viva + porção, não de uma ordem.

## 6. Fragilidades

Ficha viva como “ordem”; sem snapshot de emissão; sem planejado ≠ realizado; sem batelada; sem eventos append-only; custos/markups na ficha; `ID_EMPRESA` frágil; mudança posterior na receita altera o que se imprime no dia seguinte.

## 7. Estado reaproveitável da Panne

Aproveitar: org/estabelecimento, RLS, ingrediente/versão, produto técnico, formulação aprovada, motor de escala, aprovação. Estender: papéis/permissões, itens/etapas (cópia no snapshot), auditoria. Separar: trial, fornecedor/preço, nutrição/conformidade. Lacuna: plano, ordem, batelada, pesagem, ficha emitida, consumo real. **`trial` não é ordem.**

## 8. Fluxo proposto

`demanda → plano → ordem → batelada → separação/pesagem → execução → apontamentos → conclusão → projeções`. Atores, comandos e evidências em `produto/FLUXO-CHAO-DE-FABRICA.md`.

## 9. Modelo conceitual

`ProductionPlan`, `ProductionPlanItem`, `ProductionOrder`, `ProductionBatch`, snapshots de formulação e escala, materiais planejados, conferência, etapas, execução, consumo real, rendimento, ocorrência, evento, emissão, recurso mínimo. Sem estoque/custos/manutenção completos. Detalhe em `arquitetura/MODELO-CONCEITUAL-PRODUCAO.md`.

## 10. Máquinas de estados

Quatro máquinas. Ordem: `draft` → `scheduled` → `released` → `in_weighing` → `ready` → `in_progress` → `completed` | `short_closed` | `cancelled`; `on_hold` com motivo. Nomes candidatos `planned`/`partially_completed`/`weighing` foram revisados. Ver `arquitetura/ESTADOS-PRODUCAO.md`.

## 11. Comandos e eventos

Comando autenticado / evento append-only. IA não comanda. Escala pelo motor existente. Quadro e relatórios só leem. `arquitetura/COMANDOS-E-EVENTOS-PRODUCAO.md`.

## 12. Quadro digital

Projeção do recorte. Filtros: data, turno, estabelecimento, estação, produto, estado, prioridade. Sem custos. Bege/grafite, navegação horizontal, desktop/tablet, tela cheia futura por estação.

## 13. Ficha impressa

Projeção da **ordem** (e batelada). Conteúdo mínimo, campos de apontamento, emissão numerada + hash. QR opcional. Cancelada = emissão recusada. Digital e papel com os mesmos códigos.

## 14. Relatórios

Projeções (operacional / gerencial / auditoria). Sem cadastro paralelo. Sem ranking individual de padeiro.

## 15. Fronteira com custos

Custos lerão snapshot, consumo, preço vigente no domínio de custo, tempos, equipamento, rendimento, perda, descarte, retrabalho, vendável. Markup e margem fora do chão.

## 16. Permissões e RLS

Códigos propostos (`production.board.read`, `…release`, `…run`, consumo, yield, ocorrência, concluir, cancelar, reabrir, emitir, rastreio, `costing.read`). Esquema de papéis **não alterado**. Um papel por associação é limitação conhecida. Tabelas futuras: organizacionais, ENABLE+FORCE, default deny.

## 17. Contingência e offline

Ficha impressa já é a contingência oficial. Offline digital não foi escolhido. Comparativo em `produto/CONTINGENCIA-E-OFFLINE.md`.

## 18. Questões abertas

Doze questões priorizadas (papel único, co-liberação técnica, pesagem obrigatória, pré-fermento, etc.) em `produto/QUESTOES-CHAO-DE-FABRICA.md`. Prioridade 1 bloqueia implementação.

## 19. Proposta CURSOR-012

Documento apenas: `prompts/CURSOR-012-proposta.md`. Fechar P1; especificar DDL em documento; sem migrar sem descoberta; sem quadro/CRUD/custos. **Não executado.**

## 20. Testes, Python, PostgreSQL e head

- Venv local **3.11.15**: 154 passed, 1 skipped.
- Container `python:3.12-slim-bookworm` (**3.12.14**): 154 passed, 1 skipped.
- PostgreSQL **18.4**, banco `panne`.
- Head Alembic: **`0009_identity_authorization_rls`** (sem `0010`).
- `/health`, `/ready`, `/api/v1/me` verdes com fakes.
- Sem alteração de schema. Sem segredos neste retorno.

## 21. Git

`panne/` permanece untracked. Rastreados pré-existentes (`infra/ecosystem-databases.sql`, `leaction-ecosystem.code-workspace`) não foram o alvo deste ciclo. Ver `git status --short` / `git diff --stat` anexos na mensagem ao arquiteto.

## 22. Commit, push e deploy

Não houve commit, push nem deploy. CURSOR-012 não foi iniciado.
