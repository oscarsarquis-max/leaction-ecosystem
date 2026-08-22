# CURSOR-008 — Retorno da execução

Data: 2026-08-22. Sem commit, push, deploy ou CURSOR-009. Aguarda revisão do arquiteto.

## 1. MySQL legado

Não foi aberto, consultado nem modificado. Nenhuma credencial ou dado de origem foi usado.

## 2. PostgreSQL alvo (antes da `0007`)

- Mecanismo: PostgreSQL 18.4 (`leaction_db`)
- Banco lógico: `panne`
- Ambiente: local / test
- Head inicial: `0006_knowledge_grounding`
- Head atual: `0007_ai_orchestration`

## 3. Arquivos (somente `panne/`)

Criados: `0007_ai_orchestration.py`; módulo `ai_orchestration` (`gateway`, `settings`, `bedrock_adapter`, `fake_gateway`, `schema`, `prompt`, `models`, `orchestrate`, `review`, `preview`); testes `test_ai_gateway.py`, `test_ai_orchestration.py`, `test_ai_security.py`, `test_ai_bedrock_live.py`; `MODELO-DADOS-ORQUESTRACAO-IA.md`; prompt e este retorno.

Alterados: `alembic/env.py`; `tests/test_migrations.py`; `pyproject.toml` (extra `bedrock` e `python-dotenv`); `.env.example` com placeholders Bedrock, **sem** access key.

HTTP: só `/health` e `/ready`. Sem CRUD, frontend, chat, embeddings, agente autônomo, rótulo ou interpretação de conformidade.

`.env` local (gitignorado) recebeu as variáveis AWS/Bedrock necessárias nesta estação. Nenhum valor foi copiado para o repositório nem para este retorno.

## 4. Tabelas e restrições

`ai_interaction`, `ai_proposal`, `ai_proposal_item`, `ai_proposal_process_step`, `ai_proposal_citation`, `ai_proposal_review`.

Checks de tipo de interação, status, hash, tokens, tipo/status da proposta, JSONB em arrays, resolução de item, quantidade e fator positivos. Unique de sequência, uma proposta por interação e uma aceitação válida por proposta. Filhos e revisões são append-only. Exclusão física bloqueada. Conteúdo da proposta é imutável; só `status` (a partir de `draft`) e o primeiro `materialized_formulation_version_id` podem mudar.

## 5. ModelGateway

Porta `ModelGateway`: pedido estruturado (`system_prompt`, payload, schema) e resposta com JSON, provedor, `model_id`, região, tokens, `stop_reason` e latência. Erros normalizados em `GatewayError`. O domínio não importa `boto3`.

## 6. Adaptador Bedrock

`BedrockClaudeGateway` usa só `boto3.client("bedrock-runtime")` + `Converse`. Recusa endpoint `bedrock-mantle`. `FakeModelGateway` cobre todos os testes comuns. O domínio não conhece ID de modelo Claude.

## 7. Configuração AWS

Variáveis: `AWS_REGION`, `BEDROCK_REGION` (preferida), `BEDROCK_MODEL_ID`, `BEDROCK_MAX_TOKENS`, `BEDROCK_TEMPERATURE`, `BEDROCK_GUARDRAIL_ID`, `BEDROCK_GUARDRAIL_VERSION`. Guardrail é opcional; se vazio, a chamada não envia `guardrailConfig`.

Credenciais pela cadeia AWS (perfil, IAM, temporárias ou `.env` local). `.env.example` não declara `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` nem `AWS_SESSION_TOKEN`.

## 8. Structured output

Modo padrão `json_schema` via `outputConfig.textFormat`. Alternativa explícita `tool_schema`. Se `unsupported`, a chamada falha com `structured_output_unsupported`. Sem parsing de Markdown.

## 9. Construção do contexto

Objetivo sanitizado → organização e caso de uso → grounding determinístico (`recipe` / `technical` / `internal_document`, revisados; sem norma para inventar fórmula) → no máximo 8 fragmentos de 800 caracteres → tokens opacos `e1`… e blocos `<panne_evidence>` → gateway → validação → persistência só se válida → prévia determinística → espera revisão humana.

## 10. Prompt injection

System prompt versionado (`panne_formulation_proposal` v1). Fragmentos entram como dados não confiáveis. Testes cobrem “ignore as instruções”, pedido de credencial, publicação, comando e campo extra (`extra="forbid"`).

## 11. Validação de IDs e citações

ID de ingrediente fora do conjunto permitido rejeita a saída inteira. Token de citação inventado rejeita. URL solta do modelo não vira citação. Citações persistidas apontam para `knowledge_fragment` + `grounding_citation` da Panne.

## 12. Schema da proposta

Pydantic `ProposalOutput` / `ExplanationOutput` com `extra="forbid"`. Tipo, título, objetivo, aviso assistivo, itens, etapas, premissas, pendências, avisos e tokens citados. Quantidades e temperaturas com faixa.

## 13. Revisão humana

`ai_proposal_review` append-only: `accepted`, `rejected`, `revision_requested`. Aceitação exige itens `resolved` com quantidade. Revisão não reescreve o conteúdo da proposta.

## 14. Materialização em draft

Criar: nova `Formulation` + `FormulationVersion` `draft`. Adaptar: nova versão na mesma formulação; a base permanece intacta. Nunca publica nem aprova. `AuditEvent` `ai_proposal_materialized`. Segunda aceitação devolve a versão já materializada.

## 15. Tratamento de erros

Mapeados: `AccessDeniedException`, `ModelTimeoutException`, `ThrottlingException`, `ValidationException`, schema inválido, saída truncada, `grounding_insufficient`, ID/citação inventados. Retry limitado (2) só para throttling, timeout e indisponibilidade.

## 16. Upgrade, downgrade e reaplicação

`0006` → `0007` → `0006` → `0007` e `0001` → `head`. Reversível. Head final `0007_ai_orchestration`.

## 17. Testes e resultados

121 passed, 1 skipped no PostgreSQL `panne` (Python local 3.11.15 do venv desta estação). Cobertura: porta, settings sem chave no exemplo, Converse sem mantle, erros Bedrock, create/adapt, item não resolvido, ID/citação inventados, imutabilidade, isolamento de fonte, injeção e campos extras. O skip é o teste vivo.

## 18. Python 3.12

Container oficial `python:3.12-slim-bookworm` (**3.12.14**): 121 passed, 1 skipped. Mesmo banco `panne`. Env temporário só com URL do Postgres; apagado depois.

## 19. Teste vivo Bedrock

Não executado. `BEDROCK_LIVE_TEST` forçado a `0` nesta rodada. `tests/test_ai_bedrock_live.py` permanece desabilitado por padrão.

## 20. Credenciais

Nenhuma access key, secret ou session token foi gravada em arquivo versionado ou neste retorno. `.env.example` permanece com placeholders. O `.env` local está no `.gitignore`.

## 21. Sem publicação/aprovação automática

A IA só produz proposta `draft`. Materialização humana cria somente `FormulationVersion` `draft`. Nenhum fluxo publica ou aprova.

## 22. Git

`git diff --stat` (rastreados; pré-existentes, não tocados neste ciclo):

```
 infra/ecosystem-databases.sql     | 1 +
 leaction-ecosystem.code-workspace | 4 ++++
 2 files changed, 5 insertions(+)
```

`git status --short`: `M` nesses dois; `?? panne/`; lixo pré-existente intacto.

## 23. Riscos e pendências

- Sem RLS nem autenticação HTTP.
- `plainto_tsquery` em português exige todas as palavras do objetivo no fragmento; grounding insuficiente é falha controlada, não invenção.
- Guardrail local ainda sem ID/versão; a configuração está pronta.
- Teste vivo Bedrock não rodou.
- Sem endpoint, chat, embeddings ou agente autônomo.
- Conformidade, rótulo e interpretação normativa continuam fora.
- Não avançar ao CURSOR-009 sem revisão.

## 24. Commit, push e deploy

Não houve commit, push nem deploy.
