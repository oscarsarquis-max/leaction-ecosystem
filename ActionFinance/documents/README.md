# Documentos oficiais do ActionFinance

Identificadores existentes não devem ser renomeados nem movidos.

## Convenção de identificadores

| Prefixo | Uso |
|---|---|
| `ACTIONFINANCE_ARQ_` / `FND_` | Arquitetura e fundação obtida |
| `ACTIONFINANCE_EVD_` / `LAC_` | Evidência e lacunas |
| `ACTIONFINANCE_DOM_` / `DAT_` / `INT_` / `UX_` | Domínio, dados, integração, experiência |
| `ACTIONFINANCE_DOMINIO_` | Identidade de publicação |
| `ACTIONFINANCE_SEC_` / `RUN_` | Segurança e operação |
| `AF-ADR-` | Decisão arquitetural |
| `ACTIONFINANCE_PLN_` / `PRM_` / `PRM_*_EXEC` | Plano e prompts |
| `ACTIONFINANCE_REV_` | Revisão e parecer |

Fonte arquitetural: [`architecture/ACTIONFINANCE_ARQ_001.md`](architecture/ACTIONFINANCE_ARQ_001.md) (v0.2). Fundação local: [`architecture/ACTIONFINANCE_FND_001.md`](architecture/ACTIONFINANCE_FND_001.md). ADRs técnicos permanecem **PROPOSED**. Decisões de negócio ARQ §1 e domínio `finaction.com.br`: **CONFIRMED_BY_OWNER**. A execução do PRM_002 não aprova produção nem promove UX/contratos futuros.

## Índice

| Identificador | Título | Versão | Situação | Caminho |
|---|---|---|---|---|
| ACTIONFINANCE_ARQ_001 | Arquitetura de produto, sistema, dados e experiência | 0.2 | Proposta; apêndice factual | [`architecture/ACTIONFINANCE_ARQ_001.md`](architecture/ACTIONFINANCE_ARQ_001.md) |
| ACTIONFINANCE_EVD_001 | Evidências e matriz implementado / proposto / bloqueado | 0.1 | Snapshot estático | [`architecture/ACTIONFINANCE_EVD_001.md`](architecture/ACTIONFINANCE_EVD_001.md) |
| ACTIONFINANCE_LAC_001 | Lacunas por etapa | 0.1 | Aberto | [`architecture/ACTIONFINANCE_LAC_001.md`](architecture/ACTIONFINANCE_LAC_001.md) |
| ACTIONFINANCE_DOMINIO_001 | Domínio finaction.com.br | 0.1 | CONFIRMED_BY_OWNER | [`architecture/ACTIONFINANCE_DOMINIO_001.md`](architecture/ACTIONFINANCE_DOMINIO_001.md) |
| AF-ADR-001 … 010 | Decisões técnicas | 0.1–0.2 | PROPOSED | [`adr/`](adr/) |
| ACTIONFINANCE_DOM_001 | Linguagem e estados da fatia de títulos e baixas | 0.4 | Implementado no recorte local | [`domain/ACTIONFINANCE_DOM_001.md`](domain/ACTIONFINANCE_DOM_001.md) |
| ACTIONFINANCE_DAT_001 | Modelo efetivo PostgreSQL da fatia | 0.6 | Implementado; V2–V7; permissões por empresa | [`data/ACTIONFINANCE_DAT_001.md`](data/ACTIONFINANCE_DAT_001.md) |
| ACTIONFINANCE_INT_001 | Matriz Spider e identidades | 0.2 | EXTERNAL_CONTRACT_PENDING | [`integrations/ACTIONFINANCE_INT_001.md`](integrations/ACTIONFINANCE_INT_001.md) |
| ACTIONFINANCE_UX_001 | Experiência operacional a receber/pagar, baixas e contas | 0.6 | Acesso PRM_006; identidade 005; regras 003/004 | [`ux/ACTIONFINANCE_UX_001.md`](ux/ACTIONFINANCE_UX_001.md) |
| ACTIONFINANCE_PLN_001 | Sequência de prompts | 0.1 | Orientativo | [`prompts/ACTIONFINANCE_PLN_001.md`](prompts/ACTIONFINANCE_PLN_001.md) |
| ACTIONFINANCE_PRM_001 | Prompt integral v0.2 | 0.2 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_001.md`](prompts/ACTIONFINANCE_PRM_001.md) |
| ACTIONFINANCE_PRM_001_EXEC | Histórico de execução | 0.2 | Executado; não autoaprovado | [`prompts/ACTIONFINANCE_PRM_001_EXEC.md`](prompts/ACTIONFINANCE_PRM_001_EXEC.md) |
| ACTIONFINANCE_PRM_002 | Prompt integral da fundação | 0.2 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_002.md`](prompts/ACTIONFINANCE_PRM_002.md) |
| ACTIONFINANCE_PRM_002_EXEC | Histórico de execução da fundação | 0.1 | Executado; sem aprovação de produção | [`prompts/ACTIONFINANCE_PRM_002_EXEC.md`](prompts/ACTIONFINANCE_PRM_002_EXEC.md) |
| ACTIONFINANCE_FND_001 | Decisões e versões da fundação | 0.1 | Obtida localmente | [`architecture/ACTIONFINANCE_FND_001.md`](architecture/ACTIONFINANCE_FND_001.md) |
| ACTIONFINANCE_SEC_001 | Identidade demo e OIDC de produto | 0.2 | Demo local; OIDC preparado | [`security/ACTIONFINANCE_SEC_001.md`](security/ACTIONFINANCE_SEC_001.md) |
| ACTIONFINANCE_RUN_001 | Operação, diagnóstico e backup | 0.3 | Local + bootstrap/migrate + pacote (não ativado) | [`operations/ACTIONFINANCE_RUN_001.md`](operations/ACTIONFINANCE_RUN_001.md) |
| ACTIONFINANCE_REV_001 | Revisão documental | 0.2 | Analista: aprovado; R1–R4 fechados; proprietário: pendente de produção | [`reviews/ACTIONFINANCE_REV_001.md`](reviews/ACTIONFINANCE_REV_001.md) |
| ACTIONFINANCE_REV_001_PARECER_ANALISTA | Parecer do analista | 0.1 | Preservado | [`reviews/ACTIONFINANCE_REV_001_PARECER_ANALISTA.md`](reviews/ACTIONFINANCE_REV_001_PARECER_ANALISTA.md) |
| ACTIONFINANCE_REV_002 | Provas da fundação | 0.1 | Histórico; restore de 25/09 era parcial | [`reviews/ACTIONFINANCE_REV_002.md`](reviews/ACTIONFINANCE_REV_002.md) |
| ACTIONFINANCE_REV_002_COR_001 | Corretivo C1–C7 | 0.1 | Executado; `mvnw verify` não verde | [`reviews/ACTIONFINANCE_REV_002_COR_001.md`](reviews/ACTIONFINANCE_REV_002_COR_001.md) |
| ACTIONFINANCE_PRM_002_COR_002 | Prompt do corretivo D1–D5 | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_002_COR_002.md`](prompts/ACTIONFINANCE_PRM_002_COR_002.md) |
| ACTIONFINANCE_PRM_002_COR_002_EXEC | Histórico de execução COR_002 | 0.1 | Executado; aceite do analista pendente | [`prompts/ACTIONFINANCE_PRM_002_COR_002_EXEC.md`](prompts/ACTIONFINANCE_PRM_002_COR_002_EXEC.md) |
| ACTIONFINANCE_REV_002_COR_002 | Encerramento das pendências da fundação | 0.1 | Executado; `mvnw verify` verde; aceite do analista pendente | [`reviews/ACTIONFINANCE_REV_002_COR_002.md`](reviews/ACTIONFINANCE_REV_002_COR_002.md) |
| ACTIONFINANCE_PRM_003 | Prompt integral da primeira fatia funcional | 0.3 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_003.md`](prompts/ACTIONFINANCE_PRM_003.md) |
| ACTIONFINANCE_REV_003 | Entrega a receber e a pagar | 0.4 | Analista: aprovado no recorte local demonstrativo; ciclo encerrado | [`reviews/ACTIONFINANCE_REV_003.md`](reviews/ACTIONFINANCE_REV_003.md) |
| ACTIONFINANCE_REV_003_PARECER_ANALISTA | Parecer: entrega parcial; correções R1–R6 | 0.1 | Histórico preservado | [`reviews/ACTIONFINANCE_REV_003_PARECER_ANALISTA.md`](reviews/ACTIONFINANCE_REV_003_PARECER_ANALISTA.md) |
| ACTIONFINANCE_REV_003_REVALIDACAO_ANALISTA | Revalidação: R3 residual | 0.1 | Histórico preservado | [`reviews/ACTIONFINANCE_REV_003_REVALIDACAO_ANALISTA.md`](reviews/ACTIONFINANCE_REV_003_REVALIDACAO_ANALISTA.md) |
| ACTIONFINANCE_REV_003_ENCERRAMENTO | Encerramento e aceite do analista | 0.1 | PRM_003 aprovado no recorte local; sem produção | [`reviews/ACTIONFINANCE_REV_003_ENCERRAMENTO.md`](reviews/ACTIONFINANCE_REV_003_ENCERRAMENTO.md) |
| ACTIONFINANCE_PRM_004 | Prompt integral de recebimentos, pagamentos registrados e contas | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_004.md`](prompts/ACTIONFINANCE_PRM_004.md) |
| ACTIONFINANCE_REV_004 | Entrega de baixas, contas e extrato gerencial | 0.1 | Executado; aceite do analista pendente | [`reviews/ACTIONFINANCE_REV_004.md`](reviews/ACTIONFINANCE_REV_004.md) |
| ACTIONFINANCE_PRM_004_COR_001 | Prompt do corretivo C1–C5 (contas, baixas, extrato) | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_004_COR_001.md`](prompts/ACTIONFINANCE_PRM_004_COR_001.md) |
| ACTIONFINANCE_REV_004_COR_001 | Correções de contas, baixas e extrato | 0.1 | Executado; base do aceite PRM_004 | [`reviews/ACTIONFINANCE_REV_004_COR_001.md`](reviews/ACTIONFINANCE_REV_004_COR_001.md) |
| ACTIONFINANCE_REV_004_PARECER_ANALISTA | Parecer do analista sobre PRM_004 | 0.1 | Copiado ao repositório no PRM_005; não existia aqui antes | [`reviews/ACTIONFINANCE_REV_004_PARECER_ANALISTA.md`](reviews/ACTIONFINANCE_REV_004_PARECER_ANALISTA.md) |
| ACTIONFINANCE_REV_004_ENCERRAMENTO_ANALISTA | Encerramento e aceite local do PRM_004 | 0.1 | Copiado ao repositório no PRM_005 | [`reviews/ACTIONFINANCE_REV_004_ENCERRAMENTO_ANALISTA.md`](reviews/ACTIONFINANCE_REV_004_ENCERRAMENTO_ANALISTA.md) |
| ACTIONFINANCE_PRM_005 | Prompt integral de identidade visual | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_005.md`](prompts/ACTIONFINANCE_PRM_005.md) |
| ACTIONFINANCE_REV_005 | Identidade e consistência da interface | 0.1 | Analista: aprovado; ciclo encerrado | [`reviews/ACTIONFINANCE_REV_005.md`](reviews/ACTIONFINANCE_REV_005.md) |
| ACTIONFINANCE_PRM_005_COR_001 | Ajuste pontual do cabeçalho compacto | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_005_COR_001.md`](prompts/ACTIONFINANCE_PRM_005_COR_001.md) |
| ACTIONFINANCE_REV_005_ENCERRAMENTO_ANALISTA | Encerramento e aceite do analista | 0.1 | PRM_005 aprovado no recorte local; sem produção | [`reviews/ACTIONFINANCE_REV_005_ENCERRAMENTO_ANALISTA.md`](reviews/ACTIONFINANCE_REV_005_ENCERRAMENTO_ANALISTA.md) |
| ACTIONFINANCE_PRM_006 | Prompt integral de acesso e pacote de publicação | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_006.md`](prompts/ACTIONFINANCE_PRM_006.md) |
| ACTIONFINANCE_REV_006 | Acesso autenticado e pacote de publicação | 0.1 | Executado; aceite do analista pendente | [`reviews/ACTIONFINANCE_REV_006.md`](reviews/ACTIONFINANCE_REV_006.md) |
| ACTIONFINANCE_REV_006_PARECER_ANALISTA | Parecer do analista sobre PRM_006 | 0.1 | Aceite pendente; C1–C6 | [`reviews/ACTIONFINANCE_REV_006_PARECER_ANALISTA.md`](reviews/ACTIONFINANCE_REV_006_PARECER_ANALISTA.md) |
| ACTIONFINANCE_PRM_006_COR_001 | Corretivo de autorização e ensaio | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_006_COR_001.md`](prompts/ACTIONFINANCE_PRM_006_COR_001.md) |
| ACTIONFINANCE_PRM_006_COR_001_ENCERRAMENTO | Parecer focado e complemento de encerramento | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_006_COR_001_ENCERRAMENTO.md`](prompts/ACTIONFINANCE_PRM_006_COR_001_ENCERRAMENTO.md) |
| ACTIONFINANCE_REV_006_COR_001 | Correções C1–C6 do PRM_006 + complemento | 0.1 | Aceite parcial do recorte; aceite integral pendente dos 3 pontos | [`reviews/ACTIONFINANCE_REV_006_COR_001.md`](reviews/ACTIONFINANCE_REV_006_COR_001.md) |

## Próximos gates

1. PRM_003: ciclo **encerrado** ([encerramento](reviews/ACTIONFINANCE_REV_003_ENCERRAMENTO.md)). Sem autorização de produção/piloto.
2. PRM_004: **aprovado pelo analista** no recorte local ([encerramento](reviews/ACTIONFINANCE_REV_004_ENCERRAMENTO_ANALISTA.md)). Parecer inicial copiado em PRM_005; não estava no repositório antes.
3. PRM_005: ciclo **encerrado** ([encerramento](reviews/ACTIONFINANCE_REV_005_ENCERRAMENTO_ANALISTA.md)). Sem autorização de produção/piloto. Sem integração Spider.
4. PRM_006: **executado**; parecer do analista em [REV_006_PARECER](reviews/ACTIONFINANCE_REV_006_PARECER_ANALISTA.md). Corretivo [REV_006_COR_001](reviews/ACTIONFINANCE_REV_006_COR_001.md) com [complemento de encerramento](prompts/ACTIONFINANCE_PRM_006_COR_001_ENCERRAMENTO.md). Aceite parcial do recorte da retomada; aceite integral pendente. Sem ativação de `actionfinance.actionhub.com.br`. Sem PRM_007.

A fundação local não é aprovação de piloto, integração Spider ou funcionalidade financeira.

## Estado vigente

PRM_001: **aprovado tecnicamente pelo analista**, sem ressalvas abertas; [encerramento](reviews/ACTIONFINANCE_REV_001_ENCERRAMENTO.md).  
PRM_002: **executado** sob instrução do proprietário — fundação técnica local.  
PRM_003: **aprovado pelo analista** em 29/09/2026 para o recorte local demonstrativo a receber/pagar; [encerramento](reviews/ACTIONFINANCE_REV_003_ENCERRAMENTO.md).  
PRM_004: **aprovado pelo analista** em 29/09/2026 no recorte local demonstrativo; [encerramento](reviews/ACTIONFINANCE_REV_004_ENCERRAMENTO_ANALISTA.md). O parecer inicial foi copiado ao repositório só no PRM_005.  
PRM_005: **aprovado pelo analista** em 29/09/2026 no recorte local de identidade/UX; [encerramento](reviews/ACTIONFINANCE_REV_005_ENCERRAMENTO_ANALISTA.md).  
PRM_006: **executado** em 29/09/2026 (acesso + pacote). Aceite parcial do recorte da retomada; aceite integral pendente do complemento. Sem ativação pública. Sem PRM_007.

## Revisão vigente do PRM_002

**PRM_006 executado em 29/09/2026 para revisão do analista.** Relatório: [REV_006](reviews/ACTIONFINANCE_REV_006.md). Sem aceite do executor. Sem ativação pública. PRM_007 não emitido.

## Diretrizes vigentes de integração — 28/09/2026

A [fonte integral do proprietário](integrations/ACTIONFINANCE_DIR_INT_001_2026-09-28.md) e sua [incorporação arquitetural](architecture/ACTIONFINANCE_ARQ_002_DIRETRIZES_INTEGRACAO.md) prevalecem sobre trechos anteriores conflitantes para o desenho futuro. Nesta fatia a operação é local e autônoma. Integração Spider não foi implementada.
