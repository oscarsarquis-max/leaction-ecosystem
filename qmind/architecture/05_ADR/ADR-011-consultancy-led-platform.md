# ADR-011 — Entrada por consultorias com propriedade dos dados pela organização

- Status: Aceito
- Data: 2026-08-04
- Responsáveis: produto e arquitetura QMind
- Afeta: roadmap, identidade, autorização, cobrança e experiência multiempresa
- Não altera: baseline `mvp-fullstack-v0`, isolamento por `Organization` e propriedade das evidências

## Contexto

O QMind pode evoluir por dois caminhos principais: ferramenta de produtividade para consultores e auditores ou SGQ SaaS abrangente para organizações. O primeiro possui aderência direta ao MVP construído e tende a permitir validação comercial mais rápida. O segundo oferece expansão maior, porém exige muitos módulos recorrentes que ainda não foram validados.

Existe uma oportunidade de combinar os caminhos: a consultoria introduz o QMind no cliente; a organização participa do projeto e pode assumir a continuidade posteriormente.

## Decisão

Adotar uma estratégia **consultancy-led B2B2B**:

- consultores e empresas de consultoria são o foco comercial inicial;
- cada organização atendida continua sendo o tenant e proprietária dos seus dados;
- a consultoria opera por acesso delegado, explícito, limitado e revogável;
- a organização pode continuar no QMind após o projeto;
- capacidades de SGQ recorrente serão adicionadas somente após validação de uso e pagamento;
- o QMind não se posicionará como organismo certificador.

## Limites de domínio

Será estudado um agregado `ConsultancyWorkspace` para representar equipe, método, templates e portfólio da consultoria.

Ele deverá permanecer separado de `Organization`:

```text
ConsultancyWorkspace
  ├── ConsultancyMembership
  ├── MethodTemplate
  └── ConsultancyOrganizationGrant ──→ Organization
                                          └── dados e evidências do cliente
```

`ConsultancyOrganizationGrant` deverá registrar organização, consultoria, finalidade, escopo, validade, estado, concessor, aceite, revogação e auditoria.

## Invariantes

1. A consultoria não se torna proprietária dos dados do cliente.
2. Templates não contêm evidências ou conteúdo identificável de organizações.
3. Revogar acesso não apaga autoria histórica.
4. Toda consulta continua restrita à organização ativa.
5. Acesso ao portfólio não permite consulta transversal ao conteúdo técnico.
6. Handoff e exportação preservam histórico e responsabilidades.
7. Papéis de consultoria e auditoria independente não são equivalentes.
8. Cobrança não altera autorização nem isolamento.

## Alternativas consideradas

### SGQ empresarial completo como entrada

Não adotado agora. Exigiria gestão documental abrangente, indicadores, fornecedores, reclamações e operação contínua antes de validar aquisição e retenção.

### Ferramenta exclusiva do consultor, com dados pertencentes à consultoria

Rejeitada. Dificultaria participação, continuidade, portabilidade e confiança da organização avaliada.

### Marketplace de consultores

Adiado. Introduziria reputação, pagamentos, disputas e governança fora do problema central.

### Venda exclusiva por organização

Permanece possível no futuro, mas não será o canal principal do primeiro piloto.

## Consequências positivas

- Forte aderência ao MVP existente.
- Ciclo inicial de validação mais curto.
- Distribuição por profissionais que atendem múltiplas organizações.
- Caminho natural de expansão para receita recorrente do cliente.
- Preservação do isolamento e da confiança.

## Consequências negativas e riscos

- Comprador, usuário e proprietário dos dados podem ser atores diferentes.
- Convite, consentimento, revogação e handoff exigem boa experiência.
- Cobrança por consultoria e continuidade do cliente precisam evitar duplicidade.
- Consultorias podem pedir personalizações difíceis de reutilizar.
- Papéis acumulados podem gerar conflitos de imparcialidade.

## Mitigações

- Contratos e estados explícitos para concessão de acesso.
- Templates versionados sem dados de cliente.
- Planos e limites padronizados antes de customizações.
- Auditoria de convites, acessos, exportações e revogações.
- Separação entre consultor, auditor interno e auditor independente.
- Piloto com métricas e critérios de continuidade.

## Impacto técnico imediato

Nenhuma migração ou implementação será iniciada apenas por este ADR. Primeiro serão realizadas entrevistas e um piloto de processo. O modelo de domínio, máquinas de estado, matriz de papéis, dicionário e DDL receberão uma emenda versionada antes do código.

## Critérios para implementação

- Entrevistas confirmam necessidade multiempresa da consultoria.
- Pelo menos um piloto exige colaboração entre consultoria e cliente.
- Propriedade, aceite, revogação e exportação são aprovados.
- Unidade de cobrança candidata é definida.
- Ameaças de acesso transversal são revisadas.
- Emenda documental do domínio é aceita e testável.

## Referências internas

- `../04_Docs/012_Business_Model_and_Product_Focus.md`
- `../04_Docs/013_Discovery_and_Pilot_Plan.md`
- `ADR-002-isolamento-multiempresa.md`
- `ADR-006-autenticacao-e-autorizacao.md`
- `ADR-010-homologacao-economica-ec2.md`

