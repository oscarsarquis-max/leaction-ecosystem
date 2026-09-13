# SEGSENSE_REV_004 — Revisão de aderência do catálogo administrativo

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_REV_004 |
| Título | Revisão de aderência do PRM_004 |
| Categoria | REV — revisão de etapa |
| Versão | 1.1 |
| Status | Concluída nesta execução |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_PRM_004; SEGSENSE_DOM_001; SEGSENSE_DAT_001; SEGSENSE_API_002; SEGSENSE_ARQ_001 v0.3 |
| Escopo revisado | Catálogo local Publisher/Channel/ContextualEnvironment; independência das três aplicações; sem IdP, Spider, Icatu ou mock |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Revisão da etapa PRM_004. |
| 1.1 | 04/09/2026 | Ressalva de FK independente do ambiente registrada; resolução pela V3 no PRM_005. |

## 1. Evidências

- `SEGSENSE_ARQ_001` v0.3 vigente, com §26.9 de independência física.
- Três aplicações independentes documentadas: SegSense, Spider, Insurance Provider Mock futuro. “Satellite” = padrão de integração.
- Aggregates e transições no domínio puro; casos de uso com autoria obrigatória; JPA só em infrastructure.
- Flyway V2 no schema `segsense`, sem alterar V1, sem `CASCADE`, `ddl-auto=none`.
- API `/api/v1/admin/**` com authorities `segsense.catalog.read` / `segsense.catalog.write`; anônimo 401; sem login.
- Frontend honesto no 401; sem fixtures de runtime; CRUD real bloqueado.
- Testes de domínio, Testcontainers, segurança, ArchUnit e frontend.
- Nenhuma integração Spider/Icatu/mock; nenhum dado pessoal cadastral.

## 2. SAT-01 a SAT-10

| ID | Situação | Comentário |
|---|---|---|
| SAT-01 | PARCIAL | Identidade local `SEGSENSE`; sem registro na Spider |
| SAT-02 | PARCIAL | Manifesto DRAFT |
| SAT-03 | NÃO IMPLEMENTADO | Sem Satellite Contract |
| SAT-04 | PARCIAL | BFF; catálogo local; sem sessão de usuário nem client Spider |
| SAT-05 | PARCIAL | Correlação local, inclusive no catálogo e em 401/403 |
| SAT-06 | NÃO APLICÁVEL NESTA ETAPA | Sem submissão de objetivo |
| SAT-07 | NÃO APLICÁVEL NESTA ETAPA | Sem execução para projetar |
| SAT-08 | PARCIAL | Deny-by-default e authorities de catálogo; **sem** IdP |
| SAT-09 | ATENDIDO | Sem knowledge de routes/adapters |
| SAT-10 | ATENDIDO | Catálogo local não usa a Spider |

O satélite permanece **não certificável**. SAT-08 não está atendido integralmente.

## 3. Riscos e débitos

- Tratar a UI administrativa como CRUD operacional.
- Inventar usuário, JWT ou header de subject “só para demonstrar o módulo”.
- Interpretar “satellite” como módulo interno da Spider.
- CSRF de `/api/**` isento enquanto a sessão for STATELESS e sem cookie; reavaliar quando houver cookie de sessão.

## 4. Conclusão

O PRM_004 adere ao recorte: catálogo local, isolamento hierárquico, persistência V2 e API protegida, com independência das três aplicações registrada. Nenhuma regra de seguros, jornada ou integração foi antecipada.

**Ressalva (transportada e resolvida no PRM_005):** as FKs independentes de `contextual_environment.publisher_id` e `channel_id` permitiam no banco a combinação Publisher A + Channel B. A etapa foi **aprovada com ressalva**. A V3 (`V3__enforce_environment_catalog_scope.sql`) resolve a invariante sem alterar V1/V2: detecta inconsistências e aborta sem mutar dados; UNIQUE em `channel(id, publisher_id)`; FK composta `(channel_id, publisher_id)`. Evidências em `SEGSENSE_REV_005` e `SEGSENSE_DAT_002`.
