# CURSOR-028-CMS — mapa de arquivos

## Action Hub (`leaction-platform`)

| Arquivo | Mudança |
|---------|---------|
| `services/gateway-api/domain/cms-site-config.js` | Allowlist `panne-demo`, `panne` |
| `services/gateway-api/domain/cms-landing.js` | Defaults Panne + `defaultsForConfigKey` |
| `services/gateway-api/domain/cms-panne-keys.test.js` | Testes de keys/defaults |
| `frontend/action-hub/src/lib/admin-api.ts` | Tipo `CmsSiteConfigKey` |
| `frontend/action-hub/src/components/admin/CmsSiteForm.tsx` | Opções admin + títulos |
| `scripts/promote-cms-site.js` | Allowlist |
| `scripts/apply-cms-site-json.js` | Allowlist |
| `scripts/promote-cms-site.ps1` | ValidateSet |

## Panne

| Arquivo | Mudança |
|---------|---------|
| `backend/app/config.py` | Settings Hub editorial |
| `backend/.env.example` / raiz `.env.example` | Vars documentadas |
| `backend/app/modules/login_editorial/content.py` | Static + sanitize |
| `backend/app/modules/login_editorial/mapper.py` | Hub → Panne |
| `backend/app/modules/login_editorial/hub_client.py` | S2S GET |
| `backend/app/modules/login_editorial/cache.py` | TTL + stale |
| `backend/app/modules/login_editorial/config_key.py` | Seleção de key |
| `backend/app/modules/login_editorial/service.py` | Orquestração |
| `backend/app/modules/login_editorial/http.py` | Rota pública **sem** query `mode`/`config_key` |
| `backend/app/modules/login_editorial/url_policy.py` | Allowlist positiva imagem/CTA |
| `backend/tests/test_login_editorial.py` | Segurança + cache ages (13) |
| `frontend/src/editorial/apiProvider.ts` | Consome API Panne |
| `frontend/src/editorial/schema.ts` | source hub/cache |
| `frontend/src/editorial/sanitize.ts` | Segunda barreira allowlist |
| `frontend/src/editorial/provider.ts` | Nota atualizada |
| `frontend/scripts/capture-028-cms.mjs` | Evidências /entrar |
| `frontend/src/pages/LoginPage.tsx` | ApiLoginEditorialProvider |
| `frontend/src/test/fetchMock.ts` | Mock login-editorial |
| `documentacao/produto/GATE-CORTEX-028-CMS.md` | Gate |
| `documentacao/evidencias/cursor-028-cms/*` | Payloads + PNGs + ops |

## Não alterado

- Banco `panne`
- Conteúdo ativo Inove4us / School / PanelDX
- Publicação / deploy / commit / push
