# CURSOR-028-CMS — Gate Cortex (local, sem publicar)

**Status:** correção pontual de segurança + evidências locais. **Não publicar.**  
**Produção / DB `panne`:** intactos. Sem commit/push/deploy.

## Correções desta passagem (gate segurança)

| Item | Comportamento |
|------|----------------|
| HTTP público | Sem `mode` / `config_key` na query; params ignorados |
| `force_mode` | Só injeção em testes do service |
| URLs imagem | Path `/images|/assets|/static` **ou** HTTPS allowlist (S3/CF documentados) |
| URLs CTA | Relativos `/docs|/ajuda|…` (sem auth) **ou** HTTPS hosts LeAction; drop só do campo ruim |
| Cache | TTL + `max_stale` (default 600s); além → static; **memória por processo** (sem Redis) |
| Config key | Prod → sempre `panne` salvo flag admin `ALLOW_DEMO_KEY_IN_PROD` + override; browser nunca escolhe |
| FE | Segunda barreira em `sanitize.ts` (mesma política) |

## Testes / builds (reexecução)

| Suíte | Resultado |
|-------|-----------|
| Hub `cms-panne-keys.test.js` | 3 passed |
| Panne `test_login_editorial.py` | 13 passed |
| Panne FE `login-editorial.test.tsx` | 7 passed |
| Panne `npm run build` | ok |
| Hub `tsc --noEmit` (action-hub) | ok |

## Evidências

`documentacao/evidencias/cursor-028-cms/`:

- PNGs `/entrar` remoto: 390 / 768 / 1024 / desktop + fallback Hub-down desktop
- `panne-api-live-fallback.json` (API real, Hub off → `source=static`)
- `key-selection.json` (separação demo/prod)
- `ops/` — auditoria de tempos/PIDs

**Bloqueio:** Docker Desktop off → Hub admin (seletor `panne`/`panne-demo`) sem screenshot nesta máquina. Sem rebuild AWS/ECR.

## Publicação

**Nada publicado.** Sem commit/push.
