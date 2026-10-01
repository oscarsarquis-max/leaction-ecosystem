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
| ACTIONFINANCE_DOM_001 | Linguagem e estados da fatia de títulos e baixas | 0.5 | Recorte local + prioridade Loja/Pay/Panne (não implementada) | [`domain/ACTIONFINANCE_DOM_001.md`](domain/ACTIONFINANCE_DOM_001.md) |
| ACTIONFINANCE_DAT_001 | Modelo efetivo PostgreSQL da fatia | 0.92 | V1–V12; importação Pay sem movimento financeiro | [`data/ACTIONFINANCE_DAT_001.md`](data/ACTIONFINANCE_DAT_001.md) |
| ACTIONFINANCE_INT_001 | Matriz Spider e identidades | 0.62 | Listagem 1.4; 1.0–1.3 intactos; fio Hub vivo pendente | [`integrations/ACTIONFINANCE_INT_001.md`](integrations/ACTIONFINANCE_INT_001.md) |
| ACTIONFINANCE_UX_001 | Experiência operacional a receber/pagar, baixas e contas | 0.10 | Recebimentos do Pay + jornada no Monitor | [`ux/ACTIONFINANCE_UX_001.md`](ux/ACTIONFINANCE_UX_001.md) |
| ACTIONFINANCE_PLN_001 | Sequência de prompts | 0.1 | Orientativo | [`prompts/ACTIONFINANCE_PLN_001.md`](prompts/ACTIONFINANCE_PLN_001.md) |
| ACTIONFINANCE_PRM_001 | Prompt integral v0.2 | 0.2 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_001.md`](prompts/ACTIONFINANCE_PRM_001.md) |
| ACTIONFINANCE_PRM_001_EXEC | Histórico de execução | 0.2 | Executado; não autoaprovado | [`prompts/ACTIONFINANCE_PRM_001_EXEC.md`](prompts/ACTIONFINANCE_PRM_001_EXEC.md) |
| ACTIONFINANCE_PRM_002 | Prompt integral da fundação | 0.2 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_002.md`](prompts/ACTIONFINANCE_PRM_002.md) |
| ACTIONFINANCE_PRM_002_EXEC | Histórico de execução da fundação | 0.1 | Executado; sem aprovação de produção | [`prompts/ACTIONFINANCE_PRM_002_EXEC.md`](prompts/ACTIONFINANCE_PRM_002_EXEC.md) |
| ACTIONFINANCE_FND_001 | Decisões e versões da fundação | 0.1 | Obtida localmente | [`architecture/ACTIONFINANCE_FND_001.md`](architecture/ACTIONFINANCE_FND_001.md) |
| ACTIONFINANCE_SEC_001 | Identidade demo e OIDC de produto | 0.2 | Demo local; OIDC preparado | [`security/ACTIONFINANCE_SEC_001.md`](security/ACTIONFINANCE_SEC_001.md) |
| ACTIONFINANCE_RUN_001 | Operação, diagnóstico e backup | 0.5 | Destino aplicado; login humano pendente | [`operations/ACTIONFINANCE_RUN_001.md`](operations/ACTIONFINANCE_RUN_001.md) |
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
| ACTIONFINANCE_REV_006 | Acesso autenticado e pacote de publicação | 0.1 | Superado pelo encerramento do analista | [`reviews/ACTIONFINANCE_REV_006.md`](reviews/ACTIONFINANCE_REV_006.md) |
| ACTIONFINANCE_REV_006_PARECER_ANALISTA | Parecer do analista sobre PRM_006 | 0.1 | Aceite pendente; C1–C6 | [`reviews/ACTIONFINANCE_REV_006_PARECER_ANALISTA.md`](reviews/ACTIONFINANCE_REV_006_PARECER_ANALISTA.md) |
| ACTIONFINANCE_PRM_006_COR_001 | Corretivo de autorização e ensaio | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_006_COR_001.md`](prompts/ACTIONFINANCE_PRM_006_COR_001.md) |
| ACTIONFINANCE_PRM_006_COR_001_ENCERRAMENTO | Parecer focado e complemento de encerramento | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_006_COR_001_ENCERRAMENTO.md`](prompts/ACTIONFINANCE_PRM_006_COR_001_ENCERRAMENTO.md) |
| ACTIONFINANCE_REV_006_COR_001 | Correções C1–C6 do PRM_006 + complemento | 0.1 | Três pontos aceitos; residual 360 corrigido; aceite integral pendente | [`reviews/ACTIONFINANCE_REV_006_COR_001.md`](reviews/ACTIONFINANCE_REV_006_COR_001.md) |
| ACTIONFINANCE_REV_006_COR_001_PARECER_ANALISTA | Parecer dos três pontos + residual visual | 0.1 | Histórico; superado pelo encerramento | [`reviews/ACTIONFINANCE_REV_006_COR_001_PARECER_ANALISTA.md`](reviews/ACTIONFINANCE_REV_006_COR_001_PARECER_ANALISTA.md) |
| ACTIONFINANCE_REV_006_ENCERRAMENTO_ANALISTA | Encerramento integral do PRM_006 | 0.1 | Aprovado no recorte local; ciclo encerrado | [`reviews/ACTIONFINANCE_REV_006_ENCERRAMENTO_ANALISTA.md`](reviews/ACTIONFINANCE_REV_006_ENCERRAMENTO_ANALISTA.md) |
| ACTIONFINANCE_PRM_007 | Publicação restrita em produção | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_007.md`](prompts/ACTIONFINANCE_PRM_007.md) |
| ACTIONFINANCE_PRM_007_AUTORIZACAO | Concordância de gasto e continuidade | 0.1 | Proprietário concordou; apply autorizado | [`prompts/ACTIONFINANCE_PRM_007_AUTORIZACAO.md`](prompts/ACTIONFINANCE_PRM_007_AUTORIZACAO.md) |
| ACTIONFINANCE_PRM_007_ADENDO_001_GATEWAY | Gateway existente e revisão de custo | 0.1 | Avaliação registada; migração não aplicada | [`prompts/ACTIONFINANCE_PRM_007_ADENDO_001_GATEWAY.md`](prompts/ACTIONFINANCE_PRM_007_ADENDO_001_GATEWAY.md) |
| ACTIONFINANCE_DEP_001 | Plano concreto de publicação e custo | 0.1 | §4 histórica; §8 reavalia ingresso | [`operations/ACTIONFINANCE_DEP_001.md`](operations/ACTIONFINANCE_DEP_001.md) |
| ACTIONFINANCE_REV_007 | Relatório da publicação restrita | 0.1 | Login/CSRF ok; restore parcial; publicação não declarada | [`reviews/ACTIONFINANCE_REV_007.md`](reviews/ACTIONFINANCE_REV_007.md) |
| ACTIONFINANCE_REV_007_ADENDO_001 | Avaliação do gateway compartilhado | 0.1 | Histórico; migração depois autorizada | [`reviews/ACTIONFINANCE_REV_007_ADENDO_001.md`](reviews/ACTIONFINANCE_REV_007_ADENDO_001.md) |
| ACTIONFINANCE_PRM_007_ADENDO_002_MIGRACAO_ALB | Migração para paneldx-alb | 0.1 | Autorizada e executada 30/09 | [`prompts/ACTIONFINANCE_PRM_007_ADENDO_002_MIGRACAO_ALB.md`](prompts/ACTIONFINANCE_PRM_007_ADENDO_002_MIGRACAO_ALB.md) |
| ACTIONFINANCE_REV_007_ADENDO_002 | Evidências da migração de ingresso | 0.1 | ALB dedicado excluído; publicação não declarada | [`reviews/ACTIONFINANCE_REV_007_ADENDO_002.md`](reviews/ACTIONFINANCE_REV_007_ADENDO_002.md) |
| ACTIONFINANCE_PRM_007_ADENDO_003_ENCODING | Correção de caracteres no nome da empresa | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_007_ADENDO_003_ENCODING.md`](prompts/ACTIONFINANCE_PRM_007_ADENDO_003_ENCODING.md) |
| ACTIONFINANCE_REV_007_ADENDO_003 | Reparo UTF-8 Loja de Pães | 0.1 | Encerrado pelo analista com confirmação visual do proprietário | [`reviews/ACTIONFINANCE_REV_007_ADENDO_003.md`](reviews/ACTIONFINANCE_REV_007_ADENDO_003.md) |
| ACTIONFINANCE_PRM_007_CONTINUIDADE_ENCERRAMENTO | Provas residuais de publicação | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_007_CONTINUIDADE_ENCERRAMENTO.md`](prompts/ACTIONFINANCE_PRM_007_CONTINUIDADE_ENCERRAMENTO.md) |
| ACTIONFINANCE_PRM_008 | Primeira integração via Spider (consulta Pay) | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_008.md`](prompts/ACTIONFINANCE_PRM_008.md) |
| ACTIONFINANCE_PRM_008_COR_001 | Confiabilidade da consulta via Spider | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_008_COR_001.md`](prompts/ACTIONFINANCE_PRM_008_COR_001.md) |
| ACTIONFINANCE_PRM_008_COR_002 | Fechamento da consulta pela Spider | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_008_COR_002.md`](prompts/ACTIONFINANCE_PRM_008_COR_002.md) |
| ACTIONFINANCE_REV_008 | Relatório da fatia isolada AF→Spider→Pay | 0.1 | Encerrado pelo analista no recorte isolado | [`reviews/ACTIONFINANCE_REV_008.md`](reviews/ACTIONFINANCE_REV_008.md) |
| ACTIONFINANCE_REV_008_COR_001 | Correção de confiabilidade C1–C5 | 0.1 | Encerrado com o ciclo PRM_008 | [`reviews/ACTIONFINANCE_REV_008_COR_001.md`](reviews/ACTIONFINANCE_REV_008_COR_001.md) |
| ACTIONFINANCE_REV_008_COR_002 | Identidade de tentativa, jornada UX e prova Spider | 0.1 | Encerrado; disputa A/B aceita | [`reviews/ACTIONFINANCE_REV_008_COR_002.md`](reviews/ACTIONFINANCE_REV_008_COR_002.md) |
| ACTIONFINANCE_REV_008_COR_002_PARECER_ANALISTA | Parecer do analista sobre COR_002 | 0.1 | Histórico; superado pelo encerramento | [`reviews/ACTIONFINANCE_REV_008_COR_002_PARECER_ANALISTA.md`](reviews/ACTIONFINANCE_REV_008_COR_002_PARECER_ANALISTA.md) |
| ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA | Encerramento e aceite do analista | 0.1 | PRM_008 + COR_001/COR_002 aprovados no recorte isolado | [`reviews/ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA.md`](reviews/ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA.md) |
| ACTIONFINANCE_PRM_009 | Sincronização de recebimentos com passagem visível pela Spider | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_009.md`](prompts/ACTIONFINANCE_PRM_009.md) |
| ACTIONFINANCE_PRM_009_CONTINUIDADE_001 | Percurso real e demonstração | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_009_CONTINUIDADE_001.md`](prompts/ACTIONFINANCE_PRM_009_CONTINUIDADE_001.md) |
| ACTIONFINANCE_PRM_009_ADENDO_001_ACEITE_PUBLICO | Jornada pública como condição de aceite | 0.1 | Cópia integral do adendo | [`prompts/ACTIONFINANCE_PRM_009_ADENDO_001_ACEITE_PUBLICO.md`](prompts/ACTIONFINANCE_PRM_009_ADENDO_001_ACEITE_PUBLICO.md) |
| ACTIONFINANCE_PRM_009_COR_001 | Cursor, limites e restore com FKs | 0.1 | Cópia de rastreio | [`prompts/ACTIONFINANCE_PRM_009_COR_001.md`](prompts/ACTIONFINANCE_PRM_009_COR_001.md) |
| ACTIONFINANCE_REV_009 | Relatório da sincronização AF→Spider→Pay | 0.1 | Local exercitado; implantação pública executada; aceite pendente | [`reviews/ACTIONFINANCE_REV_009.md`](reviews/ACTIONFINANCE_REV_009.md) |
| ACTIONFINANCE_REV_009_COR_001 | Cursor/restore | 0.1 | Correções concluídas | [`reviews/ACTIONFINANCE_REV_009_COR_001.md`](reviews/ACTIONFINANCE_REV_009_COR_001.md) |
| ACTIONFINANCE_PRM_009_PACOTE_PUBLICACAO | Pacote concreto para aplicar | 0.4 | Implantação executada; aceite pendente | [`operations/ACTIONFINANCE_PRM_009_PACOTE_PUBLICACAO.md`](operations/ACTIONFINANCE_PRM_009_PACOTE_PUBLICACAO.md) |
| ACTIONFINANCE_PRM_009_AUTORIZACAO_PROPRIETARIO | Autorização de implantação (não é aceite) | 0.1 | Concedida 01/10/2026 | [`prompts/ACTIONFINANCE_PRM_009_AUTORIZACAO_PROPRIETARIO.md`](prompts/ACTIONFINANCE_PRM_009_AUTORIZACAO_PROPRIETARIO.md) |
| ACTIONFINANCE_REV_009_RECOMENDACAO_EXECUCAO_ANALISTA | Recomendação de executar o pacote revisado | 0.1 | Recomenda execução delimitada | [`reviews/ACTIONFINANCE_REV_009_RECOMENDACAO_EXECUCAO_ANALISTA.md`](reviews/ACTIONFINANCE_REV_009_RECOMENDACAO_EXECUCAO_ANALISTA.md) |
| ACTIONFINANCE_PRM_009_GUIA_PROPRIETARIO | Como acompanhar as duas telas | 0.4 | Local feito; roteiro público para o operador | [`operations/ACTIONFINANCE_PRM_009_GUIA_PROPRIETARIO.md`](operations/ACTIONFINANCE_PRM_009_GUIA_PROPRIETARIO.md) |
| ACTIONFINANCE_REV_009_EXECUCAO_PUBLICA | Relato da implantação pública | 0.1 | Componentes no ar; jornada autenticada pendente | [`reviews/ACTIONFINANCE_REV_009_EXECUCAO_PUBLICA.md`](reviews/ACTIONFINANCE_REV_009_EXECUCAO_PUBLICA.md) |
| ACTIONFINANCE_PRM_009_INC_001 | Recuperar integração e Monitor públicos | 0.1 | Incidente após implantação; aceite bloqueado | [`prompts/ACTIONFINANCE_PRM_009_INC_001.md`](prompts/ACTIONFINANCE_PRM_009_INC_001.md) |
| ACTIONFINANCE_REV_009_INC_001 | Relato do incidente e reparo público | 0.1 | Causas demonstradas; jornada autenticada pendente | [`reviews/ACTIONFINANCE_REV_009_INC_001.md`](reviews/ACTIONFINANCE_REV_009_INC_001.md) |

## Próximos gates

1. PRM_003: ciclo **encerrado** ([encerramento](reviews/ACTIONFINANCE_REV_003_ENCERRAMENTO.md)). Sem autorização de produção/piloto.
2. PRM_004: **aprovado pelo analista** no recorte local ([encerramento](reviews/ACTIONFINANCE_REV_004_ENCERRAMENTO_ANALISTA.md)). Parecer inicial copiado em PRM_005; não estava no repositório antes.
3. PRM_005: ciclo **encerrado** ([encerramento](reviews/ACTIONFINANCE_REV_005_ENCERRAMENTO_ANALISTA.md)). Sem autorização de produção/piloto. Sem integração Spider.
4. PRM_006: **aprovado integralmente** no recorte local ([encerramento](reviews/ACTIONFINANCE_REV_006_ENCERRAMENTO_ANALISTA.md)). Sem reabrir corretivos.
5. PRM_007: host no `paneldx-alb`; login/nome/logout-CSRF comprovados; restore PITR isolado limpo, invalidação de sessão no restaurado ainda em falta. [REV_007](reviews/ACTIONFINANCE_REV_007.md). Aceite final **não** atribuído ao executor.
6. PRM_008: **aprovado e encerrado** pelo analista em 01/10/2026 no recorte isolado ([encerramento](reviews/ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA.md)), com COR_001 e COR_002. Sem reabrir corretivos.
7. PRM_009: implantação aplicada; [INC_001](prompts/ACTIONFINANCE_PRM_009_INC_001.md) em recuperação pública. Autorização ≠ aceite. Sem PRM_010. PRM_007 (sessão no restore) continua pendente.

A fundação local não é aprovação de piloto, integração Spider ou funcionalidade financeira.

## Estado vigente

PRM_001: **aprovado tecnicamente pelo analista**, sem ressalvas abertas; [encerramento](reviews/ACTIONFINANCE_REV_001_ENCERRAMENTO.md).  
PRM_002: **executado** sob instrução do proprietário — fundação técnica local.  
PRM_003: **aprovado pelo analista** em 29/09/2026 para o recorte local demonstrativo a receber/pagar; [encerramento](reviews/ACTIONFINANCE_REV_003_ENCERRAMENTO.md).  
PRM_004: **aprovado pelo analista** em 29/09/2026 no recorte local demonstrativo; [encerramento](reviews/ACTIONFINANCE_REV_004_ENCERRAMENTO_ANALISTA.md). O parecer inicial foi copiado ao repositório só no PRM_005.  
PRM_005: **aprovado pelo analista** em 29/09/2026 no recorte local de identidade/UX; [encerramento](reviews/ACTIONFINANCE_REV_005_ENCERRAMENTO_ANALISTA.md).  
PRM_006: **aprovado pelo analista** em 30/09/2026 no recorte local; [encerramento](reviews/ACTIONFINANCE_REV_006_ENCERRAMENTO_ANALISTA.md).  
PRM_007: **host no ar** após “concordo sim” em 30/09/2026 ([autorização](prompts/ACTIONFINANCE_PRM_007_AUTORIZACAO.md)). Publicação ainda não declarada. Invalidação de sessão no restore **pendente**.  
PRM_008: **aprovado pelo analista** em 01/10/2026 no recorte isolado de consulta AF→Spider→simulador; [encerramento](reviews/ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA.md). Ciclo encerrado; corretivos não reabertos.  
PRM_009: **implantação executada; INC_001 em recuperação.** Aceite ainda pendente. Sem PRM_010.

## Revisão vigente do PRM_002

**PRM_007 em 30/09/2026:** plano em [DEP_001](operations/ACTIONFINANCE_DEP_001.md); relatório [REV_007](reviews/ACTIONFINANCE_REV_007.md). Host público no ar; publicação não declarada. PRM_006 encerrado pelo analista.

## Diretrizes vigentes de integração — 28/09/2026

A [fonte integral do proprietário](integrations/ACTIONFINANCE_DIR_INT_001_2026-09-28.md) e sua [incorporação arquitetural](architecture/ACTIONFINANCE_ARQ_002_DIRETRIZES_INTEGRACAO.md) prevalecem sobre trechos anteriores conflitantes para o desenho futuro. Nesta fatia a operação é local e autônoma. Integração Spider não foi implementada.
