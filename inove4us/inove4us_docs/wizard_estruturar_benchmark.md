# Wizard Estruturar — Benchmark Pré-Lançamento

Documento de consolidação técnica do pipeline `/api/wizard/estruturar` após as etapas 1–10.  
**Escopo desta etapa:** diagnóstico, benchmark e documentação. Nenhuma otimização nova.

Data da medição final: **2026-08-11**.  
Modelo: `us.anthropic.claude-sonnet-4-20250514-v1:0`.  
`BEDROCK_MAX_TOKENS`: **4096** (teto; não representa consumo real).

---

## 1. Objetivo

Fotografar o estado atual do wizard com números reais (Bedrock), comparar com a baseline original medida na instrumentação (Etapa 5), validar qualidade/resiliência/metodologia desejada e registrar o que acompanhar em produção — sem alterar o comportamento do pipeline.

---

## 2. Arquitetura atual

```
Professor
↓
campos estruturados
↓
normalização
↓
keyword matcher local
↓
Top 8 candidatas
↓
Sonnet 1 chamada
↓
3 causas + A/B/C
↓
stitch
↓
cards determinísticos
↓
quality gate
↓
retry opcional
↓
resposta ao professor
```

**Metodologia desejada (quando válida):**

```
professor escolhe metodologia
↓
entra obrigatoriamente nos candidatos
↓
backend garante A
```

**Falha Bedrock:**

```
fallback local
↓
catálogo completo permitido
↓
cards continuam funcionando
```

Volume enviado ao modelo:

| Camada | Metodologias |
|--------|----------------|
| Sonnet (caminho feliz) | normalmente **8** (Top N do matcher) |
| Fallback local | catálogo completo permitido (**39** no Dia a Dia) |
| Baseline original | Sonnet recebia **39** |

---

## 3. Baseline original

Medida na Etapa 5 (antes das compactações / Top 8), mesmos cenários curto/médio/longo.

| cenário | input_tokens | output_tokens | latency (Bedrock ms) |
|---------|-------------:|--------------:|---------------------:|
| curto | 2197 | 1148 | 14522 |
| médio | 2548 | 1305 | 24415 |
| longo | 3343 | 1356 | 18362 |

Prompt original (referência Etapa 5):

| componente | chars |
|------------|------:|
| system | 5577 |
| catálogo | 2273 |

`json_chars` original **não** foi registrado de forma confiável na Etapa 5 — não inventado aqui.

---

## 4. Estado atual

Medição real Bedrock via `backend/scripts/diagnosticar_wizard_prompt.py --invoke-bedrock --analyze-output` (2026-08-11).

**Nota de latência:** o script mede **`bedrock_latency_ms`** (invocação Bedrock).  
**Não** mede `total_endpoint_latency_ms` do Flask/ALB nesta corrida.

| cenário | input_tokens | output_tokens | total (in+out) | bedrock_latency_ms | stop_reason | system_chars | catalogo_chars | user_chars | candidate_count | json_chars |
|---------|-------------:|--------------:|---------------:|-------------------:|-------------|-------------:|---------------:|-----------:|----------------:|-----------:|
| curto | 1076 | 556 | 1632 | 10423.3 | end_turn | 2662 | 474 | 197 | 8 | 1586 |
| médio | 1454 | 552 | 2006 | 7459.4 | end_turn | 2710 | 522 | 1359 | 8 | 1545 |
| longo | 2242 | 580 | 2822 | 10845.7 | end_turn | 2730 | 542 | 3997 | 8 | 1678 |

`full_catalog_fallback`: false nos três cenários.  
`metodologia_desejada_id`: nenhuma (cenários de performance).

---

## 5. Comparação de performance

| cenário | input original | input atual | redução | output original | output atual | redução | latency original | latency atual | redução |
|---------|---------------:|------------:|--------:|----------------:|-------------:|--------:|-----------------:|--------------:|--------:|
| curto | 2197 | 1076 | −1121 (−51,0%) | 1148 | 556 | −592 (−51,6%) | 14522 | 10423 | −4099 (−28,2%) |
| médio | 2548 | 1454 | −1094 (−42,9%) | 1305 | 552 | −753 (−57,7%) | 24415 | 7459 | −16956 (−69,4%) |
| longo | 3343 | 2242 | −1101 (−32,9%) | 1356 | 580 | −776 (−57,2%) | 18362 | 10846 | −7516 (−40,9%) |

### Total tokens (input + output)

| cenário | original | atual | redução abs. | redução % |
|---------|---------:|------:|-------------:|----------:|
| curto | 3345 | 1632 | −1713 | −51,2% |
| médio | 3853 | 2006 | −1847 | −47,9% |
| longo | 4699 | 2822 | −1877 | −39,9% |

Latência Bedrock varia entre corridas (rede/quota/modelo). Os números desta tabela são a fotografia da corrida de consolidação; a tendência vs baseline permanece claramente favorável.

### System / catálogo

| componente | original | atual (curto / médio / longo) | redução (curto) |
|------------|---------:|-------------------------------:|----------------:|
| system_chars | 5577 | 2662 / 2710 / 2730 | −52,3% |
| catalogo_chars | 2273 | 474 / 522 / 542 | −79,1% |
| metodologias no Sonnet | 39 | 8 / 8 / 8 | — |

### BEDROCK_MAX_TOKENS

- Valor: **4096**
- É **teto** de saída, não consumo real
- Nenhuma resposta atual chega perto do limite (output ≈ 550–580 tokens)
- **Não alterar** antes de dados de produção

---

## 6. Qualidade

Heurística existente do diagnóstico (sem score novo). Três cenários Bedrock:

| critério | curto | médio | longo |
|----------|:-----:|:-----:|:-----:|
| JSON válido | ok | ok | ok |
| exatamente 3 causas | ok | ok | ok |
| A/B/C | ok | ok | ok |
| IDs válidos / distintos | ok | ok | ok |
| IDs ∈ candidatos | ok | ok | ok |
| famílias distintas | ok | ok | ok |
| 1 frase (causa/gancho/hipótese) | ok | ok | ok |

Médias de chars (corrida atual): trecho ≈ 68 · causa ≈ 133 · gancho ≈ 102 · hipótese ≈ 146.  
Sem mini-planos no contrato JSON; respostas passaram nos flags de concisão da heurística.  
Textos completos do modelo **não** são reproduzidos neste documento.

---

## 7. Resiliência

### Fallback (mock / teste, sem falha real AWS)

- `test_wizard_metodologia_desejada.py`: `_fallback_payload` com preferência válida → A = metodologia desejada; B/C alternativas; 3 IDs distintos
- Fallback sem preferência ainda gera 3 caminhos
- Cards/plano determinísticos continuam sendo produzidos (ex.: 5 cards no smoke EduScrum)
- Fallback usa catálogo completo permitido (não Top 8)

### Retry (mock / teste)

- `test_wizard_retry_contract.py`: duas invocações mockadas reutilizam o **mesmo** `system_prompt` (mesmos candidatos)
- `_sum_optional_ints` agrega input/output das tentativas (contrato de `wizard_total_metrics`)
- Contrato JSON permanece parseável
- Retry real Bedrock **não** foi forçado nesta etapa

---

## 8. Metodologia desejada

Cenário funcional (fora da média de performance):

| verificação | resultado |
|-------------|-----------|
| ID válido entra nos candidatos Top 8 | ok (`preferred_injected`) |
| stitch força slot A | ok (`test_wizard_metodologia_desejada`) |
| B/C permanecem alternativas | ok |
| cards/nome de A coerentes | ok |
| inválida / bloqueada: degrada sem forçar | ok |
| fallback respeita preferência válida | ok |

---

## 9. Matcher / Top 8

- Matcher lexical local ranqueia o catálogo
- `MATCHER_CANDIDATE_TOP_N = 8` (env `WIZARD_MATCHER_TOP_N`)
- Preferida injetada quando válida
- `exclude_ids` respeitado
- Falha do matcher → `full_catalog_fallback` (catálogo completo no prompt)
- Fallback local **sempre** tem catálogo completo permitido
- Retry **não** recalcula candidatos

---

## 10. Prompt caching

Conclusão da Etapa 08 (não reaberta):

> Prompt caching tecnicamente suportado, porém pouco útil na estrutura atual.

Motivos resumidos:

- mínimo 1024 tokens por checkpoint
- prefixo global estável insuficiente
- Top 8 e blocos dinâmicos reduzem hits
- não vale aumentar o prompt artificialmente

`cache_control` **não** está em produção.

---

## 11. Observabilidade

Métricas já emitidas nos logs (`wizard_ai_metrics` / `wizard_total_metrics` e correlatos):

- `input_tokens`, `output_tokens`, `total_tokens` (quando o provider envia)
- `bedrock_latency_ms`, `total_latency_ms`
- `retry` / `retry_reason`, `fallback`
- `candidate_count`, `candidate_ids`, `full_catalog_fallback`
- `metodologia_preferida_valida` (via logs de contexto)
- matcher: top ids/scores, `positive_count`, origins/coverage
- `stop_reason`, `max_tokens_config`
- decomposição de chars: system / catálogo / âncoras / user / `candidate_catalog_chars`

### Indicadores derivados recomendados (somente documentação)

- média, p50, p95, p99 de latência (Bedrock e total)
- média de input/output tokens
- percentual de retry
- percentual de fallback
- frequência de `full_catalog_fallback`
- taxa de metodologia desejada inválida/bloqueada

### Sinais para investigação futura (não são SLA)

- `output_tokens` subindo de forma consistente acima da faixa atual (~550–580)
- retry aumentando
- fallback recorrente
- latência p95 crescendo
- grande frequência de `full_catalog_fallback`
- metodologia desejada inválida/bloqueada com frequência

Nenhum dashboard/alerta foi implementado nesta etapa.

---

## 12. Commits das otimizações

Validados no histórico atual do monorepo:

| commit | resumo |
|--------|--------|
| `dcdf197` | Etapa 1 — contexto seguro / user_content semântico |
| `4574120` | Etapa 2 — campos opcionais estruturados |
| `948880c` | Etapa 3 — metodologia desejada → slot A |
| `eafbd0f` | Etapa 4 — matcher lexical (diagnóstico) |
| `05a0f63` | Etapa 5 — instrumentação Bedrock/prompt |
| `a882944` | Etapa 6 — prompt/catálogo compactos |
| `b71567b` | Etapa 7 — Top 8 candidatos ao Sonnet |
| `a3b5a9f` | Etapa 8 — diagnóstico de prompt caching |
| `468d854` | Etapa 9 — diagnóstico de verbosidade do output |
| `9054351` | Etapa 10 — compactação proporcional do output |

### Histórico breve das etapas

1. **Contexto** — evitar vazamento/contexto inseguro; efeito: user_content semântico confiável  
2. **Entrada estruturada** — campos opcionais do professor; efeito: prompt mais preciso  
3. **Metodologia desejada** — preferência → A; efeito: escolha do professor respeitada  
4. **Keyword matcher** — ranking lexical local; efeito: base para Top N  
5. **Instrumentação** — tokens/latência/chars; efeito: baseline mensurável  
6. **Prompt compacto** — system/catálogo menores; efeito: menos input  
7. **Top 8** — Sonnet vê 8 IDs; efeito: grande queda de catálogo/input  
8. **Caching** — análise only; efeito: decisão de **não** adotar agora  
9. **Análise do output** — mapa de verbosidade; efeito: alvos de faixa  
10. **Compactação do output** — regras de faixa no prompt; efeito: menos output/latência  

---

## 13. Pontos a acompanhar em produção

1. Distribuição real de `input_tokens` / `output_tokens` / `bedrock_latency_ms` (média + p95)  
2. Taxa de `retry` e de `fallback`  
3. Frequência de `full_catalog_fallback` e scores do matcher  
4. Uso e validade de `metodologia_desejada_id`  
5. `stop_reason` e proximidade (ou não) de `max_tokens=4096`  

Não propor nova refatoração neste documento; consolidar evidências do piloto primeiro.
