# SEGSENSE_REV_005 — Revisão de aderência da oportunidade contextual

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_REV_005 |
| Título | Revisão de aderência do PRM_005 |
| Categoria | REV — revisão de etapa |
| Versão | 1.0 |
| Status | Concluída nesta execução |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_PRM_005; SEGSENSE_DOM_002; SEGSENSE_DAT_002; SEGSENSE_API_003; SEGSENSE_REV_004 v1.1 |
| Escopo revisado | Correção V3 do catálogo; aggregate DRAFT versionado; API e UI locais; sem IdP, Spider, Icatu, publicação ou IA |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Revisão da etapa PRM_005. |

## 1. Evidências

- Ressalva do PRM_004 resolvida no PostgreSQL pela V3: UNIQUE `(channel.id, publisher_id)` e FK composta do ambiente; prova JDBC de combinação coerente aceita e cross-publisher rejeitada; dados inconsistentes abortam a migration sem mutação.
- Volume Compose existente, sem `down -v`: o backend aplicou 2 migrations incrementais (V3 e V4); `segsense.flyway_schema_history` em v4.
- V4: oportunidade, revisão imutável e campos tipados; FKs compostas até o ambiente; `ddl-auto=none`.
- Domínio puro: revisão 1 na criação; N+1 imutável; `expectedVersion` + `baseRevision`; `NO_CONTENT_CHANGE`; somente `DRAFT`.
- API sob `/api/v1/admin/.../opportunities` com authorities próprias; anônimo 401; testes Spring Security para sucessos.
- Frontend após Environment: lista real, estados 401/403/erro/vazio, editor de definição e preview de placeholders **sem** valores de runtime nem publicação fictícia.
- ArchUnit: domínio sem Spring/JPA; sem clients Spider/Icatu.

## 2. SAT-01 a SAT-10

| ID | Situação | Comentário |
|---|---|---|
| SAT-01 | PARCIAL | Identidade local `SEGSENSE`; sem registro na Spider |
| SAT-02 | PARCIAL | Manifesto DRAFT |
| SAT-03 | NÃO IMPLEMENTADO | Sem Satellite Contract |
| SAT-04 | PARCIAL | BFF; catálogo e oportunidade locais; sem sessão de usuário nem client Spider |
| SAT-05 | PARCIAL | Correlação local em sucesso e erro, inclusive 401/403 |
| SAT-06 | NÃO APLICÁVEL NESTA ETAPA | Sem submissão de objetivo |
| SAT-07 | NÃO APLICÁVEL NESTA ETAPA | Sem execução para projetar |
| SAT-08 | PARCIAL | Deny-by-default e authorities de catálogo/oportunidade; **sem** IdP |
| SAT-09 | ATENDIDO | Sem knowledge de routes/adapters |
| SAT-10 | ATENDIDO | Rascunhos locais; nenhum envio à Spider |

O satélite permanece **não certificável**. SAT-08 não está atendido integralmente.

## 3. Riscos e débitos

- Tratar DRAFT como publicação.
- Inventar login, JWT ou header de subject no runtime.
- Receber valores dinâmicos ou renderizar template como se fosse entendimento da Spider.
- CSRF de `/api/**` isento enquanto a sessão for STATELESS e sem cookie.

## 4. Conclusão

O PRM_005 adere ao recorte: correção relacional herdada, oportunidade local versionada somente em DRAFT, API e UI honestas quanto à ausência de IdP. Nenhuma integração, IA, produto ou regra de cobertura foi antecipada.
