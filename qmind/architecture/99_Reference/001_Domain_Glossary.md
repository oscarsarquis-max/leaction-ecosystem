# QMind — Glossário de domínio

- Status: Aceito
- Data: 2026-08-03
- Congelamento: `domain-docs-v0`
- Aceite: `../04_Docs/006_Domain_Acceptance_Checklist.md`
- Uso: linguagem ubíqua para docs, API, UI e esquema de dados
- Não reproduz texto protegido de normas; definições são **operacionais do produto**

## 1. Estrutura avaliável

### Requisito (`Requirement`)
Item avaliável de um referencial versionado (`StandardVersion`), identificado por código estável. No QMind é a âncora de rastreabilidade para escopo, evidências e constatações. Pode ter hierarquia (pai/filho).

### Critério (`Criterion`)
Unidade de julgamento dentro de um `AssessmentModel` (ou do modelo de maturidade), com enunciado operacional e, quando mapeado, vínculo a um ou mais requisitos. Serve para pontuar ou decidir conformidade em linguagem de avaliação, não para substituir o texto normativo.

### Pergunta (`Question`)
Prompt estruturado usado em entrevista ou checklist, tipicamente ligado a um critério. Coleta resposta (`Answer`); por si só não é constatação.

---

## 2. Evidência e julgamento

### Evidência objetiva (`Evidence`)
Artefato ou registro verificável (documento, registro de sistema, foto controlada, medição, etc.) que sustenta análise. No QMind: metadados + objeto armazenado; só após `approved` (pós-quarentena) embasa constatação de conformidade. `legal_hold` é **flag** ortogonal ao estado (não um estado da máquina).

### Constatação (`Finding`)
Conclusão técnica documentada sobre o atendimento a requisito(s) no escopo da avaliação, com tipo, texto, vínculos a requisito e base conforme o tipo (ver máquinas §4.1), sujeita a revisão humana.

### Conformidade
Julgamento de que a prática observada atende ao esperado **com evidência positiva aprovada**. No QMind, `finding_type=conformity` **exige** ≥1 Evidence `approved`; flag `insufficient_evidence` é proibida.

### Não conformidade (NC)
Julgamento de falha em atender requisito aplicável, sustentada por evidência aprovada **ou**, quando a ausência/falha de evidência exigida é o próprio achado, por `insufficient_evidence` justificada. Exige tratamento proporcional (correção e, quando cabível, ação corretiva).

### Oportunidade de melhoria (OM)
Constatação que **não** configura NC, mas identifica potencial de aprimoramento. Exige evidência aprovada ou registro de entrevista; **não** usa `insufficient_evidence` como única base.

---

## 3. Tratamento e eficácia

### Correção
Ação imediata para eliminar uma não conformidade **detectada** (conter/reparar o problema imediato). Não pressupõe, por si, eliminação da causa.

### Ação corretiva
Ação para eliminar a **causa** de uma não conformidade e evitar recorrência, proporcional ao impacto. No QMind materializa-se tipicamente como `ActionItem` ligado a Finding de NC, com implementação, validação e, quando exigida, verificação de eficácia.

### Eficácia
Demonstração de que a ação corretiva (ou conjunto de ações) produziu o resultado pretendido — em especial a não recorrência ou o controle sustentado da causa. No fluxo: estados `validated` → `confirm_efficacy` → `done` (ou `fail_efficacy`).

---

## 4. Ciclos de trabalho

### Avaliação (`Assessment`)
Ciclo completo no QMind que agrega escopo, equipe, coleta, constatações, maturidade, plano de ação e relatório. Gênero que cobre diagnósticos e auditorias conduzidos na plataforma.

### Auditoria
Avaliação com propósito de verificar conformidade (e eficácia do SG) de forma sistemática, independente e documentada, segundo critérios definidos. No produto: `Assessment.type` adequado (ex. auditoria interna) com disciplina de evidência e constatação.

### Diagnóstico
Avaliação orientada a retrato de maturidade/gaps e prioridades de melhoria, podendo ser menos formal que uma auditoria de certificação, porém ainda sujeita a rastreabilidade e revisão humana no QMind.

---

## 5. Maturidade e aplicabilidade

### Maturidade
Grau, em escala definida pelo `MaturityModel` versionado, em que práticas do SG no escopo estão estabelecidas, geridas, medidas e otimizadas. Expressa-se em scores por critério/dimensão/global; **não** equivale automaticamente a “conforme”.

### Aplicabilidade
Determinação de se um requisito, critério ou item de maturidade entra na avaliação do escopo. Valores operacionais: `applicable`, `not_applicable` (com justificativa), e em rascunho `insufficient_info` (não permanece na versão aprovada).

---

## 6. Termos correlatos (remissões)

| Termo | Ver |
|---|---|
| Organização / tenant | `000_Domain_Model.md`, ADR-002 |
| Sugestão de IA | ADR-008; nunca conclusão aprovada |
| Plano de ação / item | `001_State_Machines.md` §5 |
| Relatório | `001_State_Machines.md` §6 |
| Papéis (auditor, GQ…) | `002_Roles_and_Permissions.md` |

## 7. Fora deste glossário

Definições legais de LGPD, texto integral ISO, jargão exclusivo de um cliente. Extensões setoriais entram em versões futuras do glossário.
