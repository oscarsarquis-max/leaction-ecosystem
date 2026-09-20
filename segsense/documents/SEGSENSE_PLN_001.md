# SEGSENSE_PLN_001 — Plano de desenvolvimento orientado por prompts

## Controle

- Projeto: SegSense
- Documento: SEGSENSE_PLN_001
- Versão: 1.27
- Data: 15/09/2026
- Documento-base: SEGSENSE_ARQ_001 v0.4

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Plano sequencial original da fundação. |
| 1.1 | 04/09/2026 | Reconciliação com a área de saída: independência das três aplicações, PRM_012/013 revistos e registros de execução do workspace preservados. |
| 1.2 | 04/09/2026 | PRM_004 aprovado com ressalva (FK de ambiente) resolvida na V3 do PRM_005; oportunidade DRAFT local sem publicação. |
| 1.3 | 04/09/2026 | PRM_005 aprovado com quatro ressalvas de UI resolvidas no PRM_006; governança editorial local. |
| 1.4 | 04/09/2026 | Corretivo único PRM_006_COR_001: integridade SQL composta e submissão imutável. |
| 1.5 | 11/09/2026 | PRM_006 aprovado; PRM_007 executado (link contextual seguro, V7). |
| 1.6 | 11/09/2026 | Corretivo único PRM_007_COR_001: V8 (revisão aprovada + bindings) e HTTPS fail-closed. |
| 1.7 | 11/09/2026 | PRM_008 executado: sistema visual e página pública `/c/{token}`. |
| 1.8 | 11/09/2026 | PRM_009 executado: aviso versionado, instância local e manifestação. |
| 1.9 | 12/09/2026 | Corretivo único PRM_009_COR_001: V10, idempotência sem cache de segredo, justificativa persistida. |
| 1.10 | 12/09/2026 | PRM_010 ramo B: contrato externo ausente; V11; implementação executável bloqueada. |
| 1.12 | 12/09/2026 | PRM_012: home pública de posicionamento; pesquisa Icatu; mock conceitual. |
| 1.13 | 12/09/2026 | PRM_012_COR_001: hero compacto, linguagem comercial honesta, descoberta a partir do admin 401. |
| 1.14 | 13/09/2026 | PRM_013: MVP local SegSense→Spider→mock; fatia demo, não Satellite Contract. |
| 1.15 | 13/09/2026 | PRM_013_COR_001: contexto governado, segredos locais fail-closed, UX de reunião. Sem PRM_014. |
| 1.16 | 13/09/2026 | SPIDER-SAT-003: SegSense = EXPERIENCE SATELLITE; contrato canônico na Spider (DEMO ONLY). |
| 1.17 | 13/09/2026 | PRM_014 v1.1: jornada só com fatos observados; sem timer; preflight/ACL. Sem PRM_015. |
| 1.18 | 14/09/2026 | PRM_014 aprovado com ressalvas após COR_001. PRM_015: painel recortado ao V1 demo; prova isolada de provedor indisponível. Sem PRM_016. |
| 1.19 | 14/09/2026 | Único corretivo PRM_015_COR_001: encerramento seguro da stack demo (ledger, stop fail-closed). Sem PRM_016. |
| 1.20 | 14/09/2026 | PRM_016 reprogramado: jornada contextual de negócio. Indicadores adiados (sem renumeração silenciosa). ADR_005. Sem PRM_017. |
| 1.21 | 14/09/2026 | Único corretivo PRM_016_COR_001: bloqueio de contexto vazio, fingerprint V15, invalidação de UI, copy do ditado, stack isolada. Sem PRM_017. |
| 1.22 | 14/09/2026 | PRM_017 reprogramado: proveniência fiel e demo visual (`SEGSENSE_ADR_006`). Hardening amplo **adiado**, sem virar PRM_018. Sem PRM_018 nesta execução. |
| 1.23 | 14/09/2026 | PRM_017 encerrado **APROVADO COM RESSALVAS**. PRM_018 reprogramado: marca legível e aceite visual. E2E/piloto **adiado**, sem ser marcado como realizado. Sem PRM_019 nesta execução. |
| 1.24 | 14/09/2026 | PRM_018 encerrado **APROVADO COM RESSALVAS**. PRM_019: intenção livre, perguntas e cotação simulada calculada no mock. Sem PRM_020. |
| 1.25 | 15/09/2026 | Único corretivo `SEGSENSE_PRM_019_COR_001`: linguagem pública da cotação e gates completos. Sem PRM_020. |
| 1.26 | 15/09/2026 | PRM_020: captura real de URL, Satellite 1.2, capability agrícola demonstrativa. Sem PRM_021. |
| 1.27 | 15/09/2026 | Único corretivo `SEGSENSE_PRM_020_COR_001`: fidelidade semântica da extração (janela local + conteúdo principal). Sem PRM_021. Sem segundo corretivo. |

## 1. Modelo de trabalho

O desenvolvimento será conduzido por prompts sequenciais enviados ao Cursor. Um novo prompt somente poderá ser emitido depois que:

1. o Cursor concluir o prompt corrente;
2. a devolutiva completa for apresentada para análise;
3. as alterações e evidências forem avaliadas;
4. eventuais inconsistências forem corrigidas;
5. a etapa for formalmente aprovada.

Quando uma etapa não for aprovada, poderá ser emitido **um único prompt corretivo** vinculado ao mesmo número. Não será permitido um segundo prompt corretivo para a mesma etapa.

Se ainda houver problemas após a execução do corretivo único, a etapa será encerrada como `APROVADO COM RESSALVAS`. As pendências remanescentes serão registradas e suas orientações de correção serão incorporadas obrigatoriamente ao próximo prompt original da sequência, antes do novo escopo.

## 2. Gates obrigatórios

Cada devolutiva será avaliada quanto a:

- aderência ao prompt e à arquitetura;
- arquivos efetivamente criados ou alterados;
- preservação do trabalho anterior;
- builds, testes, lint e validações executados;
- evidências reais, sem resultados presumidos;
- segurança, privacidade e ausência de segredos;
- qualidade da documentação;
- pendências, riscos e dívida técnica introduzida;
- adequação da próxima etapa planejada.

Possíveis decisões:

- `APROVADO` — próximo prompt original liberado;
- `CORREÇÃO ÚNICA NECESSÁRIA` — emissão do único corretivo permitido;
- `APROVADO COM RESSALVAS` — após o corretivo, encerra a etapa e transporta as pendências para o próximo prompt original.

## 3. Sequência planejada

### SEGSENSE_PRM_001 — Ambiente inicial de desenvolvimento

Criação da fundação no workspace `leaction-ecosystem`: frontend, backend, services, database, execução local, PostgreSQL, healthchecks, testes básicos e README.

### SEGSENSE_PRM_002 — Arquitetura interna e convenções

Consolidação do SegSense como Insurance Reference Satellite: Satellite BFF, limites entre estado local e projeção Spider, Application Identity, esqueleto do Manifest, correlação, assincronia, referências documentais, padrões de código, erros, datas, auditoria e APIs. Não haverá chamada real à Spider.

### SEGSENSE_PRM_003 — Modelo de identidade e acesso

Fundação de autenticação e autorização, perfis iniciais, isolamento entre publicadores, trilha de auditoria e regras para dados sensíveis. O mecanismo concreto dependerá das capacidades já existentes no ecossistema.

### SEGSENSE_PRM_004 — Publicadores, canais e ambientes

Primeiro módulo funcional: cadastro e gestão de publicadores, canais e ambientes contextualizados, incluindo estados, validações, persistência, APIs, interface e testes. O módulo é exclusivamente local ao SegSense. Não envia dados à Spider, não consulta a Icatu e não implementa oportunidade contextual, link, jornada, intent, capability ou execução.

Esta etapa também registra a decisão posterior de independência física das três aplicações: SegSense, Spider e o Insurance Provider Mock futuro.

### SEGSENSE_PRM_005 — Oportunidade contextual e versionamento

Criação, consulta, edição versionada e histórico de oportunidades contextuais como rascunho editorial local (`DRAFT`). Não publica links, não interpreta contexto com IA, não recomenda seguro e não integra Spider/Icatu. A correção herdada da ressalva do PRM_004 (FK composta do ambiente) é obrigatória antes do novo escopo.

### SEGSENSE_PRM_006 — Governança e aprovação de publicação

Policies de publicação, papéis responsáveis, aprovação, pausa, expiração e revogação. Nenhuma oportunidade poderá ser publicada sem decisão real registrada.

### SEGSENSE_PRM_007 — Link contextual seguro

Geração e resolução de identificadores opacos, vigência, assinatura, prevenção de adulteração, revogação, correlação e proteção contra exposição de dados em URLs.

### SEGSENSE_PRM_008 — Experiência contextual do usuário

Página intermediária, apresentação do contexto, transparência, estados de carregamento e indisponibilidade, acessibilidade e continuidade da jornada, ainda sem integração real com seguradora.

### SEGSENSE_PRM_009 — Consentimento e coleta progressiva

Implementação de finalidade, transparência, consentimento versionado, minimização e coleta progressiva das informações estritamente necessárias. Incluirá revogação e trilha de evidências.

### SEGSENSE_PRM_010 — Contrato SegSense–Spider

Preparação documental da fronteira SegSense–Spider **sem interface fictícia**. A implementação do Satellite Contract canônico permanece bloqueada enquanto a Spider não publicar contrato externo executável (schema, versão, endpoint, autenticação, exemplos e testes). PRM_010 executou o ramo B: matriz `SEGSENSE_INT_001`, fronteira `SEGSENSE_ARQ_003`, ADR_003 e lista `SEGSENSE_REQ_002`. O SegSense continua funcional localmente. A integração HTTP real com a Spider permanece **adiada** (dependência externa, `SEGSENSE_REQ_002`). O identificador `SEGSENSE_PRM_011` foi **reprogramado** em 12/09/2026 para a âncora visual comercial e o backoffice de demonstrações; a integração Spider **não** foi realizada nem renumerada silenciosamente.

### SEGSENSE_PRM_011 — Âncora visual comercial e backoffice de demonstrações

Página pública `/demonstracao/icatu` (cenário demonstrativo não oficial) e módulo editorial `DemonstrationStory`. Sem integração Spider, Icatu ou mock. O PRM_011 original de integração Spider fica adiado.

### Integração com a Spider (identificador original do PRM_011 — adiado)

Implementação do adapter do SegSense para a Spider conforme o contrato aprovado. **Adiada** até publicação do contrato externo (`SEGSENSE_REQ_002`). Não foi marcada como realizada nem recebeu um identificador novo. O número `PRM_011` passou a designar a âncora visual e o backoffice editorial.

### SEGSENSE_PRM_012 — Posicionamento, pesquisa Icatu e contrato conceitual do mock

Entrada pública `/`, pesquisa verificável (`SRC_002`) e especificação não executável do Insurance Provider Mock (`MCK_001`). Sem implementação do mock. PRM_013 condicionado a contrato/evidência e à aprovação desta etapa.

### SEGSENSE_PRM_013 — MVP integrado de demonstração (Spider + mock ilustrativo)

Fatia **local** autorizada por `SEGSENSE_ADR_004`: SegSense → Spider → Insurance Provider Mock. O caminho canônico posterior é `SPIDER-SAT-003` (SegSense EXPERIENCE). Não é adapter Icatu. `SEGSENSE_ADR_003` continua a impedir que o SegSense invente o contrato.

### SEGSENSE_PRM_014 — Jornada baseada somente em fatos observados (Satellite Contract V1)

Versão 1.1 (13/09/2026): a UI só apresenta o que ocorreu e tem evidência. Remove o timer fictício herdado do PRM_013. Consome `SPIDER-SAT-003` sem contrato paralelo. Sem preview/callback/IdP. **Encerrado 14/09/2026: aprovado com ressalvas** após o único corretivo `SEGSENSE_PRM_014_COR_001`. Ressalvas herdadas (PID inseguro da prova mock-down; aceite visual aberto) entram no PRM_015.

### SEGSENSE_PRM_015 — Painel de evidências da jornada sintética (recorte)

O enunciado original pedia visão ponta a ponta (origem, contexto, consentimento, intent, policy, plano, capabilities, resolução, execução e resultado). **Esta execução recorta** ao que o Satellite Contract V1 `local-demo` expõe: painel “Evidências desta simulação” na rota pública já existente. Sem Intent pleno, CTX-004, Eligibility Gate, Data Plane, callback, IdP ou cotação. A ambição futura permanece neste plano; não foi desenhada como cumprida. Único corretivo `SEGSENSE_PRM_015_COR_001`: encerramento seguro da stack local. **Encerrado 14/09/2026: aprovado com ressalvas** (aceite visual não executado; demonstração de negócio insuficiente). Sem segundo corretivo.

### SEGSENSE_PRM_016 — Primeira jornada contextual de negócio utilizável (reprogramado)

Originalmente previsto para atribuição e indicadores. **Reprogramado em 14/09/2026** sem renumeração silenciosa (`SEGSENSE_ADR_005`): contexto mostrado → intenção declarada e confirmada → possibilidades ilustrativas da Spider/Test Double → explicação e pendências humanas. Sem URL pública arbitrária, sem schema V1 novo, sem cotação. Único corretivo `SEGSENSE_PRM_016_COR_001` (14/09/2026): servidor bloqueia contexto vazio, fingerprint canônico, invalidação de resultado na UI, copy honesta do ditado, prova HTTP em stack isolada. **Encerrado 14/09/2026: aprovado com ressalvas** (aceite visual aberto; proveniência do relato ainda mapeada para fixture governada — correção no PRM_017).

### Atribuição e indicadores (identificador original do PRM_016 — adiado)

Medição de publicação, visualização, manifestação de interesse, continuidade e resultados permitidos. Métricas comerciais e compartilhamento de dados respeitarão papéis, consentimento e contratos. **Adiada**; não foi marcada como realizada nem recebeu o número do PRM_017.

### SEGSENSE_PRM_017 — Proveniência fiel e demonstração visual da jornada contextual (reprogramado)

Originalmente previsto para segurança e conformidade. **Reprogramado em 14/09/2026** sem renumeração silenciosa (`SEGSENSE_ADR_006`): timestamps honestos, contribuições `USER_DECLARED` vs `SATELLITE_GOVERNED`, contrato 1.1 compatível, causalidade visível, stack isolada no ar para auditoria. Encerrado **APROVADO COM RESSALVAS** após `SEGSENSE_PRM_017_COR_001`. Hardening amplo **permanece adiado**.

### Segurança e conformidade (identificador original do PRM_017 — adiado)

Hardening da aplicação, revisão de autorização, isolamento, logs, retenção, segredos, dependências, proteção de links e callbacks e evidências técnicas para revisão jurídica e de segurança. **Adiada**; não foi marcada como realizada nem recebeu o número do PRM_018.

### SEGSENSE_PRM_018 — Marca legível e aceite visual transversal (reprogramado)

Originalmente previsto para testes ponta a ponta e piloto. **Reprogramado em 14/09/2026** sem apagar este histórico: acabamento visual transversal (logo perceptível em todas as superfícies) e aceite demonstrável na stack isolada. Encerrado **APROVADO COM RESSALVAS**. Ditado real, convite vigente e piloto amplo **não** foram verificados.

### Testes ponta a ponta e piloto (identificador original do PRM_018 — adiado)

Automação dos cenários críticos, indisponibilidades e retomadas; validação do ambiente contextual de demonstração; acessibilidade, desempenho básico e evidências da jornada completa. **Adiada**; não foi marcada como realizada nem recebeu o número do PRM_019.

### SEGSENSE_PRM_019 — Intenção livre, perguntas e cotação simulada

Pedido do patrocinador após ver a tela: texto livre de intenção, perguntas de complemento, prêmio em R$ calculado no mock demonstrativo. **Não** é cotação Icatu. Corretivo único `SEGSENSE_PRM_019_COR_001` executado. `SEGSENSE_PRM_020` executado; corretivo único `SEGSENSE_PRM_020_COR_001` nesta etapa. Sem PRM_021. Sem segundo corretivo do 020.

### SEGSENSE_PRM_020 em diante

Planejado após auditoria do PRM_019. Integração plena continua condicionada a `SEGSENSE_REQ_002`.

### Preparação para implantação (identificador original do PRM_019 — adiado)

Configurações por ambiente, observabilidade, runbooks, backup, recuperação, migração, rollback e checklist de liberação. **Não** foi realizada nesta execução; o PRM_019 vigente entregou intenção livre e cotação simulada. Deploy não será executado sem autorização específica.

## 4. Dependências que podem alterar a sequência

- estrutura real do workspace `leaction-ecosystem`;
- contratos e catálogo de capabilities da Spider;
- documentação, credenciais e sandbox da Icatu;
- definição dos papéis regulatórios dos participantes;
- modelo de autenticação já usado no ecossistema;
- canal escolhido para o primeiro piloto;
- regras de consentimento, atribuição e compartilhamento de dados.

Quando uma dependência não estiver disponível, a etapa correspondente não será preenchida com suposições. O plano será reordenado ou a etapa será limitada à especificação formal.

## 5. Controle do prompt corretivo único

O primeiro envio de uma etapa usará `SEGSENSE_PRM_NNN`, versão 1.0.

Caso necessário, será admitida somente uma revisão corretiva:

- `SEGSENSE_PRM_004`, versão 1.0;
- `SEGSENSE_PRM_004`, versão 1.1 — único prompt corretivo permitido.

Não será criada a versão 1.2 para nova correção da mesma etapa.

Depois da devolutiva da versão 1.1:

1. se tudo estiver correto, a etapa será `APROVADA`;
2. se restarem problemas, a etapa será `APROVADA COM RESSALVAS`;
3. cada ressalva será registrada com evidência, impacto e orientação;
4. o próximo prompt original começará com uma seção obrigatória chamada `Correções herdadas da etapa anterior`;
5. somente depois dessas correções o próximo prompt tratará de seu novo escopo;
6. a validação do próximo prompt deverá comprovar tanto as correções herdadas quanto as novas entregas.

## 6. Requisitos de qualidade dos prompts

Como existe apenas uma oportunidade de correção por etapa, cada prompt original deverá:

- declarar contexto, objetivo, escopo e exclusões;
- identificar documentos e contratos que precisam ser lidos;
- indicar arquivos e módulos afetados;
- explicitar regras funcionais e arquiteturais;
- proibir suposições e integrações fictícias;
- definir estados, erros e comportamentos de indisponibilidade;
- exigir preservação do trabalho existente;
- estabelecer testes e evidências verificáveis;
- incluir critérios objetivos de aceite;
- exigir relatório final padronizado;
- antecipar riscos de compatibilidade e regressão;
- incorporar todas as ressalvas transportadas da etapa anterior.

## 7. Situação de execução (workspace)

Registros já realizados neste workspace **não** foram apagados. A sequência da área de saída foi incorporada, inclusive a decisão de independência das três aplicações.

| Etapa | Situação |
|---|---|
| SEGSENSE_PRM_001 | Aprovado com ressalvas após o corretivo único (`SEGSENSE_PRM_001_COR_001`) |
| SEGSENSE_PRM_002 | Aprovado sem necessidade de corretivo |
| SEGSENSE_PRM_003 | Aprovado sem necessidade de corretivo |
| SEGSENSE_PRM_004 | Aprovado com ressalva; ressalva de FK composta resolvida pela V3 no PRM_005 |
| SEGSENSE_PRM_005 | Aprovado com quatro ressalvas de UI; resolvidas no PRM_006 |
| SEGSENSE_PRM_006 | Aprovado; corretivo único `SEGSENSE_PRM_006_COR_001` (V6, submissão imutável) |
| SEGSENSE_PRM_007 | Executado; corretivo único `SEGSENSE_PRM_007_COR_001` (V8, HTTPS fail-closed) |
| SEGSENSE_PRM_008 | Aprovado com ressalvas; correções herdadas no PRM_009 |
| SEGSENSE_PRM_009 | Aprovado com ressalvas após `SEGSENSE_PRM_009_COR_001` |
| SEGSENSE_PRM_010 | Executado; ramo B (contrato externo ausente); aprovado com ressalva visual |
| SEGSENSE_PRM_011 | Aprovado com ressalvas; integração Spider **adiada**. Corretivo PRM_011 **não** consumido. |
| SEGSENSE_PRM_012 | Executado; corretivo único `SEGSENSE_PRM_012_COR_001`; aprovado com ressalvas. Sem segundo corretivo. |
| SEGSENSE_PRM_013 | Executado; corretivo único `SEGSENSE_PRM_013_COR_001`; **não** autoaprovado. Contrato pleno **não** implementado. Sem avanço ao PRM_014 neste corretivo. |
| SEGSENSE_PRM_014 | Aprovado com ressalvas após `SEGSENSE_PRM_014_COR_001`. Sem segundo corretivo. |
| SEGSENSE_PRM_015 | Aprovado com ressalvas após `SEGSENSE_PRM_015_COR_001`. Sem segundo corretivo. |
| SEGSENSE_PRM_016 | Executado (jornada contextual reprogramada); único corretivo `SEGSENSE_PRM_016_COR_001`; **aprovado com ressalvas**. Indicadores originais **adiados**. |
| SEGSENSE_PRM_017 | Executado (proveniência/demo visual reprogramados); **não** autoaprovado. Sem PRM_018. Hardening original **adiado**. |
| SEGSENSE_PRM_018 | Encerrado **aprovado com ressalvas**. Marca perceptível; E2E/piloto adiado. |
| SEGSENSE_PRM_019 | Encerrado após COR_001 com ressalva bloqueante de URL pública. |
| SEGSENSE_PRM_020 | Executado; corretivo único `SEGSENSE_PRM_020_COR_001` nesta etapa; **não** autoaprovado. Sem PRM_021. Sem segundo corretivo. |

## 8. Independência das três aplicações

| Aplicação | Natureza | Pertence à Spider? |
|---|---|---|
| SegSense | Produto satélite no monorepo; runtime, banco, frontend e ciclo de vida próprios | Não. “Satellite” é padrão de integração |
| Spider | Plataforma independente; fatia demo SegSense só em `local-demo` | — |
| Insurance Provider Mock | Aplicação irmã `segsense-provider-mock/` (porta 8095) | Não. Tampouco é módulo interno do SegSense |

Nenhum código, módulo, banco, runtime ou deployment do SegSense ou do mock pertence à Spider. A fatia `local-demo` em `spider/` é alteração **mínima e isolada**, nomeada `SEGSENSE_*`, e **não** implementa o Satellite Contract.
