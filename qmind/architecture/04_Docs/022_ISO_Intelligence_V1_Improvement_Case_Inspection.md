# 022 — ISO Intelligence V1 — Caso de Melhoria: Inspection and Domain Model

- Status: **Em revisão**
- Date: 2026-08-19
- Sprint / atividade: **ISOI-001** (inspeção e modelagem — sem implementação)
- Baseline de partida: **Context-OI V1** ([`021_Context_OI_V1_Baseline.md`](021_Context_OI_V1_Baseline.md))
- Fonte estratégica (somente leitura): `Arquitetura QMind/QMind_Da_Auditoria_a_Inteligencia_Organizacional V2.docx`

Documento de inspeção arquitetural. **Não altera comportamento do produto.**

---

## 0. Classificação das afirmações

Ao longo deste documento:

| Rótulo | Significado |
|--------|-------------|
| **Encontrado no código** | Observável em repositórios `qmind` / `qmind-oi` |
| **Encontrado na documentação** | Docs/ADR/baseline/V2 |
| **Inferência** | Conclusão derivada de evidências acima |
| **Hipótese** | Proposta de produto ainda não decidida |
| **Recomendação** | Sugestão fundamentada desta inspeção |
| **Decisão pendente** | Exige aceite humano antes de implementar |

---

## 1. Objetivo da inspeção

Propor o **menor corte vertical** para ISO Intelligence V1:

```text
Registrar problema → impacto/contexto → informações necessárias
→ interpretação fundamentada → achado → ação no Core
→ evidência de execução → reanalisar → observar evolução
```

Hipótese de produto sob avaliação (não criar artefato com este nome nesta atividade):

```text
Caso de Melhoria
```

Recorte normativo prioritário (inspeção): **ISO 9001 Cláusula 4.1 e 4.4**, com dependências documentadas (não implementadas).

---

## 2. Alinhamento com a referência estratégica V2

**Encontrado na documentação (V2):**

- Entrada pelo **problema empresarial**; ISO como estrutura de interpretação.
- Boundary: *Facts belong to Core. Interpretation belongs to OI.*
- Modelagem **proporcional** (somente o necessário para interpretar/operacionalizar a ISO).
- Evolução pela **Cláusula 4** (ISO Intelligence V1).
- Context-OI V1: readiness das **cláusulas 4 e 7**; *Context Readiness ≠ ISO Conformity*.
- Não antecipar Fit / Pain / Journey / LLM / motor de conformidade.

**Nota de caminho:** o prompt citava o arquivo na Desktop raiz; o arquivo V2 vigente está em  
`Desktop\Arquitetura QMind\QMind_Da_Auditoria_a_Inteligencia_Organizacional V2.docx`.  
Há também `_V3.docx` no mesmo diretório — **não usado** nesta inspeção (autoridade = V2 + prompt).

**Divergência registrada (não resolvida por implementação):** nenhuma incompatibilidade material entre o prompt ISOI-001 e a V2 quanto a tese, boundary, proporcionalidade e Cláusula 4. O prompt acrescenta a hipótese explícita “Caso de Melhoria” e o fixture de atrasos — coerentes com a tese V2, ainda não nomeados assim na V2.

---

## 3. Estado atual — QMind Core

### 3.1 Inventário de capacidades (resumo)

| Capacidade | Responsabilidade | Persistência | API / UI | Reuso para ciclo problema→ação |
|------------|------------------|--------------|----------|--------------------------------|
| Organization + membership | Tenant, papéis | `organizations`, `memberships` | Orgs API; `OrganizationProvider` | **Alto** (escopo obrigatório) |
| Organization Profile | Fatos org. ICP-01 | `organization_profiles` | `GET/PATCH …/profile`; `OrgOrganizationContext` | **Alto** (fatos de contexto 4/7) |
| Assessment | Ciclo de avaliação/auditoria | `assessments` + filhos | `/assessments/*`; lobby/work/guided… | **Baixo** como “problema”; **médio** se caso nascer de auditoria |
| Action Plan / Action Item | Plano e tarefas com dono/prazo | `action_plans`, `action_items` | `/action-plans`, `/action-items` | **Alto** com **lacuna**: plano exige `assessment_id` |
| Evidence | Provas + links | `evidences`, `evidence_links` | `/evidences` | **Alto** (prova de execução) |
| Evolution Map | Sugestões determinísticas por assessment | `evolution_*` | `/assessments/{id}/evolution-map` | **Médio** (padrão sugestão→ação); escopo assessment |
| Field Central | Cockpit de campo | *(sem tabela)* | `AssessmentWorkPage` | **Padrão UX**, não modelo |
| OrgJourneyOverview | Mapa de fases do Assessment focado | *(derivado)* | Home `/assessments` | **Padrão UX** |
| OI loop UI | Profile ↔ analyze ↔ Completar ↔ stale | — | `OrgIntelligenceContextLoop` etc. | **Alto** como **padrão de ciclo** |
| OI runs | Snapshots de envelope | `organization_intelligence_runs` | `…/intelligence/analyze`, `…/runs` | **Alto** como **padrão de histórico imutável** |
| Auth / RLS / tenant switch | Isolamento | RLS + `X-Organization-Id` | Cognito/dev; `OrganizationProvider` | **Obrigatório** |

**Encontrado no código:** não há entidade `BusinessProblem`, `ImprovementCase` ou “Caso de Melhoria”.

**Encontrado na documentação:** glossário define Assessment como ciclo completo de avaliação (escopo, equipe, coleta, constatações, plano, relatório) — `architecture/99_Reference/001_Domain_Glossary.md`.

### 3.2 OI no Core hoje

- Entrada: Profile → HTTP → OI.
- Persistência: JSONB do envelope `OrganizationalInsights` por run.
- UI: insights de **prontidão de contexto** (não problemas empresariais).
- Stale: **flag de UI** após PATCH do profile (não coluna DB).
- Reanálise: novo `INSERT` de run; histórico append-only.
- **Sem** conversão Insight OI → Action Item.

---

## 4. Estado atual — qmind-oi

### 4.1 Pipeline Context-OI V1

```text
OrganizationContextInput
  → OrganizationContextBuilder (clause4 + clause7 presence)
  → ISOContextReadinessEvaluator (re-emite; sem regras novas)
  → OrganizationalInsightBuilder (+ humanização)
  → OrganizationalInsightsAdapter
  → OrganizationalInsights (schema_version "1.0")
```

**Encontrado no código:** `_CLAUSES = (("4","clause4"),("7","clause7"))` — somente duas lentes.  
**Encontrado na documentação:** “Fora de escopo: cláusulas 5, 6, 8, 9, 10” — `docs/knowledge/ISO-Canonical-Context-Fase-1.md`.

### 4.2 Evidência: “4/7” = cláusulas **4 e 7** (não 4–7)

| Fonte | Evidência |
|-------|-----------|
| V2 / Baseline 021 | “prontidão das cláusulas 4 e 7” |
| Builder OI | blocos `iso.clause4` e `iso.clause7` apenas |
| Evaluator | itera pares `("4",…), ("7",…)` |
| Testes OI | `assert {a.clause for a in out} == {"4", "7"}` |

Baseline cobre **readiness limitada** dessas duas cláusulas — **não** a implementação integral dos requisitos 4 ou 7, nem o intervalo 4→7.

### 4.3 Semântica preservada

**Encontrado no código/docs:** *Context Readiness ≠ ISO Conformity* (models, builder docs, Baseline 021, V2 §9).

`unknown` em vocabulários controlados: fato preservado + lacuna de readiness (OI-017/018).

### 4.4 Contratos públicos

- `schema_version = "1.0"` único suportado (`contracts/versions.py`).
- `extra="forbid"` nos StrictModels → evolução **aditiva** via campos opcionais (ADR-002) ou **major** se mudar significado/obrigatoriedade.
- Não existe `ProblemAnalysis`, hipótese ou achado como tipos de domínio no OI.
- Pacote `intelligence/` é placeholder (“Fit, Pain, Journey — future”) sem lógica.

---

## 5. Avaliação do conceito “Caso de Melhoria”

### 5.1 Pergunta: é necessário?

**Recomendação: sim, como agregado conceitual de produto** — o ciclo problema→ação→evolução **não cabe** em Profile, Assessment ou OI run isolados sem distorção.

### 5.2 Alternativas consideradas

| Alternativa | Evidência | Vantagem | Custo | Risco | Decisão |
|-------------|-----------|----------|-------|-------|---------|
| A. Especializar Assessment (`type=improvement`) | Assessment = ciclo de auditoria/diagnóstico; exige model/standard/scope | Reusa lifecycle/UI | Distorce glossário; SoD/evidência de auditoria; ISO como entrada | Alto — reauditoriza o produto | **Rejeitar** como identidade do caso |
| B. Só agregação UI sobre Profile + OI + Agenda | Zero schema | Rápido | Sem dono do problema, impacto, evidências do caso, reanálise scoped | Alto — não prova o ciclo | **Rejeitar** para V1 Intelligence |
| C. Projeção somente leitura | — | Sem escrita | Não registra problema nem ação | — | Insuficiente |
| D. Nova entidade Core (agregado) + análises OI versionadas + Action Items ligados | Lacuna clara no código | Alinha V2 (problema primeiro); ownership claro | Schema/API/UI novos | Médio — mitigável com modelagem mínima | **Recomendada** |
| E. Duplicar ActionItem fora de ActionPlan | ActionPlan exige `assessment_id` | Evita tocar Assessment | Segunda máquina de estados | Alto | **Rejeitar**; preferir estender vínculo do plano |

**Nome “Caso de Melhoria”:**

- **Hipótese de produto** útil internamente.
- **Risco:** soa próximo de “melhoria contínua ISO” / auditoria.
- **Recomendação de linguagem de UI:** preferir **“Problema em acompanhamento”** / **“Registrar problema”** na superfície; manter “Caso de Melhoria” como termo de domínio interno **até validação com usuários** (**Decisão pendente**).

---

## 6. Modelo de domínio recomendado (conceitual)

### 6.1 Agregado raiz (Core) — fatos

Nome interno provisório: **ImprovementCase** (não implementar).  
Produto UI: problema em acompanhamento.

```text
ImprovementCase (Core)
├── organization_id
├── problem_statement          # fato declarado
├── impacts[]                  # fatos declarados (SLA, reclamação, …)
├── related_process_refs[]     # refs a org_processes / texto
├── related_parties[]          # áreas/papéis (texto mínimo na V1)
├── status                     # open | analyzing | acting | reviewing | closed
├── optional assessment_id     # se nasceu de auditoria
├── created_by / timestamps
└── links
    ├── evidence_links (Core)
    ├── analysis_runs (snapshots OI — ver §6.2)
    └── action_plan XOR assessment (ver §6.3)
```

### 6.2 Interpretação (OI) — snapshots

```text
ProblemAnalysis (conceitual OI → envelope persistido no Core)
├── case_id / analysis_id / generated_at
├── context_status             # suficiente | insuficiente | …
├── interpretation_summary
├── hypotheses[]
├── findings[]                 # achados interpretativos — NÃO NC formal
├── iso_basis[]                # ex.: 4.1, 4.4 (estrutura, não veredito)
└── limitations[]
```

**Recomendação de contrato:**

1. **Preservar** `/analyze` Profile + `OrganizationalInsights` intactos (Context-OI V1).
2. Introduzir **mensagem aditiva** (novo endpoint ou novo envelope versionado) para análise de problema — **preferência:** minor `1.x` com objeto opcional **ou** `schema_version` major `2.0` se a semântica de `insights[]` não puder carregar achados sem ambiguidade.
3. **Não sobrecarregar** insights de readiness (`supporting_facts` = chaves técnicas de Profile) para carregar hipóteses de atraso/SLA.

**Decisão pendente:** minor aditivo vs major `2.0` para ProblemAnalysis.

### 6.3 Ações (Core)

**Encontrado no código:** `ActionPlanCreate.assessment_id: UUID` obrigatório.

**Recomendação:** reutilizar Action Item (dono, prazo, status, efficacy) mediante **extensão mínima futura**: ActionPlan com vínculo **XOR** `assessment_id` | `improvement_case_id`.  
Até lá, **não** fingir que Action Items já servem Casos.

### 6.4 Relação do ciclo

```text
Problema (Core)
 → Impacto/contexto (Core facts)
 → Gate Context Readiness 4/7 (OI existente, reuso como pré-condição)
 → ProblemAnalysis (OI novo pipeline)
 → Achados interpretativos (OI → snapshot Core)
 → Ação (Core ActionItem)
 → Evidência de execução (Core Evidence)
 → Reanálise (novo snapshot; histórico imutável)
 → Evolução (comparar runs + status de ações)
```

### 6.5 Imutável vs editável

| Imutável (snapshot) | Editável |
|---------------------|----------|
| Cada `ProblemAnalysis` / OI run | `problem_statement`, impactos, vínculos de processo |
| Envelope persistido | Status do caso; Action Items; evidências novas |
| Identificadores técnicos de run | Decisão humana de aceitar/rejeitar recomendação |

---

## 7. Ownership Core / OI por elemento

| Elemento | Dono | Notas |
|----------|------|-------|
| Problema, impacto, processo/partes (fatos) | **Core** | |
| Evidência / anexo / link | **Core** | |
| Hipótese, confiança, interpretação | **OI** | |
| Achado interpretativo + `iso_basis` | **OI** (produz) / **Core** (persiste snapshot) | Achado ≠ NC formal |
| Recomendação / próximo passo | **OI** | |
| Decisão humana (aceitar/descartar) | **Core** | |
| Ação, prazo, dono, eficácia | **Core** | |
| Indicador / resultado medido | **Core** (fato) | Interpretação de tendência: OI em corte futuro |
| Não conformidade formal | **Fora** deste corte (Assessment/Finding) | |
| Workflow, auth, RLS, UI | **Core** | |
| Regras ISO / readiness / humanização | **OI** | |

**OI deve devolver:** interpretação + hipóteses + achados + limitações (não “NC”).  
**Core não implementa:** regras de cláusula; apenas exibe, persiste e operacionaliza.

---

## 8. Distinções semânticas obrigatórias

| Termo | Significado neste desenho |
|-------|---------------------------|
| Fato declarado | Afirmação do usuário/org (ex.: “há atraso”) |
| Fato observado | Dado operacional registrado (ex.: métrica importada) — V1 pode omitir |
| Evidência | Artefato/prova no Core |
| Hipótese | Interpretação provisional do OI |
| Interpretação | Síntese OI do conjunto |
| Achado | Conclusão OI rastreável ao problema — **não** NC ISO |
| Recomendação | Próximo passo sugerido pelo OI |
| Decisão do usuário | Aceite/recusa no Core |
| Não conformidade formal | Domínio de Assessment/Finding — **fora** do corte |

Estados de avaliação sugeridos (sem afirmar conformidade):

`não avaliado` · `contexto insuficiente` · `evidência insuficiente` · `hipótese` · `parcialmente sustentado` · `sustentado pelas evidências disponíveis` · `atenção necessária` · `requer validação humana`

Evitar na UI deste fluxo: conforme / não conforme / certificável / probabilidade de certificação.

---

## 9. Proposta conceitual de contrato

### 9.1 Entrada (conceitual)

```text
ProblemContextInput (v? )
├── schema_version
├── core_organization_id, request_id, correlation_id, occurred_at, source
├── context.profile?              # reuso OrganizationProfileFacts
├── context.problem               # statement, impacts[], process_refs[]
├── context.evidence_refs[]?      # EvidenceReference (ids Core)
└── metadata
```

### 9.2 Saída (conceitual)

Alinhar ao esboço `ProblemAnalysis` do prompt ISOI-001, com:

- `supporting_facts` / `supporting_evidence` como **refs rastreáveis** (não misturar com chaves de Profile readiness);
- `iso_basis[]` como **estrutura** (ex. `4.1`, `4.4`), nunca veredito de conformidade;
- `limitations[]` obrigatório quando evidência fraca.

### 9.3 Compatibilidade com OI v1 atual

| Opção | Compatível com `1.0`? | Comentário |
|-------|----------------------|------------|
| Sobrecarregar `OrganizationalInsights.insights` | Arriscado | Confunde readiness com análise de problema |
| Campos opcionais no envelope `1.0` | Possível (ADR-002) | Só se consumers Core ignorarem desconhecidos — hoje `forbid` no OI; Core snapshots precisam sync |
| Novo envelope + endpoint | Preferível | Mantém Context-OI V1 intacto |

**Preservar `schema_version="1.0"`** para o fluxo Profile↔Readiness.  
**Mudanças incompatíveis** (renomear insight readiness, mudar `supporting_facts`, exigir problem no `/analyze` atual) → **nova versão**.

---

## 10. Jornada de UI recomendada

### 10.1 Ponto de entrada

**Recomendação:** permanecer em `/assessments` (home de Inteligência Organizacional) **como hub**, com seção:

```text
Problemas em acompanhamento
[ Registrar novo problema ]
```

ao lado (não dentro) do loop Profile↔OI atual.

**Não** começar por cláusula/checklist/conforme.

### 10.2 Detalhe

**Recomendação:** rota específica de detalhe (ex. `/improvement-cases/:id` — nome de rota **Decisão pendente**) com abas/seções:

1. Problema e impacto  
2. Contexto e informações necessárias (reuso Completar + gate 4/7)  
3. Análise e achados do QMind  
4. Ações  
5. Evolução  

Hierarquia visual: problema → impacto → situação → interpretação → achados → próxima ação → evolução → **fundamentação ISO por último / colapsável**.

### 10.3 Reuso de componentes

| Componente | Como reutilizar |
|------------|-----------------|
| Action Items | Após extensão de vínculo do plano; UI `ActionPlanPanel` como referência |
| Field Central | **Não** reusar acoplado a assessment; extrair **padrão** de cockpit depois |
| Evolution Map | Não é a análise OI; inspirar “sugestão→ação”; manter separado |
| OrgIntelligenceContextLoop | Padrão Completar/stale/reanalisar para o **gate** de contexto do caso |
| OrgJourneyOverview | Opcional como mapa de fases do **caso**, sem misturar fases de Assessment |

### 10.4 Menor UI que prova o ciclo

1. Criar problema + impacto  
2. Ver lacunas de contexto (4/7) e completar Profile se preciso  
3. Rodar análise → 1 achado + 1 recomendação  
4. Criar 1 Action Item  
5. Anexar 1 evidência  
6. Reanalisar → novo snapshot na timeline  

---

## 11. Tenancy, histórico, stale

- Todo agregado com `organization_id` + RLS + `X-Organization-Id`.
- Guardar `core_organization_id` do envelope OI vs org ativa (padrão atual).
- Tenant switch: abortar in-flight; limpar cache (padrão `OrganizationProvider`).
- Histórico: **append-only** de análises do caso (espelhar `organization_intelligence_runs` ou tabela irmã scoped ao caso).
- Stale: após editar fatos do caso ou Profile relevante → cue de UI → reanalisar.
- Riscos cross-tenant: IDs de evidência/caso em refs OI sem validação de org; mitigar no Core antes de persistir.

---

## 12. Primeiro corte vertical recomendado

### 12.1 Escopo

```text
Problema operacional (atrasos em entregas — fixture conceitual)
+ processo relacionado (fato mínimo)
+ gate Context Readiness cláusulas 4 e 7 (reuso)
+ interpretação OI focada em 4.1 e/ou 4.4 (determinística V1)
+ 1 achado + 1 recomendação
+ 1 Action Item no Core
+ reanálise com histórico
```

### 12.2 Dependências ISO apenas documentadas

| Cláusula | Relação | Ação nesta V1 |
|----------|---------|---------------|
| 4.2 Partes interessadas | Cliente/SLA | Mencionar em limitações se ausente |
| 5.3 Papéis | Dono da ação | Usar membership Core, sem motor 5.3 |
| 6.1 Riscos | Hipótese de causa | Opcional em texto de hipótese |
| 7.* Apoio | Já no gate readiness | Reuso gate; sem expansão |
| 8.1 Operação | Processo de pedidos | Ref de processo como fato |
| 9.1 Monitoramento | Indicadores | Fora (só placeholder) |
| 10.2 NC/ação corretiva | Não usar NC automática | Action Item sem rótulo NC |

### 12.3 Entregará ao usuário

Um problema reconhecível acompanhado de interpretação rastreável e uma ação com dono — demonstrando valor **antes** de auditoria.

### 12.4 Fora de escopo (deliberado)

Conformidade, NC automática, certificabilidade, maturidade, eficácia SGQ, LLM, Fit/Pain/Journey, modelo enciclopédico, banco/auth no OI, Assessment como identidade do caso.

---

## 13. Capacidades: reutilizar vs não reutilizar

### Reutilizar

- Organization Profile + Completar + stale/reanalyze pattern  
- Context Readiness 4 e 7 como **gate**  
- HTTP/JSON boundary, persistência de runs, tenant guards  
- Action Item lifecycle (após vínculo)  
- Evidence + links  
- OpenAPI → api-client  

### Não reutilizar / não sobrecarregar

- Assessment como “Caso de Melhoria”  
- Insights de readiness como achados de problema  
- Evolution Map como motor ISO Intelligence  
- Field Central / OrgJourney acoplados a Assessment statuses  
- Finding `nonconformity` para rotular saída OI  

---

## 14. Lacunas reais

1. Ausência de agregado de problema empresarial no Core.  
2. ActionPlan amarrado exclusivamente a Assessment.  
3. OI sem pipeline de interpretação de problema / 4.1–4.4 além de presença.  
4. Sem ponte Insight/Análise → Action Item.  
5. Sem UI de lista/histórico de análises por problema (só latest org-level OI).  
6. Duas noções de “readiness” (OI vs AuditPlan) — risco de linguagem.

---

## 15. Riscos e decisões pendentes

| ID | Tema | Status |
|----|------|--------|
| D1 | Nome de produto (Caso de Melhoria vs Problema em acompanhamento) | Pendente |
| D2 | Novo envelope OI minor vs major | Pendente |
| D3 | ActionPlan XOR `improvement_case_id` vs outro vínculo | Pendente |
| D4 | Rota UI e IA copy | Pendente |
| D5 | Persistência: estender `organization_intelligence_runs` vs tabela por caso | Pendente |
| R1 | Confundir readiness com conformidade na UI | Mitigar copy |
| R2 | Reauditorizar o produto via Assessment | Evitar alt. A |
| R3 | Cross-tenant via evidence_refs | Guards Core |

---

## 16. Prompt recomendado para a primeira implementação

*(Não executar nesta atividade.)*

Escopo sugerido do próximo prompt:

1. Aceitar D1–D5 mínimos.  
2. Migration + API Core do agregado mínimo (problema, impacto, status, org).  
3. Extensão ActionPlan XOR + 1 fluxo criar ação a partir de achado aceito.  
4. OI: novo pipeline determinístico 4.1/4.4 + contrato (versão decidida) **sem** alterar readiness `/analyze` atual.  
5. UI hub + detalhe com 5 seções; fundamentação ISO colapsável.  
6. Testes: tenancy, histórico imutável, stale, não afirma conformidade.  
7. Proibir LLM, NC automática, scores.

---

## 17. Referências inspecionadas (amostra)

**Core:** `04_Docs/016`–`021`, glossário, state machines, módulos `orgs`, `oi`, `assessments`, `actions`, `evidence`, `evolution_map`, UI `OrgIntelligence*`, `AssessmentsPage`, OpenAPI/api-client.

**OI:** `docs/architecture/001`–`009`, `ISO-Canonical-Context-Fase-1.md`, ADR-001/002, `contracts/*`, `context/*`, `readiness/*`, `insights/*`, `orchestration/*`, `api/*`, testes associados.

**Estratégia:** V2 docx (extração textual 2026-08-19).

---

## 18. Fechamento ISOI-001

Inspeção concluída **sem implementação de funcionalidade**.  
Artefato: este documento + entrada no índice `architecture/README.md`.
