# SEGSENSE_REV_008 — Revisão de aderência do PRM_008

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_REV_008 |
| Título | Revisão de aderência do PRM_008 |
| Categoria | REV — revisão |
| Versão | 1.0 |
| Status | Concluída nesta execução |
| Data | 11/09/2026 |
| Dependências | SEGSENSE_PRM_008; SEGSENSE_UX_001; SEGSENSE_UX_002; SEGSENSE_UX_003; SEGSENSE_UI_001; SEGSENSE_LNK_001; SEGSENSE_API_005 |
| Escopo revisado | Sistema visual roxo/lilás/branco; admin editorial refinado; página pública `/c/{token}`; sem coleta, consentimento, Spider, Icatu ou mock |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 11/09/2026 | Revisão da etapa PRM_008. |

## 1. Etapa anterior

PRM_007 e o corretivo único `SEGSENSE_PRM_007_COR_001` estão **aprovados**. V1–V8 não foram alteradas. Nenhuma migration nova.

## 2. SAT-01 a SAT-10

| SAT | Situação | Evidência |
|---|---|---|
| SAT-01 | PARCIAL | Identidade local `SEGSENSE`; envelope público não é título de página; sem registro aceito pela Spider |
| SAT-02 | PARCIAL | Manifesto preliminar inalterado; sem Satellite Contract executável |
| SAT-03 | NÃO IMPLEMENTADO | Satellite Contract não existe e não foi inventado |
| SAT-04 | PARCIAL | Browser → React Router → BFF; página `/c/{token}` só chama o GET público; sem sessão de usuário nem client Spider |
| SAT-05 | PARCIAL | Correlação HTTP local nas rotas administrativas; resolução pública sem credencial; sem IDs canônicos da Spider |
| SAT-06 | NÃO APLICÁVEL NESTA ETAPA | Sem submissão de objetivo; CTA público é ação local |
| SAT-07 | NÃO APLICÁVEL NESTA ETAPA | Sem execução para projetar |
| SAT-08 | PARCIAL | Deny-by-default; CORS inalterado; **sem** IdP, Guard nem Policy; admin honesto sobre autenticação ausente |
| SAT-09 | ATENDIDO | Sem knowledge de routes/adapters; frontend só chama o BFF |
| SAT-10 | ATENDIDO | Catálogo, governança, links e página pública não usam a Spider |

## 3. Evidências funcionais

- Frontend: `npm run lint`, `npm test` (**45** testes) e `npm run build` aprovados.
- Roteador `react-router-dom` 7.9.1; Vite `appType: 'spa'`. Refresh de `/admin/catalogo` e `/c/{token}` devolve `index.html` 200.
- Backend: `mvnw.cmd verify` BUILD SUCCESS — **65** unitários + **22** IT. Contrato de resolução e headers inalterados.
- HTTP real: `GET /api/v1/system/info` 200; `GET /api/v1/admin/publishers` 401; token malformado `GET /api/v1/public/context-links/short` 404 `CONTEXT_LINK_NOT_FOUND`.
- PostgreSQL `:5437` healthy; volume não apagado. Zero migration nova.

## 4. Evidências de interface e acessibilidade

- Tokens `--segsense-*` conforme UX_002; primário de botão `#1800B0` sobre branco para AA em texto de controle.
- Logo oficial importado; SHA-256 antes e depois: `CEF4A9C0B8F7B0D8F2A50D85DE41FEA02498B15E3021EBB063E75945810C089D`.
- Abas com teclado, diálogo com foco inicial em “Manter link”, `aria-live` na cópia, `prefers-reduced-motion`, alvos públicos 44 px, coluna pública sem `min-width` acima de 320 px.
- Estados públicos mapeados sem códigos `CONTEXT_LINK_*` na superfície.
- Esta sessão não dispôs de ferramenta interativa de browser para screenshots nas viewports 1440/768/390/320. A verificação visual por clique real permanece como conferência humana; os testes automatizados cobrem sucesso, 404/410/503/rede, CTA local e ausência de token no DOM.

## 5. Segurança e privacidade

- Token não é persistido nem renderizado na página pública.
- Sem `localStorage`, `sessionStorage`, cookie, analytics, fonte CDN ou `dangerouslySetInnerHTML` no código da aplicação.
- Bundle de produção contém o identificador interno `dangerouslySetInnerHTML` do React; a aplicação não o utiliza.
- CORS do backend não foi alterado. Nenhum endpoint público novo.

## 6. Riscos

Sem IdP, o admin real continua 401. A página pública de sucesso no runtime depende de um link emitido de verdade; fixtures ficam só nos testes. Conferência visual humana das viewports ainda é desejável na auditoria.

## 7. Ausências confirmadas

Sem commit, push, deploy, alteração fora de `segsense/`, Spider, Panne, `.cursor/`, V1–V8, coleta, consentimento, ContextInstance, materialização de objetivo, Icatu ou mock.
