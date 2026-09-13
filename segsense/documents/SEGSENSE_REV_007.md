# SEGSENSE_REV_007 — Revisão de aderência do PRM_007

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_REV_007 |
| Título | Revisão de aderência do PRM_007 |
| Categoria | REV — revisão |
| Versão | 1.1 |
| Status | Concluída nesta execução |
| Data | 11/09/2026 |
| Dependências | SEGSENSE_PRM_007; SEGSENSE_PRM_007_COR_001; SEGSENSE_LNK_001; SEGSENSE_DAT_004; SEGSENSE_API_005; SEGSENSE_SEC_002 |
| Escopo revisado | Link contextual seguro; V7; APIs admin e pública; painel admin; sem página pública final, Spider, Icatu, mock, consentimento ou PII |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 11/09/2026 | Revisão da etapa PRM_007. |
| 1.1 | 11/09/2026 | Corretivo único: FK da revisão aprovada, bindings SQL e HTTPS fail-closed. |

## 1. PRM_006

PRM_006 e o corretivo único `SEGSENSE_PRM_006_COR_001` estão **aprovados**. V1–V6 não foram alteradas.

## 2. SAT-01 a SAT-10

| SAT | Situação | Evidência |
|---|---|---|
| SAT-01 | PARCIAL | Identidade local `SEGSENSE`; envelope público `applicationId=SEGSENSE`; sem registro aceito pela Spider |
| SAT-02 | PARCIAL | Manifesto preliminar inalterado; sem Satellite Contract executável |
| SAT-03 | NÃO IMPLEMENTADO | Satellite Contract não existe e não foi inventado |
| SAT-04 | PARCIAL | Browser → React → BFF; URL pública de configuração; sem sessão de usuário nem client Spider |
| SAT-05 | PARCIAL | Correlação HTTP local nas rotas `/api/**`, inclusive 401/403/410/503; sem IDs canônicos da Spider |
| SAT-06 | NÃO APLICÁVEL NESTA ETAPA | Sem submissão de objetivo nem execução assíncrona |
| SAT-07 | NÃO APLICÁVEL NESTA ETAPA | Sem execução para projetar; envelope público não materializa jornada |
| SAT-08 | PARCIAL | Deny-by-default; authorities `segsense.link.*`; CORS restrito; **sem** IdP, Guard nem Policy |
| SAT-09 | ATENDIDO | Sem knowledge de routes/adapters; frontend admin só chama o BFF |
| SAT-10 | ATENDIDO | Catálogo, governança, links e resolução pública não usam a Spider |

## 3. Decisões

- Lista tipada de bindings em vez de objeto JSON livre.
- Sem SoD extra de sujeito para emissão de link (GOV_001 não define quarto papel).
- Rate limit público documentado como gateway, não simulado.
- Logo oficial em `frontend/images/segsense logo.png` preservado e usado no shell admin.

## 4. Corretivo PRM_007_COR_001

Achados da auditoria:

1. V7 permitia, via SQL, `published_context_link.revision_number` apontar para uma revisão existente que não era `approved_revision`.
2. `ContextLinkConfiguration` relaxava HTTP sem profile ativo e com profile `default`.

Correções:

- V8: pré-validação + `opportunity_id_approved_revision_unique` + `published_context_link_approved_revision_fk`. FKs de escopo e de revisão existente preservadas.
- Auditoria de binding: SQL direto podia inserir `field_key`/`field_type` alheios à revisão. Endurecido na V8 com identidade técnica `opportunity_revision_id`, `field_source` (`PUBLISHER`/`EITHER`) e FKs compostas. Preenchimento só por derivação unívoca.
- HTTPS: só profiles ativos `local` e/ou `test`; `local,prod` e ausência de profile exigem HTTPS. `SPRING_PROFILES_ACTIVE=local` e `spring-boot.run.profiles=local`.

A execução original do PRM_007 alterou `.cursor/rules/ecosystem-focus.mdc` apesar da proibição do prompt. Este corretivo não toca `.cursor/` nem nenhum caminho fora de `segsense/`.

## 5. Riscos

Rate limit ainda não está no processo local. A experiência `/c/{token}` não foi construída. Sem IdP, o painel de emissão permanece 401 fora dos testes.

A V8 aplica-se incrementalmente no volume `:5437` sem `down -v`. V1–V7 intactas. `flyway:validate` deve cobrir schema + V1–V8.
