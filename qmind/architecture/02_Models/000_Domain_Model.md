# QMind — Modelo de domínio conceitual (v0)

- Status: Aceito
- Data: 2026-08-03
- Congelamento: `domain-docs-v0`
- Base: visão do produto, ADRs 001–009 Aceitos, confronto monorepo
- Glossário canônico: `../99_Reference/001_Domain_Glossary.md`
- Aceite: `../04_Docs/006_Domain_Acceptance_Checklist.md`
- Escopo: **conceitual** — ainda sem esquema físico nem código

## 1. Objetivo

Descrever as entidades, relacionamentos e invariantes do fluxo principal da ISO 9001:2015 no QMind, de forma que o esquema de dados e os casos de uso possam ser derivados sem ambiguidade crítica.

## 2. Linguagem ubíqua (trecho)

Definições operacionais completas no glossário. Resumo:

| Termo | Significado no QMind |
|---|---|
| Organização | Tenant / cliente; fronteira de isolamento (`organization_id`) |
| Requisito / Critério / Pergunta | Camadas do referencial → modelo de avaliação → coleta (glossário §1) |
| Evidência objetiva | Artefato verificável; só `approved` embasa constatação aprovada |
| Constatação | Conformidade, NC, oportunidade ou observação — com revisão humana |
| Correção / ação corretiva / eficácia | Tratamento de NC e verificação de resultado (glossário §3) |
| Avaliação / auditoria / diagnóstico | Ciclo `Assessment` e seus tipos (glossário §4) |
| Maturidade / aplicabilidade | Scores versionados; N/A justificado (ver `003_Maturity_Model.md`) |
| Sugestão de IA | Saída assistida, nunca conclusão aprovada |

## 3. Contextos e agregados principais

Alinhado ao ADR-001:

```text
Identidade          Organizações         Referenciais
     \                   |                    |
      \                  v                    v
       ---------->  Processos  <---- Requisitos / Critérios
                         |
                         v
                    Avaliações
                    /    |    \
           Entrevistas Evidências  Escopo
                    \    |    /
                     Constatações
                          |
               Maturidade + Planos de ação
                          |
                       Relatórios
                          |
                 Assistência de IA (transversal)
                 Auditoria da plataforma (transversal)
```

## 4. Entidades e atributos mínimos

Todos os registros de negócio de cliente possuem **`organization_id`** (obrigatório). Identificadores externos: **UUID**.

### 4.1 Identidade e acesso

- **User** — identidade global (sub do IdP / Cognito).
- **Membership** — `(user_id, organization_id, roles[], status, valid_from/to)`.
- **Role** — administrador_plataforma | administrador_organização | consultor_auditor | gestor_qualidade | responsavel_processo | responsavel_acao | leitor.

### 4.2 Organizações

- **Organization** — nome, status, fuso, política de retenção padrão.
- **Unit** — organização pai, nome, tipo.
- **PersonContact** (opcional) — contato na organização, sem substituir User.

### 4.3 Referenciais

- **Standard** — código (ex. ISO 9001), título.
- **StandardVersion** — versão (2015), status, vigência.
- **Requirement** — versão do padrão, código, enunciado autorizado, hierarquia/pai.
- **AssessmentModel** — conjunto versionado de critérios/perguntas ligados a requisitos.
- **Criterion / Question** — texto, tipo de resposta, requisito(s) aplicável(is).

> Textos normativos protegidos não são reproduzidos sem licença; o modelo guarda referências e conteúdo autorizado.

### 4.4 Processos

- **OrgProcess** — nome, dono, unidade, interação com outros processos, aplicabilidade.

### 4.5 Avaliações

- **Assessment** — organização, modelo/versão, tipo (`diagnosis` \| `internal_audit` \| `other`), status do ciclo, `maturity_model_id` opcional congelado, datas, equipe.
- **AssessmentScope** — processos e/ou requisitos incluídos.
- **Interview** — avaliação, entrevistados, data, modo (presencial/remoto).
- **Answer / Observation** — entrevista, pergunta/critério, conteúdo, autor.

Máquina: `001_State_Machines.md` §2.

### 4.6 Evidências

- **Evidence** — metadados (ADR-007): tipo, hash, classificação, retenção, estado de quarentena/aprovação, versão.
- **EvidenceLink** — evidência ↔ requisito | pergunta | constatação | ação.
- Objeto binário fora do banco (S3); imutabilidade após uso em constatação/relatório publicado (nova versão).

### 4.7 Constatações

- **Finding** — `finding_type` (`conformity` \| `nonconformity` \| `opportunity` \| `observation`), severidade, requisito(s), evidência(s), texto, status (`draft → in_review → approved → rejected` / `withdrawn`).

### 4.7b Maturidade

- **MaturityModel / Dimension / Criterion** — catálogo versionado (`003_Maturity_Model.md`).
- **MaturityAssessment** — pacote por avaliação (status de revisão humana, `global_score`).
- **MaturityScore** — por critério: `applicability`, `level` 1–5, justificativa, vínculos de evidência mínima.

### 4.8 Ações

- **ActionPlan** — avaliação origem, status.
- **ActionItem** — `action_kind` (`correction` \| `corrective_action` \| `improvement`), responsável, prazo, status, validação, eficácia.

### 4.9 Relatórios

- **Report** — avaliação, versão, status (`draft → in_review → published`), conteúdo estruturado + artefato; pode incorporar maturidade aprovada.
- Publicação exige revisão humana; rastro de autoria e versão.

### 4.10 IA e auditoria da plataforma

- **AiSuggestion** — caso de uso, proveniência (ADR-008), estado (`suggested → accepted | edited | rejected`).
- **PlatformAuditEvent** — ator, organização, ação, recurso, correlação, resultado.

### 4.11 Trabalhos assíncronos

- **Job** — tipo (relatório, varredura, extração, IA), estado (`queued → running → succeeded | failed | cancelled`), organização, solicitante, payload versionado, erro.

## 5. Relacionamentos críticos (rastreabilidade)

```text
StandardVersion 1──* Requirement
AssessmentModel *──* Requirement / Criterion
Organization 1──* OrgProcess
Organization 1──* Assessment
Assessment *──* OrgProcess          (escopo)
Assessment 1──* Interview
Interview 1──* Answer
Assessment 1──* Evidence
Evidence *──* Requirement
Assessment 1──* Finding
Finding *──* Evidence
Finding *──* Requirement
Assessment 1──* MaturityAssessment (versionado; um vigente) 1──* MaturityScore
Assessment 1──* ActionPlan 1──* ActionItem
Assessment 1──* Report
AiSuggestion *──> Finding | Report | Interview | MaturityScore (como rascunho)
```

Invariante central: **constatação aprovada com requisito aplicável e base conforme o tipo** — conformidade exige evidência positiva `approved`; insuficiência só onde a máquina §4.1 permite.

Invariante de maturidade: **pacote `approved` imutável (correção = nova versão); sem `insufficient_info`; N/A justificado; scores ≠ conformidade**.

## 6. Invariantes de isolamento e segurança

1. Toda entidade de negócio carrega `organization_id` não nulo.
2. FKs não cruzam organizações.
3. Contexto de organização vem da associação autenticada, nunca só do body.
4. Evidência, índice e prompt de IA herdam e filtram pela mesma organização.
5. Sugestão de IA não altera Finding/Report sem ato humano auditado.
6. Membership revogada remove acesso imediato; autoria histórica permanece.

## 7. Fluxo de domínio do MVP (ISO 9001:2015)

1. Criar Organization (+ Membership do consultor).
2. Cadastrar OrgProcess relevantes.
3. Selecionar StandardVersion + AssessmentModel autorizados.
4. Abrir Assessment com AssessmentScope.
5. Conduzir Interview / Answer; anexar Evidence (quarentena → aprovada).
6. Elaborar Finding e MaturityScore com revisão.
7. Gerar ActionPlan / ActionItem.
8. Produzir Report em rascunho → revisão → publicação.
9. (Opcional) AiSuggestion em etapas 5–8, sempre revisável.

## 8. Fora deste documento

- DDL / migrações físicas (`03_Database`).
- Contratos OpenAPI (`01_Prompts` / especificação futura).
- Conteúdo literal da norma sem licença.
- UI e wireframes.

## 9. Próximos refinamentos

1. Domínio documental **Aceito** / congelado em `domain-docs-v0` (ver checklist).
2. DDL v0 + migração inicial (próximo passo físico).
3. Ampliar âncoras L1–L5 no seed do catálogo de maturidade.
4. Emendas pós-congelamento = nova versão documental (não editar silenciosamente o Aceito).

## Referências

- `../00_Architecture/000_Project_Vision.md`
- `../00_Architecture/001_System_Architecture.md`
- `../04_Docs/004_Initial_Backlog.md`
- `../04_Docs/005_Monorepo_Confrontation.md`
- `../04_Docs/006_Domain_Acceptance_Checklist.md`
- `../05_ADR/` (001–009 Aceitos)
