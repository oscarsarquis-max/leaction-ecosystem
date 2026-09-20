# SEGSENSE_UI_001 — Arquitetura implementada do frontend

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_UI_001 |
| Título | Arquitetura do frontend: rotas, shells e componentes |
| Categoria | UI — implementação de interface |
| Versão | 1.5 |
| Status | Vigente nesta etapa |
| Data | 15/09/2026 |
| Dependências | SEGSENSE_UX_001; SEGSENSE_UX_002; SEGSENSE_UX_003; SEGSENSE_API_005; SEGSENSE_API_006; SEGSENSE_PRM_009 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 11/09/2026 | Rotas React, tokens `--segsense-*`, shells admin/público e página `/c/{token}`. |
| 1.1 | 11/09/2026 | Ressalvas PRM_008; aba Finalidade; jornada pública progressiva; credencial só em memória. |
| 1.2 | 12/09/2026 | Credencial no escopo da jornada; BOOLEAN Sim/Não; blocos com Voltar/revisar; sem coerção silenciosa. |
| 1.3 | 12/09/2026 | `/` passou a ser a entrada pública de posicionamento; `/demonstracao/icatu` permanece cenário. |
| 1.4 | 14/09/2026 | PRM_018: `SegSenseLogo` usa recorte de margem; tokens de altura por superfície. |
| 1.5 | 15/09/2026 | PRM_019_COR_001: cotação simulada com explicação humana derivada; códigos só no `details`; `MISSING_CONTEXT` sem seções ilustrativas vazias. |

## 1. Decisão de roteamento

O frontend usa `react-router-dom` 7.18.3, estável com React 19. A decisão cobre navegação direta, `NavLink` e refresh: o Vite permanece `appType: 'spa'`, devolvendo `index.html` para rotas profundas.

```text
/                              Entrada pública de posicionamento
/demonstracao/icatu            Cenário demonstrativo Icatu (não oficial)
/admin                         Início editorial (401 sem IdP)
/admin/catalogo                Publicador → Canal → Ambiente
/admin/oportunidades            Lista no contexto selecionado em memória
/admin/oportunidades/:id       Abas Conteúdo / Governança / Finalidade / Links
/c/:token                      Página pública mobile-first
```

IDs na rota administrativa não são rótulos visuais. A seleção de catálogo vive só no estado React da sessão; não há `localStorage` nem `sessionStorage`. Sem contexto, a lista de oportunidades pede retorno honesto ao catálogo.

Não há tela de login. Sem IdP, o admin continua declarando que a autenticação administrativa não está configurada.

## 2. Superfícies

| Superfície | Shell | Densidade |
|---|---|---|
| Admin | `AdminShell` — cabeçalho horizontal, logo ~60 px de marca visível + nome, navegação, estado do ambiente | ferramenta editorial |
| Pública | `PublicShell` — logo 104–136 px de marca visível, coluna de leitura, sem navegação admin | convite contextual |

Ambas usam tokens `--segsense-*` (UX_002). O visitante nunca vê o admin. O admin nunca simula cotação.

## 3. Cliente HTTP

- Admin: clientes existentes (`systemInfo`, `catalog`, `opportunity`, `links`) com correlação.
- Público: `fetchPublicContextLink` e, se `continuity.available`, mutações da instância com header `X-SegSense-Instance-Credential`. Credencial só em `useRef` da jornada ativa (não em módulo, storage nem cookie). `credentials: 'omit'`.
- Frontend chama somente o BFF SegSense (`VITE_API_BASE_URL`).

## 4. Componentes

| Componente | Papel |
|---|---|
| `SegSenseLogo` | Display `frontend/images/segsense-logo-header.png`; original `segsense logo.png` intacto |
| `AdminShell` / `PublicShell` | Layouts distintos |
| `HumanStatus` | Estados humanos com ícone + título + texto |
| `AsyncState` | Carregamento / erro / vazio |
| `ContextSummary` | Superfície lilás do contexto não pessoal |
| `TechnicalAuditDetails` | `<details>` só no admin |
| `DestructiveConfirmation` | Diálogo de revogação |
| `CopyOnceLink` | URL uma vez + `aria-live` + descarte |
| `OpportunityTabs` | Abas acessíveis, inclusive Finalidade e transparência |
| `PublicTransparency` | “O que acontece agora?” quando a continuidade ainda não está disponível |
| `PublicProgressiveJourney` | Sessão local: transparência, campos, autorização explícita e retirada |
| `IntegratedMvpPage` | Jornada pública: intenção livre, perguntas, cotação simulada ou possibilidades ilustrativas |
| `ConsentNoticePanel` | CRUD versionado do aviso na aba administrativa |

## 5. Resumo público

`materializeContextSummary` substitui apenas placeholders com valor do publicador e devolve texto React. Sem aviso aprovado, o CTA funcional permanece **Entender os próximos passos**. Com aviso aprovado, o CTA passa a **Continuar com segurança** e inicia a sessão local. `callToActionLabel` continua virando finalidade textual; linguagem enganosa (“Contratar agora”) é neutralizada. A credencial da instância não é persistida nem renderizada.

## 6. Fora desta arquitetura

IdP, consentimento jurídico válido, Spider, Icatu, mock, busca/filtro/paginação sem API, analytics e fonte por CDN.
