# ACTIONFINANCE_REV_001 — Evidências, divergências e validação documental

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_001 |
| Versão | 0.2 |
| Status | DOCUMENTATION_ONLY; analista aprovou com ressalvas; proprietário pendente |
| Data | 25/09/2026 |
| Objeto | ARQ_001 v0.2 e PRM_001 v0.2 |

Cursor **não** preenche aprovação do proprietário nem marca ADR ACCEPTED.

Parecer do analista (preservado): [`ACTIONFINANCE_REV_001_PARECER_ANALISTA.md`](ACTIONFINANCE_REV_001_PARECER_ANALISTA.md).

## 1. Classificação

| Informação | Classe | Fonte |
|---|---|---|
| Hub só assinaturas; AF é a gestão restante; Panne = estoque físico; Spider ≠ ledger | CONFIRMED_BY_OWNER | ARQ_001 §1; prompt 0.2 |
| Java 21; produto independente; EXPERIENCE; padaria como exemplo | CONFIRMED_BY_OWNER | ARQ_001 §1; `pom.xml` L21 |
| `finaction.com.br` registrado | CONFIRMED_BY_OWNER | DOMINIO_001 |
| `java.version` 21; Boot 3.4.2 na Spider | OBSERVED_IN_CODE | `spider/backend/pom.xml` L10, L21 |
| Boot 4.1.1 SegSense e SpiderBank | OBSERVED_IN_CODE | respectivos `pom.xml` L10 |
| Postgres 18.6; React 19.2.8; TS 5.9.3 | OBSERVED_IN_CODE | SegSense compose / package.json |
| Purpose só seguros/crédito; SYNC; EXPERIENCE sem EXECUTE | OBSERVED_IN_CODE | schemas L37–39, L69; Service L92–96 |
| Idempotência Spider em RAM | OBSERVED_IN_CODE | `SatelliteIdempotencyStore.java` L9 |
| Registry sem `actionfinance` | OBSERVED_IN_CODE | `application-local-demo.yml` L113+ |
| SpiderBank sem persistência na 1ª entrega | OBSERVED_IN_CODE | `spider-bank/database/README.md` |
| Cobrança avulsa no Hub / consumidor Loja | OBSERVED_IN_CODE | levantamento; untracked `amount-checkout.js` |
| ADRs 001–010; UX; camadas; dinheiro string | PROPOSED | ADRs e UX_001 |
| Contrato financeiro, provider, canal async, inbox | EXTERNAL_CONTRACT_PENDING | INT_001 |
| Resolução Maven/npm; portas livres; DNS/TLS; schema efetivo Hub; runtime Spider memória vs JPA | NOT_VERIFIED | sem build/serviço |

## 2. Padrão de satélite adotado

Referência estrutural: SegSense (pastas, Flyway canônico, manifesto preliminar não certificado). Papel: EXPERIENCE, como SAT-003. Independência física: ARCH-017.

Divergências intencionais:

| Tema | Referência | ActionFinance |
|---|---|---|
| Persistência na 1ª entrega | SpiderBank: ausente / memória | PostgreSQL obrigatório |
| Spring Boot | Satélites 4.1.1 | Proposto 3.4.2 (linha Spider); **não copiar POM** |
| Pacotes HTTP | SegSense `inbound/http` | Árvore alvo `interfaces/http` (F3) |
| Visual | Homepage editorial | Ferramenta operacional (AF-ADR-010) |
| Contrato | Purpose seguros/crédito | Bloqueado até PRM_005 |

Conflito técnico real: o contrato 1.2 não carrega finalidade financeira. **Impacto:** integração bloqueada. **Alternativa:** CRUD local agora; evoluir contrato na Spider depois. Decisões de negócio preservadas.

## 3. Achado fora de escopo — Hub

Cobrança avulsa (`POST /v1/checkout/amount` e correlatos) e consumidor na Loja de Pães existem no working tree, em parte não rastreados. Não comprovam publicação. Não são base da primeira fatia. **Não removidos nem expandidos.**

## 4. Fechamento R1–R4

| Item | Estado |
|---|---|
| R1 prompt integral | Fechado — `ACTIONFINANCE_PRM_001.md` |
| R2 regra global de foco | Registrado; não revertido; este incremento só `ActionFinance/` |
| R3 cluster vs tabelas | Fechado — ADR-001/003 v0.2 |
| R4 matriz INT | Fechado — INT_001 §2 |
| R5 aprovação vs desenvolvimento | Mantido; PRM_002 não executado |

## 5. Verificação documental (Etapa 4)

| Checagem | Resultado |
|---|---|
| Documentos obrigatórios do prompt | Presentes (ver índice) |
| Links internos do índice | Relativos a `architecture/`, `adr/`, `domain/`, `data/`, `integrations/`, `ux/`, `prompts/`, `reviews/` |
| Diagramas alvo vs implementado | INT_001 e ARQ §4 rotulam alvo / não implementado / contratos ausentes |
| Estados DRAFT/OPEN/CANCELLED | Consistentes; vencida derivada |
| Runtime criado | Não (sem frontend/backend/database/compose) |
| Git aninhado | Não |
| Spider/Panne/Hub/SegSense neste incremento | Sem diff rastreado nos caminhos inspecionados |
| Build/testes de runtime | **Não executados** |

HEAD observado: `7177805b`. Branch: `feat/sponge-lojadepaes-145`. Untracked preexistente em Hub/Panne permanece; autoria não atribuída a este prompt.

## 6. Parecer

| Papel | Data | Resultado |
|---|---|---|
| Analista | 25/09/2026 | Aprovado com ressalvas (parecer associado); R1–R4 tratados na documentação |
| Proprietário | — | Pendente |
| Cursor | — | Sem autoaprovação |

## 7. Insumos ao PRM_002 (não implementado)

O analista já escreveu [`../prompts/ACTIONFINANCE_PRM_002.md`](../prompts/ACTIONFINANCE_PRM_002.md). Este REV não o substitui nem o executa.

Insumos que a fundação precisará, quando autorizada:

- Java 21; Spring Boot 3.4.2 observado; MVC; sem POM Boot 4
- Inventário de portas locais; container/volume dedicados
- Banco/schema/usuário `actionfinance`; Flyway a partir de `database/migrations`
- Identidade demo explícita, deny-by-default, sem fallback
- Health/ready locais sem Spider
- Sem contas a pagar, sem integração, sem tela de gestão
- Demonstrar resolução de dependências; não inferir de README
- `finaction.com.br` não configura CORS/produção

## Encerramento pelo analista

Após verificar o retorno final: **APROVADO tecnicamente**, R1–R4 fechados, sem ressalvas abertas deste ciclo. Ver [encerramento](ACTIONFINANCE_REV_001_ENCERRAMENTO.md). O parecer anterior permanece como histórico. PRM_002 v0.2 preparado; execução somente por instrução do proprietário ao Cursor.
