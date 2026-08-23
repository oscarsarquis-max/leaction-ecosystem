# CURSOR-019 — Retorno

Assistente guiado de criação e adaptação de receitas, sobre o CURSOR-018 não versionado. Sem commit, push ou deploy.

## 1. Preservação do CURSOR-018

HEAD de partida `3d14c01145547a45ba403f55aac2450762235a38`. Nenhuma restauração, descarte ou sobrescrita do 018. `0015`, `recipe_http`, Receitas, ficha, permissões e evidências 018 permanecem no working tree.

## 2. Fechamento das condições técnicas

Suíte oficial no container `python:3.12-slim-bookworm` (**3.12.14**), Postgres `panne` em `host.docker.internal:5434`: **215 passed, 1 skipped** (`test_ai_bedrock_live`, Bedrock vivo off). Cobertura de criação, versões, componentes, percentual do padeiro, escala, trials, aprovação, nutrição, ficha, RLS, idempotência e concorrência permanece na regressão 018. `test_migrations` prova `0014↔0015`, `0015↔0016` e `0001→head`. `0015` não abre classe nova de ruído Alembic; `0016` usa índice único, não `UniqueConstraint`. Frontend: 45 de regressão + 10 do assistente = **55 passed**, typecheck, lint e build.

## 3. Referências por versão

`formulation_version_recipe_reference` com snapshot, localizador, hash, versão da fonte e data de acesso. Identidade (`formulation_recipe_reference`) permanece para vínculos gerais. Ficha e auditoria leem a versão. Publicada não recebe vínculo novo. Edição posterior da identidade não reescreve o snapshot.

## 4. Auditoria da IA

Reuso de `ModelGateway`, `BedrockClaudeGateway`, `FakeModelGateway`, Converse, schema estrito, `run_proposal`, grounding e revisão. Sem segundo gateway, orquestrador ou grounding.

## 5. Migração

`0016_recipe_ai_assistant` sobre `0015`. Cria referências por versão, estende `ai_proposal`, adiciona `ai_proposal_change`, estados, guardas de imutabilidade, RLS e as três permissões. Reversível.

## 6. Modelo e estados

Proposta persistente com intent, restrições, perfil de recuperação, hashes, Guardrail, citações, decisões humanas e rascunho materializado. Estados reconciliados: solicitado, buscando evidências, grounding insuficiente, gerando, validação falhou, aguardando revisão/`draft`, aceito, rejeitado, materializado, cancelado.

## 7. Permissões e RLS

`recipe.ai.propose`, `recipe.ai.review`, `recipe.ai.materialize`. Sem Cognito groups e sem `legacy_role_label`. Padeiro e viewer não geram nem materializam. Propostas de A invisíveis para B. Fontes privadas isoladas.

## 8. Entrada guiada

Formulário criar/adaptar: objetivo, tipo, rendimento, características, obrigatórios/proibidos, alergênicos a evitar sem promessa de ausência, limites, jurisdição e observações. Sem chat livre.

## 9. Grounding

Filtro por organização, privacidade, tipo, autoridade, jurisdição, vigência, revisão e estado. Fonte é dado, não instrução. Sem web ou crawler. Falha persistida como `grounding_insufficient`.

## 10. Guardrails

Dez camadas, do input ao aceite humano. Produção sem Guardrail falha fechado. Fake explícito só em dev/teste.

## 11. Schema

Título, resumo, justificativa, componentes com IDs permitidos, massa, etapas, hipóteses, alertas, lacunas e citações. Modelo não é autoridade para bruto, percentual, escala ou nutrição.

## 12. Criação

Materialização atômica de produto, formulação e versão 1 em rascunho, com evidências na versão. Ingrediente inexistente não é criado.

## 13. Adaptação

Snapshot da base, diff, nova versão em rascunho. Base preservada.

## 14. Revisão

Comparação, citações, filtros, aceite/rejeição individual e em conjunto com confirmação, comentário, rejeição integral. Edição posterior é no rascunho.

## 15. Materialização

Somente rascunho. Proposta já materializada devolve 409. Auditoria registra `published/approved/ingredient_created/compliance_declared/production_commanded = false`.

## 16. Interface

Assistente, criar, adaptar, histórico, detalhe, grounding, comparação, revisão e resultado, com mentoria de 10 passos. Oficina + Atelier. Selo **Assistido por IA**.

## 17. Limites

Fragmentos, tamanho, tokens, timeout, retries, concorrência, modelos, temperatura e versão do prompt via `limits.py` / env, sem segredos e sem cobrança.

## 18. Segurança

RLS, isolamento, credenciais AWS fora do Git, token OIDC em memória, sem prompt completo em log comum, sem HTML cru, limpeza ao trocar organização.

## 19. Testes backend no Python 3.12

215 passed, 1 skipped. Inclui 0015/0016, referências, RLS, grounding, injection, schema, fake, Guardrail, criar/adaptar, revisão, rascunho, imutabilidade, idempotência, concorrência, timeout mapeado e nutrição. `pip-audit`: sem achado nas dependências da Panne; avisos só do `pip` 25.0.1 da imagem oficial.

## 20. Testes frontend

55 passed (45 de regressão + 10 do assistente), typecheck, lint, build. Sem chamada externa nos testes comuns.

## 21. Evidências

`documentacao/evidencias/cursor-019/` — HTML fake + PNG desktop, notebook e tablets.

## 22. Documentação

Índice, assistente, referências por versão, evidências, limitações e este retorno.

## 23. Git, segredos e riscos

Working tree local. Sem `.env` nem credenciais AWS. Risco residual: Bedrock vivo continua opt-in; Guardrail ausente em produção falha fechado.

## 24. Ausência de commit, push e deploy

Nenhum commit, push ou deploy neste ciclo.

## 25. Limites da IA

A IA não publicou, não aprovou, não criou ingrediente, não declarou conformidade e não comandou produção.
