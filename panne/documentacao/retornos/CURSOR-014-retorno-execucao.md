# CURSOR-014 — Retorno de execução

## 1. Isolamento

Somente `panne/`. Sem MySQL, FTP, apps irmãs, Bedrock/Cognito reais, frontend, PDF/HTML/QR, estoque, custos, offline, WebSocket/SSE ou IA operacional. Sem commit, push ou deploy.

## 2. Banco e head

PostgreSQL **18.4**, banco `panne`. Head **`0012_production_api_roles`**. Runtime sem fallback administrativo (`configured_runtime_url` nunca devolve a URL admin). `panne_runtime` sem superuser, BYPASSRLS ou ownership. Rotas de produção usam `get_runtime_session`.

## 3. Múltiplos papéis

Tabela `organization_membership_role` (organização, associação, papel, concedido/revogado por e em, motivo). Papel ativo único por associação (`revoked_at IS NULL`). Atribuições 0011 copiadas sem perda. `membership.role` permanece rótulo denormalizado; a fonte de autorização é a relação muitos-para-muitos. RLS: SELECT por org ou associação do usuário atual; INSERT/UPDATE só por org.

## 4. Autorização e `/me`

Permissões unidas de todos os papéis ativos. Grupos do Cognito não autorizam. Concessão/revogação exigem `membership.role.manage`, preservam histórico, bloqueiam o último proprietário ativo e a escalada (só proprietário concede/revoga `owner`). Segunda conferência continua exigindo usuários distintos. `/api/v1/me` devolve lista de papéis e união de permissões.

## 5. Conversão

Massa↔massa com `Decimal`. Canônico: grama. Pesagem e consumo guardam quantidade/unidade informadas, quantidade/unidade canônicas, fator, origem e versão. Massa↔volume proibida. Tolerância na unidade canônica. Valores 0011 preservados como identidade (`legacy_identity`, fator 1). g→kg e kg→g cobertos. Sem float.

## 6. Política antiga

`production.order.policy_adopt` só se a ordem está `released` ou `on_hold`, sem política congelada, sem fatos de execução, com política completa e motivo. Gera hash e evento `execution.policy_adopted`. Idempotente. Sem fatos retroativos. Liberação nova continua exigindo política antes do `release`.

## 7. Decisão `scrapped`

Reservado/depreciado no catálogo da batelada. Sem comando `scrap`. Descarte = consumo `waste`, rendimento, ocorrência ou `short_closed`.

## 8. Leituras

Prefixo `/api/v1/organizations/{organization_id}/production`: planos, ordens, bateladas, materiais e etapas (planejado × realizado), dependências, eventos, pesagens, consumos, execução de etapas, rendimentos, ocorrências, emissões, rastreabilidade e quadro. Sem custos ou margens.

## 9. Comandos

Planejamento: criar/alterar/remover item, programar plano e ordem, dependência, bateladas, liberar, espera/retomar, cancelar, substituta, definir e adotar política. Execução: sessão de pesagem, ledger e conferência, consumo/retorno/desperdício/correção, máquina de etapas, rendimento, ocorrência, override, concluir, `short_closed` e emissão/reemissão. Routers só resolvem contrato, contexto e serviço.

## 10. Quadro

`GET .../production/board` é projeção dos dados operacionais. Filtros: data ou intervalo curto, estabelecimento, turno, área, produto, estado, prioridade, código/texto. Cartão: ordem/batelada, produto, quantidade e alvo, horário, estados, etapa atual, dependências/bloqueios, ocorrências abertas, atraso determinístico, próxima ação permitida e `row_version`. Sem tabela paralela e sem custos.

## 11. Rastreabilidade

`GET .../orders/{id}/traceability` exige `production.traceability.read`. Consolida ordem, bateladas, formulação/escala, hashes, materiais, pesagens, consumos, etapas, rendimentos, ocorrências, dependências, overrides, emissões e eventos. Sem fonte nova e sem custos.

## 12. Ficha

Payload canônico da emissão: emissão, ordem/batelada, produto, versões/hashes, materiais, etapas, alertas, apontamento, estado na emissão, finalidade e emissão anterior. Sem HTML, PDF ou QR. Sem consulta a cadastro vivo.

## 13. Segurança e RLS

Toda rota autenticada usa sessão runtime. RLS default deny, ENABLE+FORCE. Testes A/B com `panne_runtime` e isolamento HTTP entre organizações (recurso alheio invisível / 403). Limites de paginação e texto. Schemas `extra="forbid"`. Logs sem token. Correlação ponta a ponta.

## 14. Idempotência

`Idempotency-Key` obrigatório em comandos. Reexecução devolve o mesmo recurso. `If-Match` / `row_version` gera 409 em concorrência.

## 15. Erros e OpenAPI

`{code, message}` em português, sem SQL, token ou stack. 400 contrato, 401 autenticação, 403 autorização, 404 invisível, 409 estado/idempotência/concorrência, 422 domínio, 503 dependência. OpenAPI em `/openapi.json`; rotas fora de `/health` e `/ready` exigem HTTPBearer.

## 16. Migração

`0011_production_execution` → `0012_production_api_roles` → `0011`, reaplicação e `0001 → head` comprovados. Downgrade de 0011 remove contador `sheet` antes de restaurar o check de `kind`.

## 17. Testes

**197 passed, 1 skipped** (Bedrock ao vivo). Local 3.11.15 e **Python 3.12.14** no container. `pip-audit` limpo (panne não publicado no PyPI). Cobertos: migração, papéis, união, último proprietário, escalada, `/me`, g↔kg, massa→volume, memória original, tolerância canônica, adoção/rejeição de política, `scrapped`, authz, RLS, idempotência, ETag, paginação, quadro, planejado×realizado, rastreio, ficha, erros, OpenAPI, endpoints antigos e ausência de chamadas externas proibidas.

## 18. Endpoints antigos

`/health`, `/ready` e `/api/v1/me` preservados. `/me` passa a listar `roles` e a união de permissões.

## 19. Documentação

ADR da API, múltiplos papéis, concessão/revogação, conversão, política antiga, `scrapped`, catálogo, schemas/erros, idempotência, quadro, rastreabilidade, payload da ficha, ameaças, matriz endpoint × permissão × RLS, prompt, este retorno e `INDICE.md`.

## 20. Git e segredos

Nenhum segredo registrado. Nenhum valor de `.env` neste retorno.

## 21. Riscos

`membership.role` denormalizado ainda existe (rótulo 0009); autorização lê só papéis ativos. Não se revoga o último papel ativo da associação. Filtro de estação do quadro usa área/`public_code` (sem coluna de estação). `scrapped` continua sem comando. Interface visual permanece no CURSOR-015.

## 22. Ausência de commit, push e deploy

Nenhum commit, push ou deploy foi feito. CURSOR-015 não iniciado.
