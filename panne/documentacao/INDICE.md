# Índice mestre da documentação Panne

Fonte exclusiva: esta pasta e o código em `panne/`.  
Documentos homônimos em outras aplicações do workspace, inclusive `qmind`, pertencem a **outro produto** e não são fonte da Panne.

## Como ler

| Pasta | Conteúdo |
|---|---|
| `decisoes/` | Decisões canônicas (grounding, IA, governança, identidade visual, chão de fábrica) |
| `regulatorio/` | Mapa e política de normas |
| `produto/` | Fronteiras de produto ainda sem implementação |
| `arquitetura/` | Modelos de dados e catálogos dos ciclos 001–009 |
| `prompts/` e `retornos/` | Contrato e evidência de cada ciclo |
| `legado/` | Inventário somente leitura do MySQL histórico |

## Decisões canônicas

- [Grounding e fontes](decisoes/GROUNDING-E-FONTES.md) — ciclo 007
- [IA assistiva via Bedrock](decisoes/IA-ASSISTIVA-BEDROCK.md) — ciclo 008
- [Governança regulatória](decisoes/GOVERNANCA-REGULATORIA.md) — ciclo 009
- [Identidade visual](decisoes/IDENTIDADE-VISUAL.md)
- [Autenticação e autorização](decisoes/AUTENTICACAO-E-AUTORIZACAO.md) — ciclo 010
- [Contexto e RLS](decisoes/CONTEXTO-E-RLS.md) — ciclo 010
- [Matriz RLS](decisoes/MATRIZ-RLS.md)
- [Ameaças e riscos](decisoes/AMEACAS-E-RISCOS.md)
- [Bootstrap do primeiro proprietário](produto/BOOTSTRAP-PRIMEIRO-PROPRIETARIO.md)

## Regulatório e produto

- [Mapa regulatório inicial](regulatorio/MAPA-REGULATORIO-INICIAL.md)
- [Chão de fábrica](produto/CHAO-DE-FABRICA.md) — descoberta 011
- [Glossário](produto/GLOSSARIO-CHAO-DE-FABRICA.md)
- [Fluxo](produto/FLUXO-CHAO-DE-FABRICA.md)
- [Quadro](produto/QUADRO-PRODUCAO.md)
- [Ficha impressa](produto/FICHA-IMPRESSA.md)
- [Relatórios](produto/RELATORIOS-PROJECOES.md)
- [Contingência](produto/CONTINGENCIA-E-OFFLINE.md)
- [Questões](produto/QUESTOES-CHAO-DE-FABRICA.md)
- [Reaproveitamento](arquitetura/MATRIZ-REAPROVEITAMENTO-PRODUCAO.md)
- [Crítica do legado de produção](arquitetura/MATRIZ-LEGADO-PRODUCAO.md)
- [Modelo conceitual de produção](arquitetura/MODELO-CONCEITUAL-PRODUCAO.md)
- [Estados](arquitetura/ESTADOS-PRODUCAO.md)
- [Comandos e eventos](arquitetura/COMANDOS-E-EVENTOS-PRODUCAO.md)
- [Invariantes](arquitetura/INVARIANTES-PRODUCAO.md)
- [Fronteiras de produção](arquitetura/FRONTEIRAS-PRODUCAO.md)
- [Permissões futuras](decisoes/PERMISSOES-E-RLS-PRODUCAO.md)
- [pip-audit](decisoes/DEPENDENCIAS-E-PIP-AUDIT.md)
- [DDL produção — limitação](legado/DDL-PRODUCAO-LIMITACAO.md)
- [Custos e formação de preços](produto/CUSTOS-E-FORMACAO-DE-PRECOS.md) — descoberta, sem implementação
- [Reconciliação 012](decisoes/RECONCILIACAO-CURSOR-012.md)
- [ADR fundação de produção](decisoes/FUNDACAO-PLANEJAMENTO-PRODUCAO.md)
- [Modelo físico 0010](arquitetura/MODELO-FISICO-0010-PRODUCAO.md)
- [Invariantes de snapshot](arquitetura/INVARIANTES-SNAPSHOT-PRODUCAO.md)
- [Estados e comandos 0010](arquitetura/ESTADOS-E-COMANDOS-0010.md)
- [Catálogo de eventos](arquitetura/CATALOGO-EVENTOS-PRODUCAO.md)
- [Numeração pública](arquitetura/NUMERACAO-PUBLICA-PRODUCAO.md)
- [Divisão e arredondamento](arquitetura/DIVISAO-E-ARREDONDAMENTO-PRODUCAO.md)
- [Questões remanescentes 012](produto/QUESTOES-REMANESCENTES-012.md)
- [Proposta CURSOR-012](prompts/CURSOR-012-proposta.md)
- [Prompt CURSOR-012](prompts/CURSOR-012-implementar-fundacao-producao.md)
- [Retorno CURSOR-012](retornos/CURSOR-012-retorno-execucao.md)
- [Reconciliação 013](decisoes/RECONCILIACAO-CURSOR-013.md)
- [ADR execução de produção](decisoes/EXECUCAO-PRODUCAO.md)
- [Modelo físico 0011](arquitetura/MODELO-FISICO-0011-PRODUCAO.md)
- [Política de pesagem](arquitetura/POLITICA-PESAGEM-PRODUCAO.md)
- [Ledgers e correções](arquitetura/LEDGERS-E-CORRECOES-PRODUCAO.md)
- [Máquinas de estados da execução](arquitetura/MAQUINAS-ESTADOS-EXECUCAO.md)
- [Catálogo de eventos da execução](arquitetura/CATALOGO-EVENTOS-EXECUCAO.md)
- [Conclusão e short_closed](arquitetura/CONCLUSAO-E-SHORT-CLOSED.md)
- [Ocorrências](arquitetura/OCORRENCIAS-PRODUCAO.md)
- [Rendimento](arquitetura/RENDIMENTO-PRODUCAO.md)
- [Emissão da ficha](arquitetura/EMISSAO-FICHA-PRODUCAO.md)
- [Permissões de execução](decisoes/PERMISSOES-EXECUCAO-PRODUCAO.md)
- [Estados e comandos 0011](arquitetura/ESTADOS-E-COMANDOS-0011.md)
- [Fronteiras da execução](arquitetura/FRONTEIRAS-EXECUCAO.md)
- [Questões remanescentes 013](produto/QUESTOES-REMANESCENTES-013.md)
- [Prompt CURSOR-013](prompts/CURSOR-013-implementar-execucao-producao.md)
- [Retorno CURSOR-013](retornos/CURSOR-013-retorno-execucao.md)
- [Reconciliação 014](decisoes/RECONCILIACAO-CURSOR-014.md)
- [ADR API de produção](decisoes/API-PRODUCAO.md)
- [Múltiplos papéis](decisoes/MULTIPLOS-PAPEIS.md)
- [Concessão e revogação](decisoes/CONCESSAO-E-REVOGACAO.md)
- [Conversão de unidades](arquitetura/CONVERSAO-UNIDADES-PRODUCAO.md)
- [Política de ordens antigas](decisoes/POLITICA-ORDENS-ANTIGAS.md)
- [Estado `scrapped`](decisoes/ESTADO-SCRAPPED.md)
- [Catálogo de endpoints](arquitetura/CATALOGO-ENDPOINTS-PRODUCAO.md)
- [Schemas e erros](arquitetura/SCHEMAS-E-ERROS-PRODUCAO.md)
- [Idempotência e concorrência](arquitetura/IDEMPOTENCIA-E-CONCORRENCIA.md)
- [Projeção do quadro](arquitetura/PROJECAO-QUADRO-PRODUCAO.md)
- [Rastreabilidade](arquitetura/RASTREABILIDADE-PRODUCAO.md)
- [Payload da ficha](arquitetura/PAYLOAD-FICHA-PRODUCAO.md)
- [Ameaças e limites da API](decisoes/AMEACAS-E-LIMITES-API-PRODUCAO.md)
- [Matriz endpoint × permissão × RLS](decisoes/MATRIZ-ENDPOINT-PERMISSAO-RLS.md)
- [Prompt CURSOR-014](prompts/CURSOR-014-implementar-api-producao.md)
- [Retorno CURSOR-014](retornos/CURSOR-014-retorno-execucao.md)
- [ADR interface da Panne](decisoes/ADR-INTERFACE-PANNE.md)
- [Tokens e paleta](decisoes/TOKENS-E-PALETA.md)
- [Uso dos logos](decisoes/IDENTIDADE-VISUAL.md)
- [Arquitetura frontend](arquitetura/ARQUITETURA-FRONTEND.md)
- [Autenticação OIDC/PKCE](decisoes/AUTENTICACAO-OIDC-PKCE.md)
- [Mapa de páginas](arquitetura/MAPA-DE-PAGINAS.md)
- [Quadro e filtros](arquitetura/QUADRO-E-FILTROS.md)
- [Detalhe da ordem (UI)](arquitetura/DETALHE-ORDEM-UI.md)
- [Ficha imprimível](arquitetura/FICHA-IMPRIMIVEL.md)
- [Acessibilidade](decisoes/ACESSIBILIDADE-FRONTEND.md)
- [Segurança frontend](decisoes/SEGURANCA-FRONTEND.md)
- [Estados de erro da UI](arquitetura/ESTADOS-DE-ERRO-UI.md)
- [Evidências visuais 015](arquitetura/EVIDENCIAS-VISUAIS-015.md)
- [Limitações da interface](produto/LIMITACOES-INTERFACE-015.md)
- [Prompt CURSOR-015](prompts/CURSOR-015-implementar-interface-panne.md)
- [Retorno CURSOR-015](retornos/CURSOR-015-retorno-execucao.md) — ciclo concluído
- [Prompt CHECKPOINT-GIT-001](prompts/CHECKPOINT-GIT-001-commit-push.md)
- [Retorno CHECKPOINT-GIT-001](retornos/CHECKPOINT-GIT-001-retorno.md) — concluído
- [ADR modo operacional](decisoes/ADR-MODO-OPERACIONAL.md)
- [Modo operacional](arquitetura/MODO-OPERACIONAL.md)
- [Fluxo por ator](produto/FLUXO-POR-ATOR.md)
- [Comandos e feedback](arquitetura/COMANDOS-E-FEEDBACK.md)
- [Pesagem e conferência](arquitetura/PESAGEM-E-CONFERENCIA.md)
- [Consumo operacional](arquitetura/CONSUMO-OPERACIONAL.md)
- [Etapas operacionais](arquitetura/ETAPAS-OPERACIONAIS.md)
- [Ocorrências operacionais](arquitetura/OCORRENCIAS-OPERACIONAIS.md)
- [Rendimento operacional](arquitetura/RENDIMENTO-OPERACIONAL.md)
- [Ficha e snapshots](arquitetura/FICHA-E-SNAPSHOTS.md)
- [Atualização operacional](arquitetura/ATUALIZACAO-OPERACIONAL.md)
- [Segurança e idempotência](decisoes/SEGURANCA-E-IDEMPOTENCIA.md)
- [Evidências visuais 016](arquitetura/EVIDENCIAS-VISUAIS-016.md)
- [Limitações da interface 016](produto/LIMITACOES-INTERFACE-016.md)
- [Prompt CURSOR-016](prompts/CURSOR-016-implementar-modo-operacional.md)
- [Retorno CURSOR-016](retornos/CURSOR-016-retorno-execucao.md) — aceito funcionalmente
- [Prompt CHECKPOINT-GIT-002](prompts/CHECKPOINT-GIT-002-cursor-016.md)
- [Retorno CHECKPOINT-GIT-002](retornos/CHECKPOINT-GIT-002-retorno.md) — concluído
- Projeto de UX/UI — pendente e não iniciado
- CURSOR-017 — pendente e não iniciado
- [Prompt CURSOR-011](prompts/CURSOR-011-descobrir-chao-de-fabrica.md)
- [Retorno CURSOR-011](retornos/CURSOR-011-retorno-execucao.md)

## Reconciliação

Os números ADR/REG citados em prompts anteriores **não existiam neste repositório da Panne**. Este ciclo cria os documentos canônicos sem renumerar migrações. Divergências ficam em [RECONCILIACAO.md](decisoes/RECONCILIACAO.md).
