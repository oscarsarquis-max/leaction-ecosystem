# SPIDERBANK-ADR-001
## Definição do Produto, Fronteiras e Arquitetura do Banco de Crédito

**Status:** DRAFT — para discussão e aprovação explícita nesta conversa  
**Versão:** 0.4  
**Data:** 14 de setembro de 2026  
**Responsabilidade de análise:** análise de TI especializada em crédito bancário  
**Base:** contextualização inicial, esclarecimentos do usuário sobre a imagem ilustrativa e definição do diretório do projeto. Inspeção inicial de Git e pastas realizada em 14 de setembro de 2026; contratos e código ainda não foram validados.

## 1. Propósito e decisão central

Spider é a plataforma contextual horizontal. SpiderBank é o produto Banco de Crédito, concebido como Experience Satellite independente, construído sobre o Spider.

SpiderBank parte da necessidade do cliente e tem como horizonte a experiência de crédito ao longo de originação, processamento e análise, liberação e desembolso, conectada aos sistemas de administração do crédito por meio do Spider.

A denominação Banco de Crédito expressa a direção do produto. Este documento não estabelece condição regulatória, autorização operacional ou prontidão para produção.

## 2. ICP e usuários iniciais

**Proposta ainda não aprovada:** pequenas empresas com necessidades de capital de giro relacionadas a caixa, estoque e atendimento de pedidos. Segmentos, porte e atuação geográfica permanecem em aberto.

Usuários propostos: cliente empresarial, representante autorizado e participantes internos de análise e operação, conforme jornadas e permissões definidas. A necessidade de experiências internas está reconhecida; sua cobertura inicial ainda será discutida.

CampoAberto e o contexto agro são referências aproveitáveis, sem determinar especialização exclusiva em crédito rural.

## 3. Domínio e referência do processo de crédito

A imagem fornecida é meramente ilustrativa. Sua parte inferior está fora desta análise, conforme orientação do usuário.

| Elemento da imagem | Interpretação adotada |
|---|---|
| Barra verde acima das colunas | Spider, com responsabilidade de estruturação e execução governada ao longo do processo. |
| Colunas de fases | Originação; processamento e análise; liberação e desembolso. |
| Blocos dentro das colunas | Subdomínios do processo de crédito em cada fase. |
| Última coluna | Sistemas de administração do crédito a serem vinculados à plataforma. |

Fase, subdomínio, Business Capability e sistema são conceitos distintos. Um subdomínio pode requerer diversas capabilities. O sistema que as executa é determinado posteriormente pela resolução do Spider.

Os blocos da figura não constituem inventário de implementação nem autorização para integrar sistemas. A figura não define sequência universal, fornecedores, contratos ou uso obrigatório de IA.

O produto distinguirá necessidade, objetivo confirmado, elegibilidade, possibilidade, simulação, proposta, aprovação e contratação. Cada marco exige evidência correspondente; uma simulação não equivale a aprovação.

## 4. Jornadas e recorte inicial

O horizonte de produto abrange as fases de crédito representadas na imagem. A primeira fatia proposta continua sendo uma experiência que parte da necessidade:

1. **Contexto:** cliente informa ou revisa sua situação, com origem e dados relevantes compreensíveis.
2. **Objetivo confirmado:** cliente confirma o que deseja resolver.
3. **Possibilidades:** apresentação condicionada ao resultado correspondente recebido do Spider.
4. **Explicação e próximos passos:** resultado, limitações e pendências efetivamente disponíveis.

Quando realmente declarado pelo usuário, o objetivo utiliza `objective.origin = USER_DECLARED`, sujeito à validação do contrato existente.

| Situação | Comportamento esperado |
|---|---|
| `MISSING_CONTEXT` | Solicitar informações necessárias que estejam faltando. |
| `AMBIGUOUS` | Solicitar esclarecimento sem presumir interpretação. |
| `POLICY_REJECTED` | Comunicar bloqueio e explicação permitida. |
| Executor indisponível | Informar indisponibilidade sem fabricar alternativas. |
| Pendência humana | Apresentar encaminhamento e acompanhamento somente quando suportados. |

Os códigos e formatos serão confrontados com o contrato real. Este ADR não cria novos códigos de API. Jornadas detalhadas por fase serão documentadas antes da implementação correspondente.

## 5. Responsabilidades do SpiderBank

SpiderBank conhece cliente, experiência e domínio de crédito. Será responsável por frontend, BFF, configuração e ciclo de vida próprios; coleta de contexto permitido; confirmação do objetivo; validações de entrada e acesso da aplicação; interações contratuais; apresentação fiel de resultados e dados próprios necessários à experiência.

### 5.1. Localização e organização física definidas pelo usuário

O diretório definido é **`C:\Projetos\spider-bank`**. A estrutura de pastas seguirá a referência existente em `C:\Projetos\segsense`.

| Pasta | Finalidade no SpiderBank |
|---|---|
| `backend/` | BFF e responsabilidades de backend do satélite. |
| `frontend/` | Experiência própria do produto. |
| `database/` | Migrações e seeds quando houver persistência necessária. |
| `documents/` | Documentação do projeto, decisões, especificações e evidências. |
| `scripts/` | Rotinas de desenvolvimento, operação local e verificação. |
| `services/` | Organização das integrações contratuais permitidas com o Spider. |

Subpastas estruturais observadas na referência incluem `backend/src`, `frontend/src`, `frontend/images`, `database/migrations`, `database/seeds`, `documents/evidencias`, `documents/references` e `services/spider-integration`.

Pastas geradas, dependências, logs, segredos e conteúdo específico de seguros não serão copiados. A existência de `services/icatu-integration` no SegSense não constitui autorização para criar essa integração no SpiderBank. A organização de pastas não implica copiar o código ou adotar automaticamente todas as tecnologias da referência.

Uma nova inspeção, solicitada pelo usuário, confirmou que `C:\Projetos\spider-bank` existe e está vazia, incluindo a verificação de itens ocultos. A divergência observada na inspeção inicial está resolvida.

Persistência própria será adotada quando necessária. SpiderBank não será um módulo interno do Spider Core e não escolherá providers, routes, adapters, Intent canônico ou Execution Plan.

## 6. Responsabilidades do Spider

Spider mantém a autoridade sobre a cadeia:

**Contexto + objetivo → normalização/interpretação → Intent Contract → Policy/Guard → Execution Plan → Business Capabilities → Capability Resolution → execução → resultado.**

A IA é opcional antes do Intent Contract. Entradas suficientes podem seguir sem LLM. Entradas insuficientes ou ambíguas exigem complementação.

A partir da representação canônica, o processamento é governado e determinístico. Resultados externos podem variar conforme dados e disponibilidade; regras, entradas e decisões devem permitir rastreabilidade.

Contexto e objetivo não substituem capabilities e não serão encaminhados diretamente a sistemas.

## 7. Satellite Contract

Referência informada: Satellite Contract V1, versão `1.0`, endpoint `POST /v1/satellites/interactions`, identificado na contextualização como `SPIDER-SAT-003 — VERIFIED`. Essa condição foi informada pelo usuário e ainda não foi verificada no repositório nesta conversa.

SpiderBank terá papel `EXPERIENCE`. Declarará identidade, objetivo, contexto permitido, finalidade, proveniência, correlação e classificação aplicável.

Antes de implementar, verificar campos, registro, autenticação, autorização, respostas, erros, reenvios e suporte a acompanhamento. Lacunas exigem discussão contratual; não autorizam chamadas diretas a providers.

SegSense é referência estrutural de independência e integração, sem cópia indiscriminada de código, domínio ou identidade visual.

## 8. Aquisição de contexto

Fontes contempladas: `DIRECT_ENTRY`, `CONTEXTUAL_LINK` e `SATELLITE_CONTEXT`.

A entrada direta é a prioridade inicial proposta. O mecanismo Contextual Link, incluindo `/go`, permanece aproveitável conforme inspeção de compatibilidade. SpiderBank não depende exclusivamente de CampoAberto.

Todas as fontes preservam finalidade, proveniência e classificação. Conteúdo externo é dado sem autoridade para alterar políticas ou execução. URLs não autorizam buscas arbitrárias. Ditado local pode ser considerado sem pressupor envio de áudio ao backend.

## 9. Business Capabilities

As necessidades conceituais incluem identificar cliente, verificar cadastro, conhecer perfil, compreender finalidade, consultar compromissos, avaliar elegibilidade, encontrar alternativas, simular condições e encaminhar análise humana.

Essa relação não é um catálogo implementado. Antes de criar capabilities, confrontar o Business Capability Catalog real do Spider, registrando adequação, entradas, saídas e lacunas. Novas capacidades dependem de necessidade demonstrada.

Capabilities expressam o que precisa ser feito. Regras canônicas de planejamento não serão duplicadas no BFF.

## 10. Providers e sistemas administradores

Fluxo obrigatório: **SpiderBank → Spider → Capability Resolution → executor/provider → Spider → SpiderBank.**

Os sistemas da última coluna da imagem representam potenciais participantes da execução e administração do crédito. Seus contratos, atribuições e integrações ainda precisam ser identificados. A figura não determina correspondência de um sistema para cada capability.

Providers recebem somente os dados necessários à execução. Seleção e adaptação ficam fora do SpiderBank. A troca de executor deve preservar a semântica principal do BFF e da experiência, respeitando os resultados suportados.

Nenhum provider de crédito é definido por este ADR. ServiceNow permanece possibilidade futura. Não há autorização para presumir integrações com instituições financeiras. Mocks autorizados serão identificados como ilustrativos, sem disponibilidade financeira real.

## 11. Segurança e governança

Aplicam-se finalidade, necessidade, minimização, classificação, integridade, auditabilidade e controle de acesso. A identidade declarada pelo satélite requer validação confiável; permissões da aplicação não substituem políticas do Spider.

Credenciais de providers ficam fora do frontend. Logs devem permitir correlação evitando conteúdo sensível desnecessário. Retenção, jurisdição e requisitos de operação real precisam de definição específica antes de mudança de escopo.

## 12. Dados e autoridade

| Componente | Responsabilidade |
|---|---|
| SpiderBank | Estado da experiência, contexto coletado, confirmação do objetivo e referências necessárias ao acompanhamento. |
| Spider | Representações canônicas e evidências de políticas, planos, resolução e execução, conforme sua arquitetura. |
| Executor/provider | Dados e resultados sob sua responsabilidade na capacidade executada. |

Projeções mantidas no SpiderBank não se tornam autoridade sobre decisões de execução ou condições financeiras. Correções do cliente devem gerar interação rastreável e preservar a relação com resultados anteriores quando necessário.

## 13. Persistência

Persistência será introduzida por necessidade demonstrada. Cada conjunto de dados terá finalidade, autoridade, acesso, retenção e tratamento de exclusão definidos.

**Não persistir conteúdo desnecessário. Preservar a evidência necessária.**

Não armazenar indiscriminadamente textos, páginas ou payloads completos. Trusted Evidence, blockchain, Merkle Tree e ledger não integram a arquitetura atual implementada.

## 14. Explicabilidade

A experiência deve comunicar necessidade e objetivo considerados, informações relevantes, resultado efetivo, alcance, limitações, pendências e próximos passos reais.

SpiderBank traduz explicações do Spider para linguagem do cliente sem inventar justificativas. Taxa, limite, carência, validade, produto e demais condições somente serão exibidos quando sustentados pelo resultado correspondente. Detalhes técnicos ficam recolhidos e sujeitos às permissões apropriadas.

## 15. Limites e consequências

Permanecem `SIMULATED_INFRASTRUCTURE` e `MOCK_ONLY` até mudança formal. Este ADR não autoriza produção, contratação, desembolso ou integração externa real.

Execution Eligibility permanece proposto e não implementado. Trusted Evidence também permanece não implementado. Não haverá reconstrução indiscriminada de capacidades bancárias maduras nem migração automática do legado.

A independência implica configuração e ciclo de vida próprios e gestão de compatibilidade contratual. Possibilidades dependem das capacidades e executores disponíveis, e a interface deve representar essa dependência honestamente.

## 16. Roadmap

1. **Discussão e aprovação do ADR:** confirmar ICP, recorte inicial, usuários e limites.
2. **Inspeção e inventário:** verificar branch, HEAD, working tree e alterações locais; localizar eventual SpiderBank independente; inspecionar contratos, catálogo e referências estruturais. Não sobrescrever trabalho nem alterar projetos irmãos.
3. **Classificação do legado:** componentes, regras, assets, testes, fluxos, contexto, integrações e documentação em REUTILIZAR, ADAPTAR, DESCARTAR ou MIGRAR. Classificar como DESCARTAR não autoriza exclusão imediata.
4. **Primeiro prompt de implementação:** somente após definição aprovada e inspeção, com escopo, dependências, lacunas e critérios verificáveis.
5. **Primeira jornada independente:** entrada direta, objetivo confirmado, integração contratual e apresentação fiel dos resultados e exceções.
6. **Evolução por fases:** detalhar subdomínios e expandir jornadas conforme capacidades disponíveis e decisões aprovadas.

Critérios da primeira fatia: independência da aplicação, contrato canônico, ausência de chamada direta a providers e correspondência verificável entre execução e conteúdo apresentado.

## 17. Método de trabalho e documentação

Conforme orientação do usuário, a assistência nesta conversa atuará como analista de TI especializado em crédito bancário.

Definições, discussões relevantes, decisões e implementações serão registradas em documentos próprios ou em revisões dos documentos pertinentes. Os documentos de trabalho serão apresentados na área lateral da conversa.

O fluxo documental é **DRAFT → discussão nesta conversa → APPROVED → implementação/publicação autorizada**. Criar e abrir um rascunho na área lateral é parte da elaboração; não significa publicação externa ou aprovação do conteúdo.

Novas propostas permanecem identificadas como propostas. Registros de implementação distinguirão o que foi executado, o que foi verificado e o que permanece pendente. Aprovação de uma revisão não aprova automaticamente futuras alterações.

A conversa é a fonte de verdade para raciocínio, arquitetura, crítica e aprovação. O ambiente de desenvolvimento apoia inspeção, arquivos, testes e código quando necessários.

## 18. Pendências de decisão

- Confirmar ICP e recorte inicial de capital de giro.
- Confirmar prioridade de entrada direta.
- Definir alcance inicial da experiência de participantes internos.
- Detalhar jornadas e subdomínios das fases antes das respectivas implementações.
- Aprovar explicitamente este ADR antes de implementar.

## Histórico de revisões

| Versão | Registro |
|---|---|
| 0.1 | DRAFT inicial apresentado na conversa, com definição do produto e arquitetura. |
| 0.2 | Incorporação da interpretação da imagem, abrangência das fases de crédito e orientação para documentação na área lateral; consolidação em arquivo próprio. |
| 0.3 | Registro do diretório definido pelo usuário, estrutura de pastas observada no SegSense e inspeção inicial do monorepo. |
| 0.4 | Nova inspeção confirma que `C:\Projetos\spider-bank` existe e está vazia; pendência de localização resolvida. |

## Inspeção inicial do ambiente — 14 de setembro de 2026

- Monorepo acessível em `C:\Projetos`.
- Branch observada: `feat/spider-sat-003-segsense`.
- HEAD observado: `4fb3712` — `feat(spider,segsense): add Satellite Contract V1 and honest experience journey`.
- Working tree contém alterações e arquivos não rastreados, inclusive no Spider e no SegSense, além de alterações em projetos irmãos. Nenhum desses arquivos foi modificado por esta atividade.
- A estrutura principal de pastas do SegSense foi inspecionada; o código e o contrato não foram auditados.
- Nenhuma pasta ou arquivo do projeto SpiderBank foi criado nesta etapa. Apenas este DRAFT foi atualizado na área de entregáveis da conversa.

**Status vigente: DRAFT. Nenhuma implementação realizada nesta etapa.**

## Apêndice — inspeção de ciclo (17 de setembro de 2026)

Não altera o status DRAFT nem aprova o ADR. Registro de verificação ao reabrir o ciclo:

- `C:\Projetos\spider-bank` continua vazio (este arquivo em `documents/` é o único artefato criado neste ciclo).
- SegSense: pastas `backend`, `frontend`, `database`, `documents`, `scripts`, `services`. Existe `services/icatu-integration` — **não** copiar para o SpiderBank.
- SPIDER-SAT-003 **verificado** no repositório: `POST /v1/satellites/interactions`, papel `EXPERIENCE`, `contractVersion` 1.0, boundary `SIMULATED_INFRASTRUCTURE` / `MOCK_ONLY`. Documento: `spider/docs/architecture/SPIDER-SATELLITE-CONTRACT-V1.md`.
- Spider branch `feat/spider-sat-003-segsense`, HEAD `5ee7756` (o ADR 0.4 citava `4fb3712`). Working tree sujo em Spider, SegSense e projetos irmãos — não sobrescrito.
- Tensão a discutir: ADR prioriza `DIRECT_ENTRY`; o contrato V1 não aceita `DIRECT_ENTRY` como prova governada (exige `SATELLITE_GOVERNED` + `SERVER_REGISTRY`).
- Nenhum provider de crédito no catálogo atual; o mock vigente é de seguros. A primeira jornada de crédito ainda não tem executor ilustrativo próprio.
