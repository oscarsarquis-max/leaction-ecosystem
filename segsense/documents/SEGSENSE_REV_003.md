# SEGSENSE_REV_003 — Revisão de aderência da fundação de segurança

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_REV_003 |
| Título | Revisão de aderência do PRM_003 |
| Categoria | REV — revisão de etapa |
| Versão | 1.1 |
| Status | Concluída |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_ARQ_002 v1.2; SEGSENSE_SEC_001; SEGSENSE_ADR_002; SEGSENSE_API_001 v1.2; SPIDER-ARCH-017; SEGSENSE_PRM_003 |
| Escopo revisado | Segurança web deny-by-default, modelo de ator, 401/403 correlacionados; sem IdP nem integração Spider/Icatu |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Revisão da etapa PRM_003. |
| 1.1 | 04/09/2026 | Esclarecimento de independência das três aplicações (ARQ_001 v0.3); SAT inalterados. |

## 1. Evidências

- Spring Security com cadeias explícitas; form login, Basic e request cache desabilitados.
- Públicos: `system/info`, health, readiness. Demais `/api/**` deny-by-default.
- 401 `AUTHENTICATION_REQUIRED` e 403 `ACCESS_DENIED` no formato de `SEGSENSE_API_001`, com o mesmo UUID no header e no corpo.
- Correlação executa antes da decisão de segurança em `/api/**`.
- Tipos de domínio `Actor`, `ApplicationIdentity`, `ChannelContext` sem Spring Security, JWT ou servlet.
- Nenhum UserDetailsService de desenvolvimento; nenhum Resource Server.
- Fixtures de 401/403 apenas em testes.
- Frontend sem login, sem token e com tipos de erro 401/403 a partir de respostas reais.

## 2. SAT-01 a SAT-10

| ID | Situação | Comentário |
|---|---|---|
| SAT-01 | PARCIAL | Identidade local `SEGSENSE`; sem registro na Spider |
| SAT-02 | PARCIAL | Manifesto DRAFT |
| SAT-03 | NÃO IMPLEMENTADO | Sem Satellite Contract |
| SAT-04 | PARCIAL | BFF; sem sessão de usuário nem client Spider |
| SAT-05 | PARCIAL | Correlação local, inclusive em 401/403 |
| SAT-06 | NÃO APLICÁVEL NESTA ETAPA | |
| SAT-07 | NÃO APLICÁVEL NESTA ETAPA | |
| SAT-08 | PARCIAL | Deny-by-default e erros padronizados; **sem** IdP, autenticação do satélite, Guard ou Policy |
| SAT-09 | ATENDIDO | |
| SAT-10 | ATENDIDO | Operações locais públicas não usam a Spider |

SAT-08 **não** está atendido integralmente.

## 3. Riscos e débitos

- Tratar 401 em rota desconhecida como “falta de login de produto”.
- Introduzir header de usuário “só para o próximo sprint”.
- Habilitar Resource Server com issuer de exemplo.
- CSRF de `/api/**` foi isento no PRM_004 (STATELESS, sem cookie); reavaliar se houver sessão por cookie.

## 4. Independência (esclarecimento posterior)

A revisão do PRM_003 permanece válida. O `SEGSENSE_ARQ_001` v0.3 registra que SegSense, Spider e o Insurance Provider Mock futuro são aplicações fisicamente independentes. “Satellite” não incorpora o SegSense à Spider. Este esclarecimento não altera os SAT da fundação de segurança.

## 5. Conclusão

O PRM_003 adere ao recorte: superfície HTTP segura e neutra, modelo de ator puro, sem identidade fictícia. O satélite permanece não certificável. Nenhuma regra de seguros ou integração foi antecipada.
