# 029 — ISO Intelligence V1 — Evidência Contextual e Medição do Resultado

- Status: **Em revisão (Core-only)** — revisão **001** aplicada; ver §11
- Date: 2026-08-24
- Activity: **ISOI-008**
- Name: **Evidence & Result Measurement V1**
- Revision: **001** (migration `20260824_0024` reconciliada; contrato de API alterado)
- Predecessor: [`028`](028_ISO_Intelligence_V1_Action_Execution_Workspace.md) (ISOI-007)
- OI: **sem alteração funcional** — pin `2d78eff` preservado

Documento operacional da camada que responde a duas perguntas distintas: **o que comprova que a ação foi feita** (evidência) e **o que comprova que o problema diminuiu** (medição). Prepara os fatos que a **Execution Intelligence** (ISOI-009) irá interpretar; **não** os interpreta no OI neste incremento.

---

## 1. Propósito

Fechar a lacuna entre "ação concluída" e "resultado provado".

Até ISOI-007 o sistema sabia dizer que uma ação foi executada e validada por gente. Não sabia dizer **com que prova** nem **quanto o problema mudou**. ISOI-008 acrescenta as duas coisas sem transformar o QMind num repositório de arquivos nem num BI:

- **Evidência contextual** — o arquivo é anexado *à ação* (ou ao caso de melhoria), e o contexto de origem é derivado no servidor; o navegador nunca precisa nomear um alvo.
- **Medição do resultado** — um plano de medição por ActionPlan, com indicadores versionados, linha de base, meta e leituras append-only.

A regra que atravessa tudo: **meta atingida não equivale, por si só, à eficácia confirmada**. A avaliação alimenta a decisão humana de eficácia; nunca a substitui.

---

## 2. Mapa visual

```text
ActionItem (card no board)
   ├── Evidência contextual ......... "isto foi feito"
   │      authorize → PUT → receive → link (mesma chamada)
   │
   └── ActionPlan
          └── MeasurementPlan ....... "isto mudou?"
                 └── IndicatorDefinition (versionado)
                        ├── unidade tipada + casas decimais
                        ├── meta (valor | faixa) + data-alvo
                        └── MeasurementRecord (append-only, correção = nova versão)
                               ├── kind = baseline .... o ponto de partida
                               └── kind = observation . as leituras seguintes
                                 ↓
                        TargetEvaluation → postures
                                 ↓
   Board (badges/filtros) · Card detail · ImprovementCase Evolution
                                 ↓
             decisão humana de eficácia (inalterada)
                                 ↓
             Execution Intelligence — fase futura (ISOI-009)
```

---

## 3. Princípios e invariantes

1. **Meta ≠ eficácia** — `target_posture = met` é insumo. O aviso permanente aparece no card detail e no painel de evolução; nenhuma transição de `ActionItem` é disparada por medição.
2. **Evidência tem contexto exclusivo** — `evidences` com XOR `assessment_id`/`improvement_case_id` (`ck_evidences_context_xor`); linhas legadas (todas com `assessment_id`) continuam válidas.
3. **Trilha não some** — `evidence_links` com soft delete (`removed_at/removed_by/removal_reason`); `DELETE` revogado para `qmind_app` em **todas** as tabelas da trilha (`action_measurement_plans`, `indicator_definitions`, `measurement_records`, `outcome_observation_measurements`, `evidence_links`, `evidences`). Descarte de evidência é mudança de status, não remoção de linha.
4. **Correção não apaga** — corrigir uma medição insere nova linha com `supersedes_measurement_id` + `correction_reason` obrigatório (CHECK no banco). `measurement_records` **não tem coluna `status`**: ser superseded é *derivado* da existência de um sucessor, e o vínculo de sucessão é único (`uq_measurement_one_successor`), então cada leitura é corrigível exatamente uma vez. `UPDATE` também está revogado — o serviço não tem como reescrever um valor nem por engano.
5. **Indicador é versionado** — revisar um indicador que já tem medições cria nova versão (`version`, `lineage_id`, `supersedes_indicator_id`); a série antiga permanece atribuída à versão que a produziu, e a linha de base é recarregada como baseline da nova versão.
6. **Linha de base é uma medição** — o ponto de partida é a primeira leitura do indicador (`measurement_records.measurement_kind = 'baseline'`), não uma coluna da definição: assim ele carrega quem mediu, quando mediu e pode ser corrigido pelas mesmas regras. Ativar o plano exige, em cada indicador ativo, **baseline registrada ou `baseline_unavailable_reason` escrito**, meta completa e responsável nomeado. A regra é de ativação, não de rascunho.
7. **Decimal é decimal** — `numeric(20,6)` no banco, `Decimal` no serviço, **string** no contrato e na tela. Nenhum `Number()` toca um valor de indicador no caminho até o olho de quem lê — inclusive no gráfico, cuja geometria é calculada com `BigInt` (`web/src/execution/decimalSeries.ts`).
8. **Unidade é tipada** — `unit_kind` fechado (`percentage`, `count`, `currency`, `ratio`, `score`, `duration_*`, `dimensionless`, `custom`) + `custom_unit_label`/`currency_code`/`decimal_places`. Texto livre permitia dois indicadores dizerem `%`, `percent` e `pct` querendo coisas diferentes; o rótulo de tela (`unit_label`) é derivado na leitura.
9. **Sustentação vem de documento** — `substantiation` é `verified` só quando a leitura tem evidência **aprovada** anexada, `partial` quando há documento ainda não aprovado, `none` sem documento. O número sozinho é uma afirmação, não uma prova.
10. **Pior sinal vence** — `measurement_posture` do conjunto é `awaiting_baseline > overdue > awaiting_measurement > on_time`; o board precisa mostrar o que pede atenção, não a média.
11. **Sem N+1** — contagem de evidência vem em `LATERAL` na consulta do board; posturas vêm de **uma** chamada em lote por `action_plan_id`; `GET evidence-links` devolve o anexo já resolvido (link + documento) numa consulta, então o navegador não relê evidência por evidência.
12. **UI sem UUID** — a lista de evidências fala em tipo, situação, data e tamanho; nunca em identificador ou `storage_key`.
13. **Idempotência com escopo** — `authorize` e `create_measurement` gravam `idempotency_scope` (escolhido pelo servidor), `idempotency_key_hash` (SHA-256 da chave do cliente) e `request_fingerprint` (SHA-256 dos campos significativos). Repetir a mesma requisição devolve o mesmo recurso; **reusar a chave com corpo diferente responde 409** em vez de devolver silenciosamente o recurso errado.
14. **RLS** — as quatro tabelas novas com `ENABLE` + `FORCE ROW LEVEL SECURITY` e política `tenant_isolation`; papéis de medição não elevam RBAC. `action_owner` só escreve no que é seu (plano, indicador ou item sob sua responsabilidade).
15. **Rollback não apaga história** — `downgrade()` da `20260824_0024` **recusa** rodar se existir qualquer dado ISOI-008, com a contagem no erro. Roundtrip de migração exige base descartável (`tests/alembic_support.py`).

---

## 4. Domínio (persistência)

Migration aditiva: **`20260824_0024`** (após `20260824_0023`).

| Entidade | Papel |
|----------|--------|
| `action_measurement_plans` | Como um ActionPlan vai provar que funcionou: `objective`, `owner_membership_id`, `review_cadence_days`, `next_review_at`. XOR assessment/caso; **um** plano não-`closed` por ActionPlan (índice único parcial); plano `active` exige responsável (`ck_amp_active_has_owner`) |
| `indicator_definitions` | Indicador versionado: `unit_kind` + `custom_unit_label`/`currency_code`/`decimal_places`, `direction`, meta (`target_value` **ou** `target_min/max`, coerência garantida por `ck_indicator_target_shape`), data-alvo, cadência, `owner_membership_id`, `baseline_unavailable_reason` |
| `measurement_records` | Leituras append-only com `measurement_kind` (`baseline\|observation`); correção via `supersedes_measurement_id` (sucessor único); sem coluna `status` |
| `outcome_observation_measurements` | Liga observação de resultado do caso às medições que a sustentam |

Alterações em tabelas existentes:

- `evidences`: `improvement_case_id`, XOR de contexto, fase `action_execution`, trio de idempotência (`idempotency_scope`, `idempotency_key_hash`, `request_fingerprint`) com índice único parcial.
- `evidence_links`: novos alvos (`action_item`, `action_check_in`, `action_impediment`, `measurement_record`, `outcome_observation`, `improvement_case`), soft delete e unicidade só entre ativos.
- `action_items`: índice `(action_plan_id, organization_id)` para o board responder "esta ação é medida?" sem consulta por card.

Chaves estrangeiras do domínio são todas `NO ACTION` (efeito `RESTRICT`): apagar um plano nunca leva os indicadores nem as medições consigo. Só `organization_id` cascateia — remover um tenant inteiro é uma operação deliberada.

`upgrade()` é **idempotente e auto-reparadora**: cada passo é `IF NOT EXISTS` ou `DROP ... IF EXISTS` seguido de `CREATE`/`ADD`, então rodar sobre uma base já marcada `20260824_0024` na forma antiga a converte para a forma da revisão 001 (incluindo backfill de `baseline_value` para `measurement_records` e migração de `unit` para `unit_kind`).

---

## 5. Avaliação (regras puras)

`app/modules/measurements/evaluation.py` — sem banco e sem relógio próprio (o `now` é injetado).

| Estado (`TargetEvaluationState`) | Quando |
|---|---|
| `awaiting_baseline` | Linha de base não resolvida |
| `awaiting_measurement` | Base resolvida, nenhuma leitura depois da ação |
| `inconclusive` | Há leitura, não há meta comparável |
| `target_met` | Última leitura satisfaz a meta (`>=`, `<=` ou dentro da faixa) |
| `on_track` | Meta não satisfeita e prazo não venceu |
| `target_not_met` | Meta não satisfeita e `target_due_at` já passou |

`direction` fala em intenção, não em aritmética: `higher_is_better`, `lower_is_better`, `within_range`, `maintain_range`. Os nomes antigos (`increase_is_better`, `decrease_is_better`, `stay_within_range`) continuam aceitos como *alias* na entrada da API.

Derivados:

- `substantiation`: `verified` quando a leitura tem evidência **aprovada** anexada; `partial` com documento anexado ainda não aprovado; `none` sem documento. O plano vale pelo indicador mais fraco.
- `next_measurement_due_at`: cadência a partir da última leitura (ou da ativação); sem cadência, a própria data-alvo.
- `is_measurement_overdue`: com cadência, `now > due`. Sem cadência, **só** um indicador nunca medido pode atrasar — quem já mediu não tem compromisso agendado a perder.
- `measurement_posture` / `target_posture` (`unknown\|met\|not_met\|mixed`): agregação por plano e por caso.

Cada avaliação carrega `headline` e `what_to_do_next` em português corrente — a tela lê o que o domínio decidiu, não reinterpreta.

---

## 6. APIs (Core)

Evidência contextual:

- `POST /api/v1/organizations/current/actions/{action_item_id}/evidences/authorize` — já devolve o vínculo com o `action_item`
- `POST /api/v1/organizations/current/improvement-cases/{case_id}/evidences/authorize` — já devolve o vínculo com o `improvement_case`
- `GET  /api/v1/organizations/current/evidence-links?target_type=&target_id=` — devolve **anexos** (`{ link, evidence }`), não só vínculos
- Ciclo existente preservado: `PUT bytes` (local) → `transitions/receive` → `security_pass|security_fail`.

Medição:

- `POST|GET /api/v1/organizations/current/measurement-plans` (+ `{plan_id}`, `PATCH`)
- `POST .../measurement-plans/{plan_id}/transitions/activate|close`
- `POST|GET .../measurement-plans/{plan_id}/indicators` (`include_superseded` para histórico)
- `POST .../indicators/{indicator_id}/revise|retire`
- `POST|GET .../measurement-plans/{plan_id}/measurements`
- `POST .../measurements/{record_id}/correct`
- `GET  /api/v1/action-plans/{action_plan_id}/measurement-summary`

Papéis: escrita de plano/indicador em `org_admin, consultant_auditor, quality_manager`; **registrar medição** inclui `process_owner` e `action_owner` (quem executa mede); leitura inclui `reader`. `authorize` de evidência de ação segue os papéis de execução; `security_pass` continua restrito a operadores e desabilitável por configuração.

**R6 — escopo do `action_owner`:** quem tem apenas `action_owner` escreve somente no que é seu — o plano cujo `owner_membership_id` é o seu, o indicador que responde, ou o `ActionItem` sob sua responsabilidade. Fora disso a resposta é 403, não uma escrita silenciosa em plano alheio.

UI: **Execução** (`/execution`, `/execution/cards/:id`) consome `@qmind/api-client` gerado — nenhum `fetch` manual foi introduzido.

---

## 7. Superfície de UI

| Lugar | O que mostra |
|---|---|
| Card detail — **Evidências** | Lista por rótulo humano (tipo · situação · data · tamanho); anexo contextual com fases `Preparando/Enviando/Confirmando`; leitor vê a lista, não o formulário |
| Card detail — **Medição do resultado** | Posturas, `headline`, `what_to_do_next`, aviso permanente de eficácia; responsável do plano e de cada indicador por nome; formulários de criar plano (com escolha de responsável), adicionar indicador (unidade tipada + responsável), registrar ponto de partida, medir e corrigir |
| Histórico do indicador | Tabela acessível sempre, distinguindo ponto de partida de medição; *sparkline* SVG **apenas** com ≥2 leituras comparáveis, com `aria-label` descrevendo a série; linha estática, sem animação a desligar sob `prefers-reduced-motion`; geometria em `BigInt`, então valor gigante ou com muitas casas não vira `NaN` nem `Infinity` |
| Board | Badge de evidência (`N evidência(s) · N aprovada`) e de postura; postura `on_time`/`unknown` fica em silêncio — só o que pede atenção vira selo |
| Board — filtros | "Medição atrasada" e "Meta não atingida", aplicados sobre o payload já carregado |
| ImprovementCase Evolution | `MeasurementSummaryPanel` compartilhado: mesmas posturas, mesma frase, mais o motivo da prontidão de encerramento |

O plano em rascunho não oferece formulário de observação: a tela explica que as leituras começam depois de iniciado o acompanhamento, em vez de deixar o servidor recusar com 409. O **ponto de partida**, ao contrário, pode ser registrado com o plano ainda em rascunho — é justamente o que falta para ativá-lo.

---

## 8. Integrações preservadas

- Contratos OI inalterados; pin funcional `2d78eff`.
- Fluxo de evidência de assessment (autorize/guided/link) intacto — `uploadActionEvidenceFile` é adição, não substituição.
- Transições de `ActionItem` inalteradas: medir não move card, não valida e não confirma eficácia.
- `closure_readiness` do caso passa a considerar postura de medição como **informação faltante** (`awaiting_measurement`, `awaiting_baseline`, `overdue` bloqueiam a revisão) — nunca como veredito de sucesso ou fracasso.
- OpenAPI + `@qmind/api-client` regenerados; `check:api-client` verde.

---

## 9. Limitações remanescentes legítimas

- `security_pass` continua simulado e sujeito a `allow_simulated_security_pass`; não há worker de quarentena.
- A UI não expõe `retire` de indicador nem `close` de plano — as rotas existem; a tela cobre o caminho principal.
- Comparação entre versões de indicador não é agregada no gráfico: a série mostrada é a da versão corrente, por decisão de honestidade estatística.
- `outcome_observation_measurements` está no domínio e no board de leitura, mas ainda sem tela dedicada de vínculo observação↔medição.
- Sem projeção de tendência, previsão ou alerta automático — ISOI-009/010.
- Testes de *roundtrip* de migração (0002–0005) são **pulados** em base compartilhada com história ISOI-008: a recusa do `downgrade` é o comportamento correto e está coberta por teste próprio, mas o ida-e-volta completo só roda em base descartável.

---

## 10. Matriz Core ↔ OI

| Capacidade | Lado | Nota |
|------------|------|------|
| ISOI-008 Evidência contextual | **Core-only** | Prova documental da execução |
| ISOI-008 Medição do resultado | **Core-only** | Fatos numéricos + avaliação determinística |
| Aviso "meta ≠ eficácia" | **Core-only** | Regra de produto, não de modelo |
| Execution Intelligence (ISOI-009, futuro) | OI | Consumirá indicadores, leituras e posturas via contrato ainda não definido |

---

## 11. Revisão 001 — o que mudou e por quê

A primeira forma desta atividade foi aplicada em bases de desenvolvimento e revisada antes de virar baseline. As mudanças não são refinamento cosmético: cada uma corrige uma afirmação que o modelo antigo não conseguia sustentar.

| Antes | Agora | Por que |
|---|---|---|
| `indicator_definitions.baseline_value/baseline_at` | `measurement_records` com `measurement_kind = 'baseline'` | O ponto de partida é uma medição. Como coluna, não tinha autor, não tinha data própria de leitura e não podia ser corrigido pelas regras das outras leituras |
| `unit` em texto livre | `unit_kind` fechado + `custom_unit_label` / `currency_code` / `decimal_places` | `%`, `percent` e `pct` eram três unidades diferentes para o banco e a mesma para quem lia. Sem tipo não há como validar que uma porcentagem está entre 0 e 100 |
| `increase_is_better` / `decrease_is_better` / `stay_within_range` | `higher_is_better` / `lower_is_better` / `within_range` / `maintain_range` (aliases antigos aceitos na entrada) | O nome descrevia a aritmética, não a intenção, e faltava dizer "mantenha onde já está" |
| `action_measurement_plans.purpose` | `objective` (+ `owner_membership_id`, `review_cadence_days`, `next_review_at`) | `purpose` dizia para que a linha existia; auditoria pergunta o que ela precisa alcançar, quem responde e quando será revisto |
| `measurement_records.status` | derivado de `supersedes_measurement_id` (sucessor único) | Um `status` armazenado obrigava o app a ter `UPDATE` numa tabela append-only e permitia dois escritores discordarem sobre qual leitura é a atual |
| `substantiation` derivada da linha de base | derivada de evidência **aprovada** anexada | Ter um número de partida não é ter prova documental. A palavra "sustentado" precisava significar o que diz |
| `authorize_idempotency_key` (chave crua) | `idempotency_scope` + `idempotency_key_hash` + `request_fingerprint` | A chave crua identifica o cliente e, sem escopo nem impressão do corpo, uma chave reusada devolvia o recurso errado em silêncio. Agora conflito é 409 |
| Alvo de vínculo `agile_ceremony_record` | removido; `improvement_case` acrescentado | Uma cerimônia pertence a um sprint: não havia como provar que um vínculo a ela ficava dentro da fronteira assessment/caso que todo outro alvo respeita |
| `GET evidence-links` devolvia vínculos | devolve anexos (`{ link, evidence }`) | O navegador relia cada evidência por identificador; o servidor já sabe responder numa consulta |
| `downgrade()` derrubava as tabelas | **recusa** com contagem quando há história | Um rollback de esquema não é licença para apagar trilha de auditoria |

Pendências desta revisão: nenhuma no Core. O status volta a **Implementado** quando a baseline for pinada.
