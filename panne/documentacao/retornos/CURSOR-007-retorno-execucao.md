# CURSOR-007 — Retorno da execução

Data: 2026-08-22. Sem commit, push, deploy ou CURSOR-008. Aguarda revisão do arquiteto.

## 1. MySQL legado

Não foi aberto, consultado nem modificado. Nenhuma credencial ou dado de origem foi usado.

## 2. PostgreSQL alvo (antes da `0006`)

- Mecanismo: PostgreSQL 18.4 (`leaction_db`)
- Banco lógico: `panne`
- Ambiente: local / test
- Head inicial: `0005_nutrition_calculation`
- Head atual: `0006_knowledge_grounding`

## 3. Arquivos (somente `panne/`)

Criados: `0006_knowledge_grounding.py`; `knowledge_grounding` (`models`, `rules`, `ingest`, `retrieval`); testes `test_knowledge_sources.py`, `test_knowledge_retrieval.py`, `test_nutrition_profiles.py`, `test_ingredient_loq.py`; `MODELO-DADOS-CONHECIMENTO-E-GROUNDING.md`; prompt e este retorno.

Alterados: `alembic/env.py`; modelos de `ingredient_catalog` e `nutrition_calculation`; `calculation_engine/nutrition.py`; `tests/helpers.py`; `tests/test_migrations.py`; docs de ingredientes, nutrição, fronteiras e proposta.

HTTP: só `/health` e `/ready`. Sem CRUD, frontend, chat, crawler, rótulo ou seed regulatório.

## 4. Tabelas e restrições

`knowledge_source`, `knowledge_source_version`, `knowledge_fragment`, `knowledge_tag`, `knowledge_source_tag`, `grounding_query`, `grounding_result`, `grounding_citation`, `nutrition_expectation_profile`, `nutrition_expectation_profile_item`.

Checks de tipo, autoridade, privacidade, norma oficial (órgão + jurisdição), receita ≠ norma oficial, vigência, hash, LOQ e propósitos do perfil. Unique de sequência, rank, tag e nutriente no perfil. Fragmentos, queries, resultados, citações e itens de perfil são append-only. Exclusão física bloqueada. Versão só admite revisão (`pending` → `reviewed`/`rejected`) ou `superseded`/`revoked`.

`ingredient_nutrient` ganhou `value_status`, `limit_of_quantification`, `loq_unit_id` e `method_or_source`. `nutrition_calculation.expectation_profile_id` é opcional.

## 5. Autoridade e confiança

`official` > `curated` > `user_provided` > `unverified`. Norma oficial exige emissor e jurisdição. Global nasce `restricted` e só entra na busca depois de `released`. `unverified` não gera conclusão normativa. Tags não substituem vigência nem autoridade. IA futura não é fonte primária.

## 6. Versionamento e vigência

Versões imutáveis no conteúdo. Hash SHA-256 obrigatório quando há conteúdo; hash diferente cria nova versão; hash igual reutiliza. `retrieved_at` não infere vigência. A janela é `effective_from` / `effective_until`. Revogada ou substituída permanece para história.

## 7. Fragmentação e localizadores

Unidade citável com sequência, localizador (`page`, `section`, `article`, `clause`, `annex`, `paragraph`, `block`, `url_fragment`), hash próprio e `search_vector` português + `unaccent`. Sem fragmento sem versão.

## 8. Algoritmo de recuperação

`deterministic_pg_fts_pt` v1. Filtros: texto, organização, tipo, autoridade, jurisdição, data, estado, revisão e tags. Ordem: filtros → `ts_rank_cd` → autoridade → estado/vigência → revisão → `fragment.id`. Score técnico, sem probabilidade. Consulta vazia não inventa evidência.

## 9. Fontes normativas

Padrão: oficial, revisada, `in_force`, jurisdição informada e data dentro da vigência. Consulta pública e histórico só com opção explícita. Ingestão normativa fica `pending`. Sem seed de RDC 429/2020, IN 75/2020, RDC 727/2022 ou Q&A — só referência documental.

## 10. Citações

`grounding_citation` congela título, versão, emissor, URL, localizador, hashes e data de acesso. Reconstruível se a identidade da fonte mudar. Sem conclusão normativa.

## 11. Isolamento

Fonte privada só na organização dona. Global restrita invisível. Fragmento de outra organização rejeitado na persistência.

## 12. Perfis nutricionais

Propósitos `technical`, `regulatory_candidate`, `custom`. Cálculo aceita perfil opcional. Esperado e ausente — inclusive em todos os ingredientes — vira `missing_data`. Snapshot antigo sem perfil permanece intacto. Sem seed regulatório e sem propósito `regulatory`.

## 13. LOQ

`measured` e `known_zero` contribuem. `below_loq` não vira zero (`below_quantification_limit`). `not_detected` e `unknown` são `missing_data`. Combinações inválidas recusadas no banco. Sem arredondamento regulatório.

## 14. Ingestão

Porta local: validar tipo/tamanho (256 KiB, `text/plain` ou `text/markdown`) → hash → fonte → versão → segmentação por parágrafo → localizadores → FTS → revisão pendente se normativa. Receita exige citação, resumo ou estrutura extraída. Sem crawler e sem endpoint.

## 15. Upgrade, downgrade e reaplicação

`0005` → `0006` → `0005` → `0006` e `0001` → `head`. Reversível. Head final `0006_knowledge_grounding`.

## 16. Testes e resultados

106 passed no PostgreSQL `panne` (Python local 3.11.15 do venv desta estação). Cobertura: migração, fontes, fragmentos, FTS com acentuação, recuperação, citações, isolamento, perfis e LOQ.

## 17. Python 3.12

Container oficial `python:3.12-slim-bookworm` (**3.12.14**): 106 passed. Mesmo banco `panne`.

## 18. Ausência de LLM

Sem OpenAI, Anthropic, Bedrock, Claude, embeddings ou chat. Recuperação só com SQL determinístico.

## 19. Git

`git diff --stat` (rastreados; pré-existentes, não tocados neste ciclo):

```
 infra/ecosystem-databases.sql     | 1 +
 leaction-ecosystem.code-workspace | 4 ++++
 2 files changed, 5 insertions(+)
```

`git status --short`: `M` nesses dois; `?? panne/`; lixo pré-existente intacto.

## 20. Riscos e pendências

- Sem RLS nem autenticação HTTP.
- Liberação global ainda é ato explícito de domínio, sem fluxo de produto.
- FTS português depende de `unaccent` + configuração `portuguese`.
- Embeddings, Bedrock e Claude continuam fora.
- Conformidade, rótulo e interpretação normativa continuam fora.
- Não avançar ao CURSOR-008 sem revisão.

## 21. Credenciais

Nenhuma senha, token ou URL com segredo foi gravada em arquivo da Panne. `.env.example` permanece com placeholders. O env temporário do teste 3.12 foi apagado.

## 22. Commit, push e deploy

Não houve commit, push nem deploy.
