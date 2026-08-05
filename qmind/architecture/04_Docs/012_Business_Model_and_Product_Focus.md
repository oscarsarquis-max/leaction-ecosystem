# QMind — Modelo de negócio e foco do produto

- Status: Aceito
- Data: 2026-08-04
- Baseline técnico: `mvp-fullstack-v0`
- Decisão arquitetural relacionada: `../05_ADR/ADR-011-consultancy-led-platform.md`
- Próximo ciclo: `013_Discovery_and_Pilot_Plan.md`

## 1. Decisão executiva

O QMind será lançado como uma **plataforma de diagnóstico, auditoria e melhoria contínua para consultorias e seus clientes**.

O foco comercial inicial será o consultor ou a empresa de consultoria, que busca reduzir o tempo gasto na preparação, execução, consolidação e entrega de avaliações. A organização avaliada permanecerá como proprietária dos seus dados e poderá assumir a continuidade do workspace após o projeto.

O QMind não será posicionado, nesta fase, como um SGQ corporativo completo nem como organismo certificador.

## 2. Modelo de entrada no mercado

### Comprador inicial

- Consultor independente.
- Empresa de consultoria em sistemas de gestão.
- Equipe que realiza diagnósticos e auditorias internas para clientes.

### Usuários operacionais

- Consultores e auditores.
- Gestores da qualidade.
- Responsáveis por processos e ações.
- Auditores convidados com acesso temporário e restrito.

### Beneficiário e possível comprador futuro

A organização atendida recebe diagnóstico, evidências organizadas, constatações, maturidade, plano de ação e relatório rastreável. Ao fim do projeto, poderá contratar a continuidade para acompanhar ações, novas avaliações e evolução do sistema de gestão.

## 3. Proposta de valor inicial

O QMind reduz o trabalho administrativo da consultoria ao oferecer um fluxo único:

```text
Preparação → Entrevistas → Evidências → Constatações
→ Maturidade → Plano de ação → Relatório → Acompanhamento
```

Os ganhos a validar no piloto são:

- menor tempo entre trabalho de campo e entrega do relatório;
- menor retrabalho para relacionar evidências e requisitos;
- maior consistência entre profissionais da mesma consultoria;
- melhor rastreabilidade das conclusões;
- continuidade das ações pela organização cliente;
- reutilização segura de método e templates, nunca de dados de clientes.

## 4. Modelo B2B2B

```text
QMind
  ↓ assinatura e suporte
Consultoria
  ↓ cria e conduz projetos
Organizações clientes
  ↓ recebem acesso e resultados
Continuidade opcional após o projeto
```

A consultoria poderá operar múltiplas organizações. A relação não altera a fronteira de segurança: cada organização continuará isolada e nenhum dado poderá ser reutilizado entre clientes.

## 5. Princípios de propriedade e acesso

1. A organização avaliada é proprietária dos seus dados de negócio e evidências.
2. A consultoria recebe acesso delegado, limitado ao contrato e aos projetos autorizados.
3. Método, templates e materiais próprios da consultoria permanecem de sua titularidade.
4. Dados de uma organização não podem compor templates reutilizáveis.
5. Encerrado o vínculo, o acesso da consultoria pode ser revogado sem apagar autoria e auditoria históricas.
6. A organização deve conseguir exportar seus dados e relatórios em formatos definidos.
7. Transferência, continuidade e descarte devem seguir contrato, retenção e legislação aplicável.
8. Acesso de auditor externo deve ser temporário, restrito e auditado.

## 6. Ofertas comerciais a validar

### Profissional

- Um ou poucos usuários.
- Limite de organizações ou avaliações ativas.
- Fluxo completo de avaliação e relatório.

### Consultoria

- Equipe e portfólio de clientes.
- Métodos e templates versionados.
- Identidade visual e relatórios personalizados.
- Indicadores operacionais da consultoria sem exposição cruzada de clientes.

### Continuidade da organização

- Acompanhamento de ações.
- Preservação do histórico.
- Novas avaliações e evolução de maturidade.
- Expansão futura para capacidades recorrentes de SGQ, condicionada à validação comercial.

Valores, limites e unidade de cobrança não estão decididos. O piloto deverá comparar cobrança por usuário, organização ativa, avaliação ou combinação desses elementos.

## 7. Escopo prioritário

### Manter e aprimorar

- Gestão multiempresa para consultores.
- Avaliações, entrevistas e checklists adaptáveis.
- Evidências vinculadas a requisitos e perguntas.
- Constatações, maturidade, ações e relatórios.
- Separação de responsabilidades e auditoria.
- Uso em campo, responsividade e evolução offline.
- Templates reutilizáveis sem dados de clientes.
- Handoff da consultoria para a organização.
- Governança e controle de custo da IA.

### Adiar até validação

- Gestão documental corporativa completa.
- Gestão geral de indicadores do SGQ.
- Reclamações, fornecedores e ocorrências operacionais abrangentes.
- Portal permanente para todos os colaboradores.
- Marketplace de consultores.
- Automação autônoma de decisões técnicas.
- Infraestrutura de alta disponibilidade sem demanda comprovada.

## 8. Implicações para o produto

O novo limite de domínio a avaliar é `ConsultancyWorkspace`, responsável por equipe, métodos e relações delegadas com organizações. Ele não substitui `Organization` nem se torna proprietário de evidências do cliente.

Capacidades candidatas:

- portfólio de organizações e projetos;
- `ConsultancyMembership`;
- `ConsultancyOrganizationGrant` com validade, escopo e revogação;
- templates versionados e isolados de dados de cliente;
- convite e aceite da organização;
- encerramento e handoff;
- identidade visual por consultoria;
- medição de uso, armazenamento e IA.

Qualquer implementação dependerá da descoberta descrita em `013_Discovery_and_Pilot_Plan.md`.

## 9. Imparcialidade e posicionamento

- O QMind apoia consultoria, diagnóstico e auditoria; não concede certificação.
- O sistema deve identificar o tipo de trabalho e o papel exercido.
- Acesso de auditor independente não deve herdar permissões de consultoria.
- Potenciais conflitos e acumulação de papéis devem ser visíveis e auditáveis.
- Comunicações comerciais não podem prometer conformidade ou certificação automática.

## 10. Estratégia de IA e informações

- Banco de dados, S3 e arquivos versionados são as fontes persistentes.
- Prompts recebem apenas o contexto necessário para a tarefa.
- Conversas completas não são reenviadas por padrão.
- Resumos estruturados e resultados revisados podem ser persistidos.
- Modelos menores devem atender tarefas simples quando a qualidade for suficiente.
- Cada caso de uso terá limite de tokens, custo e frequência.
- Custos serão medidos por organização, projeto e funcionalidade.
- Cache só será usado quando seguro, autorizado e compatível com a versão das fontes.

Tokens de autenticação OIDC continuam necessários e não devem ser armazenados de forma insegura.

## 11. Estratégia de infraestrutura

Durante descoberta e piloto, a prioridade será custo fixo mínimo e operação simples, conforme ADR-010:

- servidor Ubuntu Linux simples;
- aplicação e serviços consolidados quando seguro;
- S3 para evidências e backups;
- crescimento de infraestrutura condicionado a uso e risco medidos;
- ALB, ECS, RDS e alta disponibilidade preservados como evolução futura, não como requisito de entrada.

## 12. Relação com a ISO 9001

O produto inicia com o catálogo ISO 9001:2015 autorizado. Como os referenciais e modelos são versionados, uma nova edição será introduzida como nova versão, preservando avaliações históricas. A transição normativa deverá ser tratada como oportunidade de produto, com roteiro e conteúdo licenciados antes da disponibilização.

## 13. Indicadores de validação

- Tempo de preparação por avaliação.
- Tempo entre fim do campo e relatório publicado.
- Horas economizadas por profissional.
- Número de organizações ativas por consultoria.
- Percentual de projetos concluídos integralmente no QMind.
- Taxa de convite e participação do cliente.
- Percentual de clientes que continuam após o projeto.
- Disposição a pagar e modelo de preço preferido.
- Armazenamento e custo de IA por avaliação.
- Satisfação do consultor e da organização.

Metas serão definidas após a linha de base das entrevistas e do primeiro piloto.

## 14. Critérios de expansão para SGQ SaaS

A expansão para um SGQ corporativo será considerada quando houver evidência conjunta de:

1. clientes usando o QMind após o encerramento da consultoria;
2. demanda recorrente por uma mesma capacidade de manutenção;
3. disposição a pagar por assinatura própria;
4. retenção e frequência de uso suficientes;
5. capacidade operacional e segurança compatíveis;
6. benefício superior ao aumento de escopo e suporte.

Pedidos isolados não serão suficientes para transformar o roadmap.

## 15. Decisões ainda abertas

- Unidade e faixas de cobrança.
- Limites dos planos.
- Propriedade inicial do workspace quando criado pela consultoria.
- Termos de convite, aceite, handoff e exportação.
- Regras de identidade visual e domínio personalizado.
- Escopo offline do primeiro piloto.
- Primeiros casos de uso pagos de IA.

