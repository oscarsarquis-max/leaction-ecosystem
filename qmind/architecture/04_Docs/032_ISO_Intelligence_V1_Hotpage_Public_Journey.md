# ISO Intelligence V1 — Hotpage e Jornada Pública V2 (ISOI-011)

- Status: **Em revisão** (implementação Core frontend + docs; aguarda gate e commit)
- Data: 2026-08-26
- Produto: QMind Core (`qmind/`)
- Baseline Core: `9d17fee` — `feat(qmind): add iso intelligence cockpit` (ISOI-010 pinado)
- Baseline QMind OI: `34ead2ef471a064c8d035d569761e2afde4519c1` — **zero alteração funcional**
- Escopo: frontend público/tour + documentação arquitetural
- Fora de escopo: backend, migration, CMS, analytics, deploy, ISOI-012

## 1. Objetivo e público-alvo

Atualizar a apresentação pública (`/`) e a apresentação guiada autenticada (`/guided-tour`) para refletirem o produto após ISOI-006…ISOI-010: avaliação → Improvement Case → OI → execução → medição → Execution Intelligence → Cockpit → decisão humana.

**Público**

- Interlocutor anônimo: entender o ciclo sem dados privados.
- Apresentador autenticado: demonstrar fatos reais da organização selecionada, sem mutar.

## 2. Mapa público → login → tour → telas reais

```text
/  Hotpage pública V2 (estática)
        │
        ├─ CTA conhecer jornada (#qm-metodo)
        ├─ CTA entrar → /login?return=/assessments (allowlisted)
        └─ CTA apresentação → /login?return=/guided-tour[?chapter=…]
                │
                ▼
        /guided-tour (AppShell, org obrigatória)
                │  GETs existentes apenas
                ├─ /assessments[/:id/guided]
                ├─ /improvement-cases/:id
                ├─ /execution[/cards/:id]
                └─ /cockpit
                     └─ banner → retorno ao capítulo
```

Não há backend de apresentação, CMS nem endpoint público de dados.

## 3. Jornada V2 e vocabulário compartilhado

Fonte canônica: `web/src/journeyV2/` (capítulos, exemplo ilustrativo, capacidades, resolvers).

| # | id | Rótulo | Destino autenticado preferencial |
|---|----|--------|----------------------------------|
| 1 | understand | Compreender | `/assessments` |
| 2 | assess | Avaliar | `/assessments/:id/guided` |
| 3 | recognize | Reconhecer | `/improvement-cases/:id` |
| 4 | analyze | Analisar | `/improvement-cases/:id` |
| 5 | execute | Executar | `/execution` ou card |
| 6 | evidence_measure | Medir | caso / Evolution |
| 7 | interpret | Interpretar | caso / EI histórico |
| 8 | control | Controlar | `/cockpit` |
| 9 | decide | Decidir | caso / Evolution |

Contrato narrativo Core ↔ OI:

```text
Core conserva fatos e decisões
        ↓ contrato HTTP versionado
OI interpreta sem ler o banco do Core
        ↓ resultado explicável
Core persiste histórico, fatos de suporte e limitações
```

## 4. Limite público × privado

- `/` fora do AppShell; sem organização; sem fetch tenant/OI/Cockpit/board/cases.
- Exemplos com badge permanente **Exemplo ilustrativo**; conteúdo estático versionado.
- Dados reais só após autenticação, autorização e organização selecionada.
- Nenhum UUID/e-mail/token de organização real no DOM público.

## 5. Modelo de capítulos e resolução de contexto

- Conteúdo de fala: `demonstrate` / `message` / `limitation`.
- Requisito: `organization` | `assessment` | `case` | `action` | `cockpit`.
- `resolveTourStepAvailability` — determinístico; preferências documentadas no código:
  - avaliação: `selectFocusAssessment`;
  - caso: acting → reviewing → analyzing → open → closed, depois `updated_at` desc;
  - ação: não concluídas primeiro, depois `updated_at` desc.
- Seleção manual de avaliação/caso quando houver múltiplas opções.
- Troca de organização limpa picks e reinicia progresso (tenant-scoped).

## 6. Segurança, RBAC, tenancy e ausência de mutação

- Tour: somente GETs para localizar destinos; sem POST/PATCH/PUT/DELETE; sem disparar OI/EI.
- `unavailable`: texto humano do que falta — sem criar dado no tour.
- `forbidden`: papel sem acesso ao destino (mesmos gates de leitura do produto).
- Capítulos via `?chapter=` allowlisted (`parseChapterParam`); inválido → início.
- Return URL: `isSafeReturnUrl` (path relativo; bloqueia `/`, `/login`, externos, `javascript:`).
- Estado do tour versionado (`qmind.guidedTour.version=2`); v1 reinicia com segurança.

## 7. CTAs e return URL

| Estado | Entrar | Apresentação |
|--------|--------|--------------|
| Anônimo | login → `/assessments` | login → `/guided-tour` (+ capítulo opcional) |
| Autenticado | `/assessments` | `/guided-tour` direto |

## 8. Acessibilidade e performance

- Tablists com `aria-controls` / `aria-selected` / painéis; setas no foco.
- Progresso com `role="progressbar"`; foco visível; `prefers-reduced-motion`.
- Sem rede na hotpage; sem fontes externas novas; GuidedTour continua lazy.
- Sem vídeo autoplay; sem analytics externo novo.

## 9. Testes e evidências

- Vitest: `hotpage.test.tsx`, `guidedTour.test.ts`, `GuidedTourPage.test.tsx`, `returnUrl.test.ts`.
- Playwright: `e2e/isoi-011-public-journey.spec.ts`, `e2e/isoi-011-guided-tour.spec.ts` (guarda de mutação armada pós-login).
- Gates: typecheck, build produção, regressões de navegação afetadas.

## 10. Roteiro de apresentação — 3 minutos

1. Hotpage: hero + decisões humanas (30s).
2. Jornada: Avaliar → Reconhecer → Executar → Cockpit (90s).
3. Login → tour: abrir Cockpit e voltar pelo banner (60s).

## 11. Roteiro de apresentação — 8 minutos

1. Princípios e limites (1 min).
2. Percorrer Jornada V2 na hotpage (2 min).
3. Exemplo ilustrativo estático (1 min).
4. Tour autenticado: avaliação ou caso existente; análise OI **já persistida** (sem novo run) (2 min).
5. Board/execução se houver card; senão unavailable honesto (1 min).
6. Cockpit: fila e freshness; fechar com “humanos decidem” (1 min).

## 12. Roteiro de apresentação — 15 minutos

Inclui o de 8 minutos e aprofunda:

- Evidência contextual e meta ≠ eficácia.
- Execution Intelligence: histórico e limitações (sem POST).
- Evolution / outcome quando existir.
- Troca de organização (se houver segunda membership) para mostrar limpeza de contexto.
- Preparação fora do tour quando `unavailable`.

## 13. Limitações e preparação do próximo incremento

- Sem CMS; textos no frontend.
- Tour não prepara dados; organização demo precisa existir.
- Screenshots não são gate deste incremento.
- ISOI-010 permanece baseline em Core `9d17fee`.
- **Não iniciar ISOI-012** neste incremento.
- URLs operacionais (docs apenas): piloto `https://qmind.com.br/` · homolog `https://app.homolog.qmind.com.br/`.
