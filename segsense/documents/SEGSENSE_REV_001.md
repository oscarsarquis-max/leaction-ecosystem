# SEGSENSE_REV_001 — Revisão de aderência da fundação ao SEGSENSE_ARQ_001 e ao SPIDER-ARCH-017

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_REV_001 |
| Título | Revisão de aderência da fundação ao ARQ_001 e ao SPIDER-ARCH-017 |
| Categoria | REV — revisão de etapa |
| Versão | 1.2 |
| Status | Concluída |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_ARQ_001 v0.2; SPIDER-ARCH-017 (PROPOSED); SEGSENSE_PRM_001 v1.0; SEGSENSE_PRM_001_COR_001 v1.1 |
| Escopo revisado | Fundação técnica em `C:\Projetos\segsense` após o PRM_001; sem alteração de código neste corretivo |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Revisão só contra o ARQ_001. |
| 1.1 | 04/09/2026 | Reconciliação com SPIDER-ARCH-017 e avaliação SAT-01 a SAT-10. |
| 1.2 | 04/09/2026 | Correções herdadas: ARQ vigente v0.2; conflito ARQ §12 × ARCH-017 encerrado pelo adendo ARQ §26. |

## 1. Método

Foram lidos integralmente `documents/SEGSENSE_ARQ_001.md` e `documents/references/SPIDER-ARCH-017.md` (este último SHA-256 `B4E64959A64F633874E115388817C9C7A3F071AA909AF6C7D850C6C3333AF337`, idêntico ao anexo de origem). A fundação foi confrontada com o recorte do PRM_001: ambiente local, sem regras de seguros, sem Satellite Contract, sem Manifest fictício e sem clients. Nenhum código de backend, frontend, banco ou Compose foi alterado.

## 2. Itens aderentes

### 2.1 SEGSENSE_ARQ_001

- Stack PostgreSQL, Java e React (ARQ §17.1), com versões fixadas pelo PRM_001.
- Aplicação modular, sem microsserviços nem engine paralela à Spider (ARQ §§1, 11, 17.2).
- Icatu não é dependência estrutural do domínio (ARQ §5.6).
- Capability não é sistema, rota ou adapter (ARQ §5.5).
- Interface com estado real; ausência não é apresentada como sucesso (ARQ §§5.8, 5.9, 20).
- Sem entidades de negócio do §18 e sem o recorte funcional do §21.
- Fora de escopo do §22 respeitado.

### 2.2 SPIDER-ARCH-017

- SegSense posicionado como primeiro satélite de referência de seguros (ARCH §§29, 42); ainda só como fundação técnica, não como satélite certificado.
- Backend Java / Spring Boot é o único candidato a **Satellite BFF**; o frontend só fala com a API SegSense (ARCH §§5–7, 34).
- Frontend não chama a Spider nem guarda credenciais técnicas (ARCH §§6, 37).
- Não há Intent Router, Context Guard, Execution Plan, Capability Resolver, routes/adapters nem orquestração no satélite (ARCH §§3, 7, 37).
- Não há máquina de estados operacional paralela (ARCH §§18–20).
- Operações locais (página de ambiente, `system/info`, health) não passam pela Spider (ARCH §28, SAT-10).
- Nenhuma integração real foi declarada; o boundary documentado permanece `SIMULATED_INFRASTRUCTURE / MOCK_ONLY` (ARCH §41).
- Icatu tratada nos READMEs como executor potencial de capability, não como integração do satélite (ARCH §§31, 37).

## 3. Divergências encontradas

Não corrigidas em código neste corretivo.

| Origem | Fundação / leitura | Natureza |
|---|---|---|
| ARQ §17.2 árvore (consoles, `api/`, `contextual-link`, `database/documentation`) | Árvore do PRM_001 | Layout adiado; decisão no PRM_002 |
| ARQ §12 modalidades de integração Icatu no SegSense | ARCH-017 e ARQ §26: satélite não escolhe nem implementa integração operacional com a Icatu | **Resolvido arquiteturalmente.** O adendo ARQ §26 declara precedência do SPIDER-ARCH-017. A Icatu é executor potencial resolvido pela Spider, não integração operacional direta do SegSense. ADR_001 formaliza a decisão no PRM_002. |
| ARQ §10 “manter os contratos funcionais com a Spider” | Contrato estável é o Satellite Contract (ARCH §8), ainda não implementado | Complementar; implementação futura, não nesta etapa |
| ARCH §§8–13 Satellite Contract e Manifest | Ausentes de propósito (proibidos neste COR) | Lacuna de certificação, não de PRM_001 |
| ARCH §41 MOCK_ONLY | Fundação não contém mock de Spider/Icatu | Correto: MOCK_ONLY descreve o boundary da plataforma, não autoriza client falso no satélite |

## 4. Riscos

- Tratar a pasta `services/icatu-integration` como futuro adapter do SegSense reintroduziria o anti-pattern do ARCH §37. Os READMEs agora vedam essa leitura.
- Implementar Satellite Contract executável ou Manifest certificado nesta fundação violaria o boundary `MOCK_ONLY`.
- `SEGSENSE_ARQ_001` v0.2 e `SPIDER-ARCH-017` PROPOSED podem evoluir e invalidar trechos desta revisão.

## 5. Situação SAT-01 a SAT-10

Certificação de Spider Satellite (ARCH §33). Nada é marcado como implementado se não existe no código.

| ID | Requisito | Situação | Evidência |
|---|---|---|---|
| SAT-01 | Application Identity (`applicationId` único) | NÃO IMPLEMENTADO | Não há identidade de satélite no código nem manifesto. |
| SAT-02 | Satellite Manifest | NÃO IMPLEMENTADO | Criação fictícia foi proibida neste corretivo. |
| SAT-03 | Spider Satellite Contract | NÃO IMPLEMENTADO | Contrato não foi implementado; implementação foi proibida neste corretivo. |
| SAT-04 | BFF | PARCIAL | Existe backend Java que o frontend consome; ainda não há identidade de satélite, cliente Spider, sessão de plataforma nem correlação. |
| SAT-05 | Correlation ponta a ponta | NÃO IMPLEMENTADO | Não há `requestId` / `decisionId` / `executionId` de plataforma. |
| SAT-06 | Execução assíncrona | NÃO APLICÁVEL NESTA ETAPA | Não há submissão de objetivo nem execução Spider a acompanhar. |
| SAT-07 | Journey Projection | NÃO APLICÁVEL NESTA ETAPA | Não há execução para projetar; a UI local não inventa progresso operacional. |
| SAT-08 | Security (Guard/Policy/permissions) | PARCIAL | Segredos fora do Git, CORS restrito, health sem detalhes; sem autenticação de satélite, Manifest, policy ou Guard. |
| SAT-09 | No Route Knowledge | ATENDIDO | Frontend e backend não conhecem routes/adapters; READMEs proíbem esse acoplamento. |
| SAT-10 | Independence (operações locais sem Spider) | ATENDIDO | Ambiente, `system/info` e health são locais e não usam a Spider. |

## 6. Questões em aberto

Permanecem as do ARQ §24 e as validações pré-integração do ARCH §42 (Contract, BFF completo, Manifest, objective, preview, confirmação, jornada async, projeção, security, correlation). Nenhuma foi respondida por código nesta fundação.

## 7. Conclusão

A fundação do `SEGSENSE_PRM_001` **adere** aos princípios das duas arquiteturas no recorte autorizado: SegSense como Insurance Reference Satellite em construção, backend Java como Satellite BFF previsto, Spider como dona da decisão/execução, Icatu como executor potencial e não como integração do satélite, boundary `SIMULATED_INFRASTRUCTURE / MOCK_ONLY`, sem clients fictícios.

O satélite **ainda não é certificável** (SAT-01 a SAT-03 e SAT-05 não implementados na fundação PRM_001; SAT-04 e SAT-08 parciais). Essa lacuna é esperada naquele recorte; identidade, manifesto preliminar e correlação local seguem no `SEGSENSE_PRM_002`.

A aparente tensão entre ARQ §12 e SPIDER-ARCH-017 **não é mais conflito normativo aberto**. O adendo ARQ §26 declara expressamente a precedência do SPIDER-ARCH-017: a Icatu será executor potencial resolvido pela Spider, não integração operacional direta do SegSense. Código da fundação PRM_001 permanece intocado nesta revisão.
