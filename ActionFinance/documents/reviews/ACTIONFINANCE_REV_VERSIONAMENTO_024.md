# ACTIONFINANCE_REV_VERSIONAMENTO_024

Identificador: ACTIONFINANCE_REV_VERSIONAMENTO_024. Data: 09/10/2026. Prompt: [ACTIONFINANCE_PROMPT_VERSIONAMENTO_024](../prompts/ACTIONFINANCE_PROMPT_VERSIONAMENTO_024.md). Baseline: AF-BL-023 1.0. Produto publicado: **0.1.0**. Schema: última inspect pública **V19** (05/10/2026). Este review não publica produto, não migra e não encerra 019/020/021.

## 1. Caminhos

| Registro | Caminho |
|---|---|
| Prompt 023 (origem, não reescrito) | `documents/prompts/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023.md` |
| Cópia imutável 1.0 | `documents/versioning/baselines/AF-BL-023/1.0/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023.md` |
| Ficha da baseline | `documents/versioning/AF-BL-023.md` |
| Índice | `documents/versioning/INDEX.md` |
| Changelog | `documents/versioning/CHANGELOG.md` |
| Modelo de manifesto | `documents/versioning/manifests/TEMPLATE.md` |
| Exemplo preenchido (só fatos) | `documents/versioning/manifests/AF-0.1.0-published-at-bl023-adoption.md` |
| Disciplina | `documents/versioning/README.md` |
| Projeto 023 (não é o texto do prompt) | `documents/architecture/ACTIONFINANCE_PROJETO_TESOURARIA_MP_023.md` |

## 2. Identificação inicial adotada

| Eixo | Valor | Evidência |
|---|---|---|
| Baseline | AF-BL-023 revisão **1.0** | Decisão do proprietário 09/10/2026; SHA-256 `775B9CBD467B5F073FD73A3B01943D5A02E3BF0589B9EE2553B1D0662E20D073` |
| Produto atual | **0.1.0** | `pom.xml`, `package.json`, `actionfinance.app.version`, `GET /api/v1/system/info` público em 09/10/2026 |
| Banco | Flyway sequencial; origin **V19** na última inspect | REV_017 (05/10); **não** relido agora |
| Implantação | SPA `index-BYEiixeg.js`; task/digest **não** relidos na AWS | HTTP 200 do host |

`0.1.0` não foi inventado neste pedido: já era a versão da fundação. Não promover a 1.0.

Diagnóstico já expõe `version`. Identificação de **build** (git SHA / digest) **não** está em `SystemInfo`. Preparar para a **próxima** release funcional; 024 não exige deploy só para isso.

## 3. Estado efetivo em 09/10/2026

Conferido agora:

```json
{"name":"ActionFinance","version":"0.1.0","stage":"FOUNDATION","financialOperationsAvailable":true,"spiderIntegrationStatus":"RECEIPT_SYNC","demoEnvironment":false,"accessMode":"OIDC","homologIntegration":false,"receiptSyncEnabled":true,"spiderMonitorBaseUrl":"https://monitor.spider.actionhub.com.br"}
```

SPA: `index-BYEiixeg.js`.

Não comprovado neste ciclo: task definition corrente, digest ECS corrente, Flyway do RDS, sessão autenticada, Monitor da sincronização real, collector MP.

Limite histórico: não há tag `af-v0.1.0` no Git ligada de forma reproduzível ao deploy. Não foi criada retroativamente.

## 4. Pendências ligadas à baseline (abertas)

| Item | Estado |
|---|---|
| 019 integridade de recebimentos | Código local + V20; prova pública do ID completo **aberta** |
| 020 rastreabilidade / Monitor | RAM 24h/2000; prova pública **aberta** |
| 021 captura de recebimentos | Autorização vigente; não concluída |
| Tesouraria 023 | Projeto escrito; **não** implementada |

Nenhuma marcada concluída.

## 5. Próxima versão candidata

**Não definida.**

Impedimento concreto:

1. Working tree de `C:\Projetos` mistura 019 e outros trabalhos; 024 exige commit isolado e reproduzível para candidata.
2. 019 ainda não tem publicação identificada; não há commit único de release.
3. 023 é projeto, não código de tesouraria.
4. Sem tag anterior, a primeira candidata **futura** deve nascer de commit isolado + artefatos, não do HEAD misto.

Quando houver commit isolado da correção 019 (Hub+Spider+AF V20) a partir de árvore identificada: candidata proposta **0.1.1** (PATCH: corrige observação de recebimento já existente, sem tesouraria). Implementação aceite de 023 seria **0.2.0** (MINOR). Nenhuma das duas está candidata hoje.

## 6. Relatórios seguintes

Todo review de evolução passa a informar: baseline (AF-BL-023 + revisão), versão candidata ou publicada, commit, Flyway, evidência. Hub e Spider citados pelas versões **deles**.
