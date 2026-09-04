# Evidências CURSOR-028-CMS

| Arquivo | Conteúdo |
|---------|----------|
| `entrar-remoto-*.png` | `/entrar` com editorial remoto (mock BFF) — 390/768/1024/desktop |
| `entrar-fallback-hub-down-desktop.png` | Login intacto com editorial estático (rede editorial abortada) |
| `panne-api-live-fallback.json` | `GET /login-editorial` ao vivo, Hub down → `source=static` |
| `key-selection.json` | Separação demo/prod + query ignorada |
| `hub-panne-*.json` / `panne-api-*.json` | Defaults / mapper (passagem anterior) |
| `ops/` | Auditoria operacional (tempos, PIDs, logs) |
| `frontend/scripts/capture-028-cms.mjs` | Script de captura controlada |

**Bloqueado nesta máquina:** screenshot do seletor CMS Hub (`panne` / `panne-demo`) — Docker Desktop indisponível (Postgres Hub).

**Não publicado.** Sem PII/credenciais.
