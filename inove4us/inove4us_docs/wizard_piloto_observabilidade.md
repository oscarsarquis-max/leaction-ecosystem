# Wizard — Observabilidade do Piloto

Protocolo operacional para acompanhar `/api/wizard/estruturar` durante o piloto.  
**Não** introduz dashboard, alertas automáticos nem mudança de arquitetura.

Benchmark pré-lançamento: [`wizard_estruturar_benchmark.md`](./wizard_estruturar_benchmark.md) (commit `00d2eb0`).

---

## 1. Objetivo

Garantir que as métricas **já emitidas** possam ser exportadas, consolidadas e interpretadas com baixo risco:

- dados confiáveis;
- zero conteúdo sensível nos eventos canônicos de métrica;
- análise offline simples;
- baseline estável durante o piloto.

---

## 2. Baseline pré-lançamento

Referência **estática** do benchmark controlado (2026-08-11).  
**Não misturar** estes números com estatísticas de produção do piloto.

| cenário | input_tokens | output_tokens | bedrock_latency_ms |
|---------|-------------:|--------------:|-------------------:|
| curto | 1076 | 556 | 10423 |
| médio | 1454 | 552 | 7459 |
| longo | 2242 | 580 | 10846 |

Configuração congelada para interpretação:

- Sonnet 4 via AWS Bedrock
- Top N = 8
- `BEDROCK_MAX_TOKENS` = 4096
- 1 chamada no happy path
- retry opcional
- prompt caching **não** implementado

---

## 3. Métricas disponíveis

### 3.1 Evento `wizard_ai_metrics`

Emitido por tentativa Bedrock (`attempt=1` e, se houver, `attempt=2` no retry).  
Formato: linha stderr `[wizard] wizard_ai_metrics key=value ...`

| métrica | tipo | unidade | momento | significado |
|---------|------|---------|---------|-------------|
| `request_id` | string | id | cada tentativa | correlaciona com o request do wizard |
| `attempt` | int | 1..n | cada tentativa | número da chamada Bedrock |
| `retry` | bool | — | cada tentativa | `true` na 2ª chamada |
| `retry_reason` | string | flags | só se retry | motivos técnicos (`vinculo=...;vazamento=...`) — sem texto do relato |
| `system_chars` | int | chars | attempt 1 | tamanho do system prompt |
| `catalogo_chars` | int | chars | attempt 1 | tamanho do bloco de catálogo |
| `ancoras_chars` | int | chars | attempt 1 | tamanho das âncoras |
| `ancoras_count` | int | count | attempt 1 | quantidade de âncoras |
| `diretrizes_chars` | int | chars | attempt 1 | tamanho do bloco de diretrizes |
| `obrigatoria_chars` | int | chars | attempt 1 | bloco da metodologia obrigatória |
| `user_chars` | int | chars | attempt 1 | tamanho do user_content (**não** o texto) |
| `matcher_top_ids` | string | ids CSV | attempt 1 | top IDs do matcher |
| `matcher_top_scores` | string | scores CSV | attempt 1 | scores correspondentes |
| `matcher_candidate_count` | int | count | attempt 1 | candidatos enviados (= Top N ou 0 se fallback de catálogo) |
| `matcher_positive_count` | int | count | attempt 1 | metodologias com score > 0 |
| `candidate_ids` | string | ids CSV | attempt 1 | IDs candidatos no prompt |
| `full_catalog_fallback` | bool | — | attempt 1 | prompt usou catálogo completo |
| `candidate_catalog_chars` | int | chars | attempt 1 | chars só do catálogo candidato |
| `input_tokens` | int\|null | tokens | se usage vier | tokens de entrada Bedrock |
| `output_tokens` | int\|null | tokens | se usage vier | tokens de saída Bedrock |
| `total_tokens` | int\|null | tokens | se usage trouxer | total nativo do provider |
| `cache_creation_input_tokens` | int\|null | tokens | se usage trouxer | cache write (hoje tipicamente ausente) |
| `cache_read_input_tokens` | int\|null | tokens | se usage trouxer | cache hit (hoje tipicamente ausente) |
| `bedrock_latency_ms` | float | ms | cada tentativa | latência da invocação Bedrock |
| `stop_reason` | string | enum | cada tentativa | ex.: `end_turn`, `max_tokens` |
| `max_tokens_config` | int | tokens | cada tentativa | teto configurado (4096) |

### 3.2 Evento `wizard_total_metrics`

Emitido **uma vez** ao final do request (sucesso IA ou fallback).

| métrica | tipo | unidade | momento | significado |
|---------|------|---------|---------|-------------|
| `request_id` | string | id | fim do request | mesma correlação |
| `total_latency_ms` | float | ms | fim | tempo total do endpoint (monotonic) |
| `bedrock_calls` | int | count | fim | quantas invocações Bedrock neste request |
| `retry` | bool | — | fim | se houve retry |
| `fallback` | bool | — | fim | se usou fallback local |
| `total_input_tokens` | int\|null | tokens | fim | soma dos `input_tokens` das tentativas (só valores presentes) |
| `total_output_tokens` | int\|null | tokens | fim | soma dos `output_tokens` das tentativas |

### 3.3 Correlação

```
wizard_ai_metrics (attempt 1)  ──┐
wizard_ai_metrics (attempt 2?) ──┼── request_id ──▶ wizard_total_metrics
                                 │
outros logs [wizard] ...         ─┘  (mesmo request_id quando presente)
```

Não há tracing distribuído novo. O `request_id` (12 hex) basta para o piloto.

### 3.4 Métricas auxiliares (fora dos dois eventos canônicos)

Úteis, mas **não** fazem parte do payload estruturado de `wizard_*_metrics`:

| log | observação |
|-----|------------|
| `metodologia_preferida_valida=true\|false` | **hoje sem `request_id`** na maioria das linhas; o resumidor só conta preferência correlacionada se o export incluir `request_id` |
| `matcher_executado=... candidate_count=...` | diagnóstico do matcher |
| `qualidade request_id=... retry=... fallback=...` | flags de qualidade (booleanos/contagens) |

---

## 4. Privacidade dos logs

### 4.1 Eventos canônicos (`wizard_ai_metrics` / `wizard_total_metrics`)

**Não** registram:

- problema / objetivo / contexto / turma do professor;
- texto de causas, ganchos, hipóteses;
- system prompt ou user_content;
- resposta completa do modelo;
- dados pessoais.

Registram apenas métricas numéricas, IDs técnicos de metodologia e flags.

### 4.2 Achado residual (fora dos eventos canônicos)

Linha diagnóstica em `wizard_qualidade.py`:

```text
[wizard] BARREIRA_FINAL bloqueios=N amostra='...'
```

Essa linha pode conter **até ~80 caracteres de texto** (trecho associado ao bloqueio da barreira).  
**Não faz parte** de `wizard_ai_metrics` / `wizard_total_metrics`.

**Recomendação para o piloto:**

1. Ao exportar logs para análise compartilhada, filtrar **apenas** linhas `wizard_ai_metrics` e `wizard_total_metrics` (e opcionalmente flags sem texto).
2. **Não** incluir `BARREIRA_FINAL` / `amostra=` em dumps compartilhados.
3. Correção dessa linha (remover amostra do stderr) é mudança de produção — **fora desta etapa**; deve ser decisão explícita.

Esta etapa **não** mascarou silenciosamente o campo.

---

## 5. Como coletar/exportar

1. Obter logs do serviço (CloudWatch Logs / arquivo local do container).
2. Filtrar linhas contendo `wizard_ai_metrics` ou `wizard_total_metrics`.
3. Salvar em arquivo local `.jsonl` **ou** dump texto das linhas stderr.
4. Opcional: converter para JSONL com um objeto por linha (`event`, `request_id`, campos).

**Janela temporal:** os eventos de métrica **não** embutem timestamp.  
Filtre `--since` / `--until` na ferramenta de exportação (CloudWatch Insights, etc.) **antes** de rodar o resumo. O script offline não implementa `--since`/`--until`.

---

## 6. Como executar o resumo

```powershell
cd C:\Projetos\inove4us\backend

# Saída humana
python scripts/resumir_metricas_wizard.py path\to\export.jsonl

# Saída JSON
python scripts/resumir_metricas_wizard.py path\to\export.jsonl --json

# Fixture sintética (sem dados reais)
python scripts/resumir_metricas_wizard.py scripts/fixtures/wizard_pilot_metrics_sample.jsonl
```

O script:

- não acessa banco;
- não chama AWS;
- tolera linhas inválidas e campos ausentes;
- **não** trata campo ausente como zero.

---

## 7. Indicadores principais

| área | indicadores |
|------|-------------|
| Volume | requests, bedrock_calls, calls/request |
| Tokens | avg / p50 / p95 de input e output; avg total |
| Latência Bedrock | avg / p50 / p95 / p99 |
| Latência total | avg / p50 / p95 / p99 |
| Retry | count e % |
| Fallback | count e % |
| Matcher | candidate_count médio + distribuição; % `full_catalog_fallback` |
| Metodologia desejada | % preferência válida **quando** houver correlação por `request_id` |
| Stop | distribuição de `stop_reason` |

---

## 8. Como interpretar

### Sinais iniciais

- Pode analisar desde o primeiro dia.
- Uma ou poucas chamadas **não** justificam mudança estrutural.
- Compare ordens de grandeza com a baseline da seção 2, sem exigir igualdade.

### Evidência suficiente para decisão

- Padrão **consistente** ao longo de vários dias / volumes crescentes.
- Alinhamento entre métricas quantitativas **e** feedback qualitativo dos professores.
- Qualquer mudança de prompt/Top N/modelo invalida comparação direta — registre como nova versão do piloto.

Percentis usam **nearest-rank** (`index = ceil(p/100 * n) - 1`). Objetivo: simplicidade, não precisão estatística sofisticada.

---

## 9. Sinais que merecem investigação

Sem thresholds rígidos / sem SLA:

- crescimento consistente de p95 (Bedrock ou total);
- retry recorrente;
- fallback recorrente;
- `full_catalog_fallback` aparecendo com frequência;
- `output_tokens` significativamente acima da faixa observada no benchmark (~550–580);
- `candidate_count` diferente de 8 sem explicação (exceto fallback de catálogo);
- `stop_reason=max_tokens`;
- metodologia desejada frequentemente inválida/bloqueada (quando mensurável).

---

## 10. O que NÃO alterar durante o piloto

Salvo defeito funcional, **não** alterar simultaneamente:

- prompt;
- Top N;
- keywords;
- pesos do matcher;
- modelo;
- temperature;
- `max_tokens`;
- quality gate.

Motivo: precisamos de baseline estável para interpretar dados.  
Se alguma mudança for necessária, registrar como **versão do piloto** (data + motivação + o que mudou).

---

## 11. Checklist de revisão

Uso periódico (ex.: diário ou 2–3×/semana no início):

- [ ] volume de requests
- [ ] p50/p95 Bedrock
- [ ] p50/p95 total
- [ ] input tokens
- [ ] output tokens
- [ ] retry rate
- [ ] fallback rate
- [ ] full_catalog_fallback
- [ ] stop_reason
- [ ] metodologia desejada
- [ ] erros/exceções
- [ ] feedback qualitativo dos professores

### Feedback qualitativo (protocolo, sem feature nova)

Observar com os professores:

- se as 3 causas parecem pertinentes;
- se A/B/C oferecem alternativas realmente distintas;
- se a metodologia desejada é respeitada;
- se os cards parecem coerentes com o desafio;
- se o professor entende rapidamente o que escolher;
- percepção de tempo de espera.

Tokens/latência **não** medem qualidade pedagógica.

---

## Apêndice — Arquitetura (lembrete)

```
Professor → campos → normalização → matcher → Top 8 → Sonnet
→ 3 causas + A/B/C → stitch → cards → quality gate → retry opcional → resposta
```

Fallback: falha Bedrock → fallback local → catálogo completo permitido → cards.
