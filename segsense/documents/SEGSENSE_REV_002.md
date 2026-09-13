# SEGSENSE_REV_002 — Revisão de aderência da arquitetura interna

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_REV_002 |
| Título | Revisão de aderência do PRM_002 ao ARQ_001, ARQ_002 e SPIDER-ARCH-017 |
| Categoria | REV — revisão de etapa |
| Versão | 1.0 |
| Status | Concluída |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_ARQ_001 v0.2; SEGSENSE_ARQ_002 v1.0; SEGSENSE_ADR_001 v1.0; SEGSENSE_API_001 v1.0; SPIDER-ARCH-017; SEGSENSE_PRM_002 |
| Escopo revisado | Identidade, manifesto preliminar, correlação HTTP, camadas, ArchUnit e convenções; sem client Spider/Icatu |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Revisão da etapa PRM_002. |

## 1. Método

Leitura integral de ARQ_001 v0.2, ARQ_002, ADR_001, API_001, SPIDER-ARCH-017 e do código backend/frontend após o PRM_002. As correções herdadas da REV_001 v1.2 (ARQ vigente v0.2; conflito §12 encerrado) foram pressuposto, não reabertas.

## 2. Evidências de aderência

- `applicationId` único `SEGSENSE` em configuração tipada, manifesto e `GET /api/v1/system/info`.
- Manifesto `DRAFT / NOT_CERTIFIED`, schema preliminar, não executável, não aceito pela Spider; falha de subida se o id divergir.
- Browser/React chama só o BFF; CORS origem explícita; `X-Correlation-ID` permitido e exposto.
- Correlação local por UUID; MDC limpo; erros com `correlationId` e mensagem em português, sem detalhes internos.
- Camadas `domain` / `application` / `inbound.http` / `infrastructure` com ArchUnit.
- Ausência de Intent Router, Context Guard, Execution Plan, Capability Resolver, routes e clients Spider/Icatu.
- Frontend reflete `applicationId` e estados reais (disponível / indisponível / payload inválido).
- ADR_001 proíbe integração operacional direta SegSense–Icatu para o plano Spider.

## 3. Avaliação SAT-01 a SAT-10

Nada é marcado como certificado se a Spider não participa.

| ID | Requisito | Situação | Evidência | Débito |
|---|---|---|---|---|
| SAT-01 | Application Identity | PARCIAL | Config + manifesto + `system/info` | Sem registro/aceitação pela Spider |
| SAT-02 | Satellite Manifest | PARCIAL | YAML local `DRAFT / NOT_CERTIFIED` | Não é manifesto certificado |
| SAT-03 | Satellite Contract | NÃO IMPLEMENTADO | Proibido nesta etapa | Contrato executável futuro |
| SAT-04 | BFF | PARCIAL | React → BFF; sem credenciais no FE | Sem sessão, auth de usuário ou client Spider |
| SAT-05 | Correlation | PARCIAL | `X-Correlation-ID` local | Sem IDs canônicos da Spider |
| SAT-06 | Async | NÃO APLICÁVEL NESTA ETAPA | Sem objetivo | Execução assíncrona futura |
| SAT-07 | Journey Projection | NÃO APLICÁVEL NESTA ETAPA | UI local não inventa progresso | Projeção read-only futura |
| SAT-08 | Security | PARCIAL | CORS, erros limpos, health opaco | Sem Guard, Policy, permissões concedidas |
| SAT-09 | No Route Knowledge | ATENDIDO | ArchUnit + ausência de routes | Manter na evolução |
| SAT-10 | Independence | ATENDIDO | Health e system/info locais | Manter na evolução |

## 4. Riscos e débitos

- Tratar o YAML preliminar como contrato aceito pela Spider.
- Colapsar `correlationId` local com `requestId`/`executionId`.
- Implementar client Icatu “temporário” (rejeitado pelo ADR_001).
- Árvore ARQ §17.2 (consoles, `contextual-link`) continua adiada.
- Boundary `SIMULATED_INFRASTRUCTURE / MOCK_ONLY` permanece; nenhuma integração real foi declarada.

## 5. Conclusão

O PRM_002 **adere** ao recorte autorizado: Satellite BFF formalizado, identidade local, manifesto não certificado, correlação HTTP e camadas protegidas por teste. O satélite **não é certificável**. A Icatu permanece executor potencial resolvido pela Spider. Não houve integração, intent, plano, capability ou jornada inventada.
