# QMind — Modelo de maturidade (v0)

- Status: Aceito
- Data: 2026-08-03
- Congelamento: `domain-docs-v0`
- Código do modelo: `qmind_maturity_iso9001_v0`
- Depende de: `001_State_Machines.md`, `002_Roles_and_Permissions.md`, `../99_Reference/001_Domain_Glossary.md`
- Aceite: `../04_Docs/006_Domain_Acceptance_Checklist.md`
- Afeta: `MaturityAssessment` / `MaturityScore`, relatórios, enums de aplicabilidade, evidência mínima

## 1. Finalidade

Avaliar, de forma **repetível e auditável**, o grau de maturidade do sistema de gestão da qualidade da organização no escopo de uma `Assessment`, sem substituir o julgamento de conformidade normativa. Pontuações são **hipótese estruturada** até revisão humana.

## 2. Dimensões (v0)

Seis dimensões equilibradas para diagnóstico ISO 9001:2015 (sem reproduzir texto normativo):

| Código | Dimensão | Foco |
|---|---|---|
| `D1_context_leadership` | Contexto e liderança | Direção, política, papéis, partes interessadas relevantes ao escopo |
| `D2_process_risk` | Processos e riscos | Abordagem por processos, interações, pensamento baseado em risco |
| `D3_support` | Suporte | Competência, comunicação, informação documentada controlada |
| `D4_operation` | Operação | Planejamento e controle operacional no escopo |
| `D5_performance` | Avaliação de desempenho | Monitoramento, indicadores, auditoria interna, análise crítica |
| `D6_improvement` | Melhoria | Não conformidades, ações corretivas, melhoria contínua |

Cada dimensão possui **critérios** (abaixo) pontuáveis. Critérios ligam-se a `Requirement` / `Criterion` do `AssessmentModel` quando houver mapeamento autorizado.

## 3. Níveis

Escala ordinal **1–5** por critério aplicável:

| Nível | Código | Significado operacional |
|---|---|---|
| 1 | `initial` | Prática ad hoc; pouco ou nenhum controle demonstrável |
| 2 | `defined` | Prática definida em partes; inconsistente entre áreas |
| 3 | `managed` | Prática gerida com evidência recorrente no escopo |
| 4 | `measured` | Desempenho medido e usado na decisão |
| 5 | `optimizing` | Melhoria sistemática baseada em dados e aprendizagem |

Níveis são **inteiros**. Não há meia nota no critério.

## 4. Critérios objetivos (v0)

Cada critério: código, dimensão, enunciado operacional, âncoras por nível (resumo), evidência mínima sugerida.

### D1 — Contexto e liderança

| Código | Critério | Âncora L3 (managed) | Evidência mínima típica |
|---|---|---|---|
| `D1.C1` | Contexto e partes interessadas considerados no escopo | Registro atualizado usado no planejamento | Documento/entrevista + evidência `approved` |
| `D1.C2` | Política e objetivos alinhados e comunicados | Objetivos mensuráveis conhecidos pelos envolvidos | Política/objetivos + evidência de comunicação |
| `D1.C3` | Papéis e autoridade da qualidade claros | Responsabilidades exercidas na prática | Organograma/RACI + entrevista |

### D2 — Processos e riscos

| Código | Critério | Âncora L3 | Evidência mínima típica |
|---|---|---|---|
| `D2.C1` | Processos do escopo identificados e interativos | Mapa/lista vigente com donos | `OrgProcess` + evidência |
| `D2.C2` | Riscos e oportunidades tratados nos processos | Ações de risco rastreadas | Registro de risco + ação |
| `D2.C3` | Critérios de processo e controles aplicados | Controles observados/registrados | Procedimento + registro operacional |

### D3 — Suporte

| Código | Critério | Âncora L3 | Evidência mínima típica |
|---|---|---|---|
| `D3.C1` | Competência para funções críticas | Capacitação/qualificação demonstrada | Registro de competência |
| `D3.C2` | Informação documentada controlada | Versão vigente disponível e usada | Controle de documentos + amostra |
| `D3.C3` | Comunicação interna eficaz no escopo | Canais e registros adequados ao risco | Evidência de comunicação relevante |

### D4 — Operação

| Código | Critério | Âncora L3 | Evidência mínima típica |
|---|---|---|---|
| `D4.C1` | Planejamento operacional do escopo | Planos/ordens coerentes com requisitos | Planejamento + registro |
| `D4.C2` | Controle de mudanças e não conformidades de processo | Desvios tratados | Registro de mudança/NC de processo |
| `D4.C3` | Controle de fornecedores/externos quando aplicável | Avaliação/monitoramento vigentes | Avaliação de fornecedor |

### D5 — Avaliação de desempenho

| Código | Critério | Âncora L3 | Evidência mínima típica |
|---|---|---|---|
| `D5.C1` | Indicadores e monitoramento do escopo | Dados coletados e revisados | Painel/relatório de indicador |
| `D5.C2` | Auditoria interna / verificação independente | Ciclo planejado e executado | Relatório de AI (se no escopo) |
| `D5.C3` | Análise crítica pela direção (elementos do escopo) | Entradas/saídas tratadas | Ata/registro de análise crítica |

### D6 — Melhoria

| Código | Critério | Âncora L3 | Evidência mínima típica |
|---|---|---|---|
| `D6.C1` | Tratamento de não conformidades | Correção + registro | NC + correção |
| `D6.C2` | Ação corretiva com análise de causa | Ação proporcional ao impacto | AC + evidência de implementação |
| `D6.C3` | Verificação de eficácia | Eficácia confirmada ou retrabalho | Registro de eficácia |

Âncoras L1/L2/L4/L5 ficam no catálogo versionado do modelo (implementação); L3 é o limiar “em gestão” para calibração do MVP.

## 5. Aplicabilidade e “não aplicável”

| Valor `applicability` | Uso |
|---|---|---|
| `applicable` | Critério entra no cálculo |
| `not_applicable` | Excluído do denominador; **exige justificativa** e revisor |
| `insufficient_info` | Temporário em rascunho; **não** pode permanecer na versão aprovada do score |

Regras:

1. `not_applicable` só se o critério estiver fora do `AssessmentScope` ou for objetivamente impossível no contexto (ex.: `D4.C3` sem provedores externos no escopo).
2. Justificativa de N/A é texto obrigatório + ator; auditada.
3. Dimensão com **todos** os critérios N/A → dimensão omitida do agregado (não pontua 0 artificialmente).
4. IA pode **sugerir** N/A; humano confirma.

## 6. Cálculo e arredondamento

### 6.1 Score por critério

- Valor ∈ {1,2,3,4,5} se `applicable`.
- N/A → sem valor numérico.

### 6.2 Score por dimensão

\[
S_d = \frac{\sum s_c}{n_c}
\]

onde \(s_c\) são scores dos critérios `applicable` da dimensão \(d\), e \(n_c \ge 1\).

- Armazenar `dimension_score` com **2 casas decimais**.
- Arredondamento: **half-up** (0.005 → sobe).

### 6.3 Score global da avaliação

\[
S_g = \frac{\sum S_d}{n_d}
\]

sobre dimensões com pelo menos um critério aplicável.

- `global_score`: 2 casas, half-up.
- Relatório pode exibir também mediana e mínimo por dimensão (não substituem \(S_g\)).

### 6.4 Proibição

- Não ponderar dimensões no v0 (pesos = 1). Mudança de pesos = **nova versão** do modelo.
- Não completar lacunas com média imputada sem registro `insufficient_info` resolvido.

## 7. Evidência mínima

Para um critério ir a estado **revisado/aprovado** no score:

| Condição | Exigência |
|---|---|
| Nível ≥ 3 | ≥1 `Evidence` `approved` vinculada **ou** entrevista concluída com observação estruturada + flag de suficiência do avaliador |
| Nível ≥ 4 | Evidência de medição/uso de dados (não só declaração) |
| Nível 5 | Evidência de ciclo de melhoria (antes/depois ou série) |
| N/A | Justificativa; evidência opcional |

Vínculo: `MaturityScore` ↔ `Evidence` / `Finding` / `Answer` via links de rastreabilidade.

## 8. Versionamento do modelo

| Campo | Regra |
|---|---|
| `model_code` | `qmind_maturity_iso9001` |
| `model_version` | semver documental (`0.1.0` = este v0) |
| Imutabilidade | Avaliação referencia `(model_code, model_version)` congelados na criação/planejamento |
| Breaking change | Nova `model_version`; scores antigos não são reescritos |
| Changelog | Dimensões/critérios/âncoras/fórmulas alterados exigem entrada de histórico |

Entidade lógica: **MaturityModel** / **MaturityDimension** / **MaturityCriterion** (catálogo; pode ser global ou por `AssessmentModel`).

## 9. Ciclo de vida do pacote e revisão humana

Unidade versionada: **`MaturityAssessment`** (pacote), com linhas `MaturityScore` por critério. Máquina canônica: `001_State_Machines.md` §7.

| Estado do pacote | Significado |
|---|---|
| `draft` | Elaboração / sugestão de IA |
| `in_review` | Submetido |
| `approved` | Vigente para relatório (imutável) |
| `rejected` | Devolvido (mesmo `version_no` → `rework`) |
| `superseded` | Substituído por versão mais nova aprovada |
| `discarded` | Descarte auditável pré-aprovação |

Regras:

- `consultant_auditor` elabora e submete; `quality_manager` / `org_admin` aprovam com SoD.
- Sugestão de IA → apenas `draft`; nunca `approved`.
- **`approved` não sofre `reject`/`rework`.** Correção = evento `supersede` → novo pacote `draft` com `version_no+1`.
- Report que inclui maturidade referencia a versão **vigente** `approved` (ou snapshot da versão citada na publicação).

Auditoria: ator (user/service/system), de→para, correlação — ver dicionário.

## 10. Saídas para relatório

O relatório pode incluir:

- tabela dimensão × score;
- global \(S_g\);
- lista de N/A com justificativas;
- critérios abaixo do limiar acordado (ex.: &lt; 3);
- rastreio para constatações relacionadas (opcional).

## 11. Fora do v0

- Pesos por dimensão/critério.
- Benchmark entre organizações.
- Escalas não inteiras.
- Modelos setoriais paralelos (versão futura).
