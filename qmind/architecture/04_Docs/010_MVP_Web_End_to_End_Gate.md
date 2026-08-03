# QMind — Gate MVP ponta a ponta (frontend / web)

- Status: **APROVADO** (2026-08-03)
- Pré-requisito: Gate domínio `009_MVP_End_to_End_Gate.md` + fatias UI até Relatório (`a7b4c64`) + estabilização Vitest (`8a17041`)
- Harness: Playwright Chromium contra **build de produção** (`vite preview :4178` com proxy → API `:8008`) + PostgreSQL real (`qmind` @ `leaction_db:5433`)
- Suite: `../../web/e2e/mvp-web-gate.spec.ts`
- Runner: `../../web/scripts/run-mvp-web-gate.ps1`
- Nomenclatura: database lógico **`qmind`** · cluster/serviço **`leaction_db`** (`localhost:5433`)

## 1. Escopo validado

```
Build produção sem erros
→ Auth MODE=dev (contrato Cognito preparado / prod bloqueia dev)
→ Duas organizações + troca de tenant (abort/cache)
→ Assessment real (Postgres) → Evidence upload/download
→ Finding SoD (autor não aprova)
→ Plano vazio justificado → fase report
→ Snapshot relatório → submit → SoD publish → publish por QM
→ Job export-pdf queued
→ Assessment close → reopen
→ Refresh direto de rotas
→ Storage sem tokens/tenant payloads
→ Console sem erros inesperados
```

Complemento automatizado (unit/jsdom): tenant switch/abort (`tenantSwitch.test.tsx`), storage (`storage.test.ts`), env Cognito/prod (`env.test.ts`), suite web 43 testes.

Complemento domínio (API): `009_MVP_End_to_End_Gate.md` — SoD, RLS, snapshot imutável, supersede, job idempotente, waiver.

## 2. Checklist do gate

| # | Critério | Evidência | Resultado |
|---|---|---|---|
| W1 | Build de produção sem erros | `npm run build:gate` → `tsc -b && vite build` OK (`dist/` gerado) | PASS |
| W2 | Autenticação dev + contrato Cognito | Dev: shell autentica com headers `X-Dev-*`; Cognito: `AuthProvider` + `InMemoryWebStorage` + env exige authority/client; `env.test.ts` bloqueia `AUTH_MODE=dev` em `ENVIRONMENT=prod` | PASS |
| W3 | Jornada completa com backend + Postgres reais | Playwright + API via preview proxy; assessment/evidence/finding/plan/report/close/reopen no DB `qmind` | PASS |
| W4 | Duas organizações / troca de tenant | `POST /organizations` cria Org B; seletor troca Demo ↔ B; `preferredOrganizationId` em sessionStorage | PASS |
| W5 | Cancelamento de requests + limpeza de cache | Exercício de switch no browser + cobertura unitária `tenantSwitch` / `abortRegistry` / `qmindApi` (abort + geração) | PASS |
| W6 | SoD nas aprovações | Finding: banner + approve disabled para autor; Report: banner + publish disabled para autor; publish via QM distinto (seed SQL) | PASS |
| W7 | Upload e download de evidência | `authorize` → `PUT /bytes` → `receive` → `security_pass`; `download-url` + `GET /bytes` com payload > 0 | PASS |
| W8 | Snapshot e publicação do relatório | UI cria draft (sem maturidade, com plano), submit; QM publica; status `publicado` | PASS |
| W9 | Job de exportação e falha | UI `report-export-pdf` → job `queued`; reexport idempotente sem 5xx; falhas 4xx de domínio cobertas por banners/`ApiErrorBanner` + unitários de conflito | PASS |
| W10 | Fechamento e reabertura | UI close → `closed` → reopen com motivo → `report` | PASS |
| W11 | Refresh direto em cada rota | Reload em `/assessments/:id` e `/assessments` após navegação | PASS |
| W12 | Sessão expirada | Em `AUTH_MODE=dev` não há TTL Cognito; caminho `invalid_session` implementado no `AuthProvider` (Cognito expired/logout). Exercício real Cognito **não** rodado (sem pool). | PASS* |
| W13 | Loading / vazio / 403 / 404 / 409 / 422 / indisponibilidade | 404 UUID inexistente → `api-error`/mensagem; SoD 403 no domínio; 409/422 em unitários Findings/Maturity; loading/empty em `StatePanels` + listas. Indisponibilidade total da API: não derrubamos o backend nesta rodada (proxy `/health` OK). | PASS* |
| W14 | Teclado e foco em diálogos | Diálogo `plan-confirm` (`role=dialog`) aberto; Tab + Cancelar | PASS |
| W15 | Sem tokens/evidências/tenant no storage | Apenas `qmind.preferredOrganizationId` (UUID) em sessionStorage; scan sem JWT/`eyJ` | PASS |
| W16 | Ausência de erros inesperados no console | Filtro Playwright: sem pageerror/console.error além de ruído 404 intencional | PASS |

\*PASS com ressalva documentada (dev auth / sem outage forçado).

## 3. Ambiente da execução

| Item | Valor |
|---|---|
| Data/hora | 2026-08-03 (~14:30 -03:00) |
| Commit base UI (Relatório) | `a7b4c64` — `feat(qmind): add report review publish and export UI` |
| Commit estabilização Vitest | `8a17041` — `test(qmind): stabilize web suite and constrain Vitest workers` |
| Commit deste gate (harness + doc) | *(este commit)* |
| Tag anotada | `mvp-fullstack-v0` |
| Frontend | build produção + `vite preview` `127.0.0.1:4178` (proxy `/api`→`:8008`) |
| Backend | uvicorn `:8008`, `AUTH_MODE=dev`, `ENVIRONMENT=local`, `STORAGE_BACKEND=memory` |
| Database | `qmind` @ `localhost:5433` (Docker `leaction_db`) |
| Org Demo | `088a3007-4e52-47ff-ba4c-007a0396ca4a` (`QMind Demo Org`) |
| Browser | Playwright Chromium |

## 4. Resultado dos testes

### Produção

```text
npm run build:gate
✓ tsc -b && vite build  (dist OK)
```

### Playwright (browser real)

```text
npx playwright test
1 passed (mvp-web-gate.spec.ts)
```

### Suite unitária web

```text
npm test   # vitest --pool=threads --maxWorkers=2
13 files / 43 tests passed
(e2e/ excluído do Vitest)
```

### Domínio (referência)

Ver `009_MVP_End_to_End_Gate.md` — API E2E duas orgs **APROVADO**.

## 5. Limitações conscientes (piloto)

1. **Cognito end-to-end** com IdP real não foi exercitado; contrato + bloqueio prod→dev validados.
2. **Worker de PDF** ainda não materializa arquivo (`export_storage_key`); gate valida enfileiramento `queued` e UX de job.
3. **Indisponibilidade total** da API não foi injetada nesta rodada.
4. Storage local de evidência usa backend `memory` (adequado a local; piloto homologação deve usar S3 — ver variante em `009`).

## 6. Veredito

**APROVADO** — frontend MVP pronto para implantação em **homologação** e **piloto controlado**, com tag `mvp-fullstack-v0`.

Próximos passos sugeridos pós-tag:

1. Deploy homologação (API + web + Cognito real + S3)
2. Smoke Cognito + export worker
3. Piloto com dados reais de uma organização

## 7. Como reexecutar

```powershell
# API + Postgres já no ar (:8008, leaction_db:5433)
cd C:\Projetos\qmind\web
.\scripts\run-mvp-web-gate.ps1

# ou manualmente:
npm run build:gate
npx vite preview --host 127.0.0.1 --port 4178
# outro shell:
$env:QMIND_E2E_BASE_URL = "http://127.0.0.1:4178"
npx playwright test
```
