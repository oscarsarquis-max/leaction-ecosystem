# Documentos oficiais do SegSense

Índice da pasta `documents/` no produto `segsense/` do monorepo `leaction-ecosystem`. Identificadores existentes não devem ser renomeados nem movidos.

Fontes arquiteturais vigentes:

- domínio SegSense: [`SEGSENSE_ARQ_001.md`](SEGSENSE_ARQ_001.md) (v0.4), [`SEGSENSE_ARQ_002.md`](SEGSENSE_ARQ_002.md) (v1.6), [`SEGSENSE_ARQ_003.md`](SEGSENSE_ARQ_003.md)
- padrão satélite Spider: [`references/SPIDER-ARCH-017.md`](references/SPIDER-ARCH-017.md)

SegSense, Spider e o Insurance Provider Mock futuro são aplicações fisicamente independentes. “Satellite” é padrão de integração, não incorporação.

| Identificador | Título | Versão | Situação | Caminho |
|---|---|---|---|---|
| SEGSENSE_ARQ_001 | Proposta Inicial e Arquitetura de Referência | 0.4 | Em elaboração | [`SEGSENSE_ARQ_001.md`](SEGSENSE_ARQ_001.md) |
| SEGSENSE_ARQ_002 | Arquitetura lógica e fronteiras de componentes | 1.6 | Vigente nesta etapa | [`SEGSENSE_ARQ_002.md`](SEGSENSE_ARQ_002.md) |
| SEGSENSE_ARQ_003 | Fronteira preparada SegSense–Spider (sem conexão operacional) | 1.0 | Preparado documentalmente; implementação bloqueada | [`SEGSENSE_ARQ_003.md`](SEGSENSE_ARQ_003.md) |
| SEGSENSE_ADR_001 | Icatu como executor resolvido pela Spider | 1.1 | Aceita | [`SEGSENSE_ADR_001.md`](SEGSENSE_ADR_001.md) |
| SEGSENSE_ADR_002 | Autenticação desacoplada de provedor e ausência de identidade fictícia | 1.0 | Aceita | [`SEGSENSE_ADR_002.md`](SEGSENSE_ADR_002.md) |
| SEGSENSE_ADR_003 | Não inventar Satellite Contract no SegSense | 1.0 | Aceita; consumo do contrato publicado pela Spider (SAT-003) autorizado | [`SEGSENSE_ADR_003.md`](SEGSENSE_ADR_003.md) |
| SEGSENSE_ADR_004 | Autorização e fronteira do MVP integrado de demonstração | 1.0 | Autoriza PRM_013; addendum SAT-003 (EXPERIENCE) | [`SEGSENSE_ADR_004.md`](SEGSENSE_ADR_004.md) |
| SEGSENSE_API_001 | Convenções HTTP do Satellite BFF | 1.3 | Vigente nesta etapa | [`SEGSENSE_API_001.md`](SEGSENSE_API_001.md) |
| SEGSENSE_API_002 | Contratos do catálogo administrativo | 1.0 | Vigente nesta etapa | [`SEGSENSE_API_002.md`](SEGSENSE_API_002.md) |
| SEGSENSE_API_003 | Contratos de oportunidade contextual | 1.0 | Vigente nesta etapa | [`SEGSENSE_API_003.md`](SEGSENSE_API_003.md) |
| SEGSENSE_API_004 | Governança e autorização de publicação | 1.0 | Vigente nesta etapa | [`SEGSENSE_API_004.md`](SEGSENSE_API_004.md) |
| SEGSENSE_API_005 | Links contextuais e resolução pública | 1.2 | Vigente nesta etapa | [`SEGSENSE_API_005.md`](SEGSENSE_API_005.md) |
| SEGSENSE_API_006 | Aviso de finalidade e instância contextual pública | 1.1 | Vigente nesta etapa | [`SEGSENSE_API_006.md`](SEGSENSE_API_006.md) |
| SEGSENSE_DOM_001 | Linguagem de domínio do catálogo local | 1.1 | Vigente nesta etapa | [`SEGSENSE_DOM_001.md`](SEGSENSE_DOM_001.md) |
| SEGSENSE_DOM_002 | Oportunidade contextual e versionamento | 1.2 | Vigente nesta etapa | [`SEGSENSE_DOM_002.md`](SEGSENSE_DOM_002.md) |
| SEGSENSE_DAT_001 | Modelo relacional do catálogo local | 1.1 | Vigente nesta etapa | [`SEGSENSE_DAT_001.md`](SEGSENSE_DAT_001.md) |
| SEGSENSE_DAT_002 | Persistência da correção V3 e da oportunidade V4 | 1.0 | Vigente nesta etapa | [`SEGSENSE_DAT_002.md`](SEGSENSE_DAT_002.md) |
| SEGSENSE_DAT_003 | Persistência da governança V5+V6 | 1.1 | Vigente nesta etapa | [`SEGSENSE_DAT_003.md`](SEGSENSE_DAT_003.md) |
| SEGSENSE_DAT_004 | Persistência V7–V8 dos links contextuais | 1.1 | Vigente nesta etapa | [`SEGSENSE_DAT_004.md`](SEGSENSE_DAT_004.md) |
| SEGSENSE_DAT_005 | Persistência V9–V11 de aviso, instância e evidência | 1.2 | Vigente nesta etapa | [`SEGSENSE_DAT_005.md`](SEGSENSE_DAT_005.md) |
| SEGSENSE_INT_001 | Evidência do Satellite Contract externo versus artefatos internos | 1.0 | Snapshot 12/09; addendum SAT-003 PUBLIC_EXECUTABLE (DEMO ONLY) | [`SEGSENSE_INT_001.md`](SEGSENSE_INT_001.md) |
| SEGSENSE_REQ_002 | Condições objetivas para o contrato externo Satellite → Spider | 1.0 | Parcialmente satisfeito por SAT-003; preview/IdP/Data Plane ausentes | [`SEGSENSE_REQ_002.md`](SEGSENSE_REQ_002.md) |
| SEGSENSE_FUN_002 | Finalidade, transparência e manifestação versionada | 1.1 | Vigente nesta etapa | [`SEGSENSE_FUN_002.md`](SEGSENSE_FUN_002.md) |
| SEGSENSE_LNK_001 | Link contextual seguro | 1.2 | Vigente nesta etapa | [`SEGSENSE_LNK_001.md`](SEGSENSE_LNK_001.md) |
| SEGSENSE_GOV_001 | Governança editorial e autorização de publicação | 1.2 | Vigente nesta etapa | [`SEGSENSE_GOV_001.md`](SEGSENSE_GOV_001.md) |
| SEGSENSE_UX_001 | Arquitetura de informação e experiência inicial (padrão Panne) | 1.1 | Vigente; identidade em UX_002 | [`SEGSENSE_UX_001.md`](SEGSENSE_UX_001.md) |
| SEGSENSE_UX_002 | Sistema visual, tokens e componentes de interface | 1.0 | Aprovado e implementado no PRM_008 | [`SEGSENSE_UX_002.md`](SEGSENSE_UX_002.md) |
| SEGSENSE_UX_003 | Arquitetura de navegação, fluxos e wireframes | 1.0 | Aprovado e implementado no PRM_008 | [`SEGSENSE_UX_003.md`](SEGSENSE_UX_003.md) |
| SEGSENSE_UI_001 | Arquitetura implementada do frontend | 1.2 | Vigente nesta etapa | [`SEGSENSE_UI_001.md`](SEGSENSE_UI_001.md) |
| SEGSENSE_SEC_001 | Fundação de segurança, ameaças e identidade futura | 1.4 | Vigente nesta etapa | [`SEGSENSE_SEC_001.md`](SEGSENSE_SEC_001.md) |
| SEGSENSE_SEC_002 | Threat model do link contextual | 1.1 | Vigente nesta etapa | [`SEGSENSE_SEC_002.md`](SEGSENSE_SEC_002.md) |
| SEGSENSE_SEC_003 | Threat model da instância e da manifestação | 1.1 | Vigente nesta etapa | [`SEGSENSE_SEC_003.md`](SEGSENSE_SEC_003.md) |
| SEGSENSE_PLN_001 | Plano de desenvolvimento orientado por prompts | 1.17 | Vigente | [`SEGSENSE_PLN_001.md`](SEGSENSE_PLN_001.md) |
| SEGSENSE_PRM_001 | Criação do ambiente inicial de desenvolvimento | 1.0 | Executado; corretivo documental aplicado | [`SEGSENSE_PRM_001.md`](SEGSENSE_PRM_001.md) |
| SEGSENSE_PRM_001_COR_001 | Correção documental da fundação | 1.1 | Executado | [`SEGSENSE_PRM_001_COR_001.md`](SEGSENSE_PRM_001_COR_001.md) |
| SEGSENSE_PRM_002 | Arquitetura interna e convenções | 1.0 | Executado | [`SEGSENSE_PRM_002.md`](SEGSENSE_PRM_002.md) |
| SEGSENSE_PRM_003 | Fundação de segurança, identidade e autorização | 1.0 | Executado | [`SEGSENSE_PRM_003.md`](SEGSENSE_PRM_003.md) |
| SEGSENSE_PRM_004 | Publicadores, canais e ambientes | 1.0 | Aprovado com ressalva; resolvida na V3 | [`SEGSENSE_PRM_004.md`](SEGSENSE_PRM_004.md) |
| SEGSENSE_PRM_005 | Oportunidade contextual e versionamento | 1.0 | Aprovado com ressalvas; resolvidas no PRM_006 | [`SEGSENSE_PRM_005.md`](SEGSENSE_PRM_005.md) |
| SEGSENSE_PRM_006 | Governança, aprovação e ativação de publicação | 1.0 | Aprovado | [`SEGSENSE_PRM_006.md`](SEGSENSE_PRM_006.md) |
| SEGSENSE_PRM_006_COR_001 | Correção única de integridade da governança | 1.1 | Aprovado | [`SEGSENSE_PRM_006_COR_001.md`](SEGSENSE_PRM_006_COR_001.md) |
| SEGSENSE_PRM_007 | Link contextual seguro e resolução controlada | 1.0 | Executado; corretivo único aplicado | [`SEGSENSE_PRM_007.md`](SEGSENSE_PRM_007.md) |
| SEGSENSE_PRM_007_COR_001 | Correção única do vínculo aprovado e HTTPS | 1.1 | Executado nesta etapa | [`SEGSENSE_PRM_007_COR_001.md`](SEGSENSE_PRM_007_COR_001.md) |
| SEGSENSE_PRM_008 | Sistema visual e experiência pública contextual | 1.0 | Aprovado com ressalvas; herdadas no PRM_009 | [`SEGSENSE_PRM_008.md`](SEGSENSE_PRM_008.md) |
| SEGSENSE_PRM_009 | Consentimento versionado e coleta progressiva local | 1.0 | Executado; corretivo único aplicado | [`SEGSENSE_PRM_009.md`](SEGSENSE_PRM_009.md) |
| SEGSENSE_PRM_009_COR_001 | Correção única da instância contextual | 1.1 | Executado nesta etapa; não autoaprovado | [`SEGSENSE_PRM_009_COR_001.md`](SEGSENSE_PRM_009_COR_001.md) |
| SEGSENSE_PRM_010 | Preparação do contrato SegSense–Spider sem interface fictícia | 1.0 | Executado; ramo B; aprovado com ressalva visual | [`SEGSENSE_PRM_010.md`](SEGSENSE_PRM_010.md) |
| SEGSENSE_PRM_011 | Âncora visual comercial e backoffice de demonstrações | 1.0 | Aprovado com ressalvas; corretivo não consumido | [`SEGSENSE_PRM_011.md`](SEGSENSE_PRM_011.md) |
| SEGSENSE_PRM_012 | Posicionamento, pesquisa Icatu e mock conceitual | 1.1 | Executado; não autoaprovado | [`SEGSENSE_PRM_012.md`](SEGSENSE_PRM_012.md) |
| SEGSENSE_PRM_012_COR_001 | Correção única da âncora comercial | 1.0 | Executado nesta etapa; não autoaprovado | [`SEGSENSE_PRM_012_COR_001.md`](SEGSENSE_PRM_012_COR_001.md) |
| SEGSENSE_PRM_013 | MVP integrado sintético SegSense–Spider–mock | 1.0 | Executado; corretivo único aplicado; não autoaprovado | [`SEGSENSE_PRM_013.md`](SEGSENSE_PRM_013.md) |
| SEGSENSE_PRM_013_COR_001 | Corretivo único do MVP integrado para reunião | 1.0 | Executado nesta etapa; não autoaprovado | [`SEGSENSE_PRM_013_COR_001.md`](SEGSENSE_PRM_013_COR_001.md) |
| SEGSENSE_PRM_014 | Jornada baseada somente em fatos observados sobre o Satellite Contract V1 | 1.1 | Executado nesta etapa; não autoaprovado | [`SEGSENSE_PRM_014.md`](SEGSENSE_PRM_014.md) |
| SEGSENSE_REV_014 | Revisão de aderência do PRM_014 | 1.0 | Executado; não autoaprovado; sem PRM_015 | [`SEGSENSE_REV_014.md`](SEGSENSE_REV_014.md) |
| SEGSENSE_JRN_EVID_001 | Matriz de estados da UI e fontes observáveis | 1.0 | Vigente nesta etapa | [`SEGSENSE_JRN_EVID_001.md`](SEGSENSE_JRN_EVID_001.md) |
| SEGSENSE_SAT_V1_ADERENCIA_001 | Matriz de consumo do SPIDER-SAT-003 | 1.0 | Consumo; não é contrato concorrente | [`SEGSENSE_SAT_V1_ADERENCIA_001.md`](SEGSENSE_SAT_V1_ADERENCIA_001.md) |
| SEGSENSE_REV_001 | Revisão de aderência da fundação ao ARQ_001 e ao SPIDER-ARCH-017 | 1.2 | Concluída | [`SEGSENSE_REV_001.md`](SEGSENSE_REV_001.md) |
| SEGSENSE_REV_002 | Revisão de aderência do PRM_002 | 1.0 | Concluída | [`SEGSENSE_REV_002.md`](SEGSENSE_REV_002.md) |
| SEGSENSE_REV_003 | Revisão de aderência do PRM_003 | 1.1 | Concluída | [`SEGSENSE_REV_003.md`](SEGSENSE_REV_003.md) |
| SEGSENSE_REV_004 | Revisão de aderência do PRM_004 | 1.1 | Concluída; ressalva resolvida na V3 | [`SEGSENSE_REV_004.md`](SEGSENSE_REV_004.md) |
| SEGSENSE_REV_005 | Revisão de aderência do PRM_005 | 1.0 | Concluída; ressalvas de UI resolvidas no PRM_006 | [`SEGSENSE_REV_005.md`](SEGSENSE_REV_005.md) |
| SEGSENSE_REV_006 | Revisão de aderência do PRM_006 | 1.1 | Concluída nesta execução | [`SEGSENSE_REV_006.md`](SEGSENSE_REV_006.md) |
| SEGSENSE_REV_007 | Revisão de aderência do PRM_007 | 1.1 | Concluída nesta execução | [`SEGSENSE_REV_007.md`](SEGSENSE_REV_007.md) |
| SEGSENSE_REV_008 | Revisão de aderência do PRM_008 | 1.0 | Concluída nesta execução | [`SEGSENSE_REV_008.md`](SEGSENSE_REV_008.md) |
| SEGSENSE_REV_009 | Revisão de aderência do PRM_009 | 1.1 | Corretivo único executado | [`SEGSENSE_REV_009.md`](SEGSENSE_REV_009.md) |
| SEGSENSE_REV_010 | Revisão de aderência do PRM_010 | 1.0 | Executado; ramo B; etapa não autoaprovada | [`SEGSENSE_REV_010.md`](SEGSENSE_REV_010.md) |
| SEGSENSE_REV_011 | Revisão de aderência do PRM_011 | 1.0 | Aprovado com ressalvas | [`SEGSENSE_REV_011.md`](SEGSENSE_REV_011.md) |
| SEGSENSE_REV_012 | Revisão de aderência do PRM_012 | 1.1 | Corretivo único executado; etapa não autoaprovada | [`SEGSENSE_REV_012.md`](SEGSENSE_REV_012.md) |
| SEGSENSE_REV_013 | Revisão de aderência do PRM_013 | 1.2 | COR_001 + addendum SAT-003; etapa não autoaprovada | [`SEGSENSE_REV_013.md`](SEGSENSE_REV_013.md) |
| SEGSENSE_MVP_001 | Inventário e riscos do MVP integrado | 1.0 | Inventário pré-código do PRM_013 | [`SEGSENSE_MVP_001.md`](SEGSENSE_MVP_001.md) |
| SEGSENSE_DEMO_CONTRACT_001 | Fatia demo SegSense↔Spider (anti-corrupção) | segsense-demo-contract-v1 | Deprecated; caminho canônico = SPIDER-SAT-003 | [`SEGSENSE_DEMO_CONTRACT_001.md`](SEGSENSE_DEMO_CONTRACT_001.md) |
| SEGSENSE_MOCK_CONTRACT_001 | Contrato do Insurance Provider Mock | segsense-mock-contract-v1 | Executável só no mock irmão | [`SEGSENSE_MOCK_CONTRACT_001.md`](SEGSENSE_MOCK_CONTRACT_001.md) |
| SEGSENSE_DEMO_RUN_001 | Roteiro de reunião local | 1.3 | Fatos observados; preflight obrigatório | [`SEGSENSE_DEMO_RUN_001.md`](SEGSENSE_DEMO_RUN_001.md) |
| SEGSENSE_ASM_001 | Checkpoint estratégico e teto de personalização contextual | 1.0 | Incorporado ao índice; hipótese, não API | [`SEGSENSE_ASM_001.md`](SEGSENSE_ASM_001.md) |
| SEGSENSE_POS_001 | Posicionamento de produto | 1.1 | Vigente nesta etapa; linguagem da vitrine no COR_001 | [`SEGSENSE_POS_001.md`](SEGSENSE_POS_001.md) |
| SEGSENSE_SRC_002 | Matriz de evidências públicas Icatu | 1.0 | Vigente nesta etapa | [`SEGSENSE_SRC_002.md`](SEGSENSE_SRC_002.md) |
| SEGSENSE_MCK_001 | Contrato conceitual do Insurance Provider Mock | 1.0 | Conceitual; não executável | [`SEGSENSE_MCK_001.md`](SEGSENSE_MCK_001.md) |
| SEGSENSE_UX_005 | Entrada pública de posicionamento `/` | 1.1 | PRM_012 + composição do COR_001 | [`SEGSENSE_UX_005.md`](SEGSENSE_UX_005.md) |
| SEGSENSE_API_007 | APIs editoriais de demonstração (SegSense) | 1.0 | Vigente nesta etapa | [`SEGSENSE_API_007.md`](SEGSENSE_API_007.md) |
| SEGSENSE_DOM_003 | DemonstrationStory | 1.0 | Vigente nesta etapa | [`SEGSENSE_DOM_003.md`](SEGSENSE_DOM_003.md) |
| SEGSENSE_DAT_006 | Persistência V12 de DemonstrationStory | 1.0 | Vigente nesta etapa | [`SEGSENSE_DAT_006.md`](SEGSENSE_DAT_006.md) |
| SEGSENSE_UX_004 | Âncora visual comercial | 1.0 | Implementado no PRM_011 | [`SEGSENSE_UX_004.md`](SEGSENSE_UX_004.md) |
| SEGSENSE_SEC_004 | Ameaças da âncora comercial e do backoffice | 1.0 | Vigente nesta etapa | [`SEGSENSE_SEC_004.md`](SEGSENSE_SEC_004.md) |
| SEGSENSE_SRC_001 | Fontes públicas do Hub Icatu | 1.0 | Vigente nesta etapa | [`SEGSENSE_SRC_001.md`](SEGSENSE_SRC_001.md) |
| SPIDER-ARCH-017 | Arquitetura de Aplicações Satélite | PROPOSED (cópia SegSense) | O texto vigente está na Spider e aponta SAT-003 IMPLEMENTADO | [`references/SPIDER-ARCH-017.md`](references/SPIDER-ARCH-017.md) |
| SPIDER-SAT-003 | Satellite Contract V1 | 1.0 | IMPLEMENTADO / DEMO ONLY na Spider; SegSense = EXPERIENCE SATELLITE | [`../../spider/docs/architecture/SPIDER-SATELLITE-CONTRACT-V1.md`](../../spider/docs/architecture/SPIDER-SATELLITE-CONTRACT-V1.md) |

## Convenção

Os identificadores SegSense seguem `SEGSENSE_<CATEGORIA>_<SEQUENCIAL>`, conforme a seção 26 de `SEGSENSE_ARQ_001`. `REV` registra revisão de aderência da etapa. `SPIDER-ARCH-017` permanece com o identificador original da Spider; não é documento de domínio SegSense. Categorias adicionais usadas: `DOM`, `DAT`, `API`, `PRM`, `ADR`, `SEC`, `PLN`, `GOV`, `LNK`, `UX`, `UI`, `FUN`, `INT`, `REQ`, `SRC`, `ASM`, `POS`, `MCK`. `SEGSENSE_PRM_013_COR_001` é o único corretivo do PRM_013.
