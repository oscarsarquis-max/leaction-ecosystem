# Mapeamento: paneldx.com.br → mudaedu.com.br

> Trabalho **somente** em `C:\Projetos\mudaedu` (cópia do PanelDX).  
> O repositório original `PanelDX/` permanece **intocado**.  
> DNS `mudaedu.com.br` ainda em transição Registro.br → Route 53 — priorizar **local**.

## 1. O que já foi feito

| Item | Status |
|------|--------|
| Foco do ecossistema → `mudaedu` (demais travados) | OK |
| Cópia `PanelDX` → `mudaedu` (sem `venv` / `node_modules` / `.git`) | OK |
| PanelDX original | Intocado |

## 2. Camadas a alterar (resumo)

| Camada | Onde | Quando |
|--------|------|--------|
| **A. Config local** | `.env`, `.env.example`, `LeAction_SysF/.env*`, `LeAction_Sys_FE/.env*` | Agora (local) |
| **B. Defaults no código** | Fallbacks `https://paneldx.com.br`, e-mails `@paneldx.com.br` | Em `mudaedu/` |
| **C. Deploy scripts** | `scripts/deploy/_config.ps1` + seeds | Antes do 1º deploy mudaedu |
| **D. AWS** | Route 53, ACM, SES, ECS task env, ALB listener cert | Só após DNS estabilizar |
| **E. Integrações** | Action Hub webhooks / checkout URLs | Coordenar com Hub (projeto travado) |

---

## 3. Local — arquivos prioritários

### 3.1 Variáveis de ambiente (URL pública + e-mail)

| Arquivo | Chaves / trechos |
|---------|------------------|
| `mudaedu/.env` / `.env.example` | `MAIL_USERNAME`, `EMAIL_SENDER` (`@paneldx.com.br`) |
| `mudaedu/LeAction_SysF/.env` | `MAIL_*`, `EMAIL_SENDER`, `PANELDX_PUBLIC_URL` |
| `mudaedu/LeAction_SysF/.env.production.example` | `PANELDX_PUBLIC_URL`, `HUB_WEBHOOK_URL`, e-mails SES |
| `mudaedu/LeAction_Sys_FE/.env.production` | `BACKEND_URL=https://paneldx.com.br` |
| `mudaedu/LeAction_Sys_FE/.env.production.example` | `BACKEND_URL`, `HUB_WEBHOOK_URL` |

Sugestão local (sem depender do DNS público ainda):

```env
PANELDX_PUBLIC_URL=http://localhost:3000
# ou, quando DNS ok:
# PANELDX_PUBLIC_URL=https://mudaedu.com.br
BACKEND_URL=http://127.0.0.1:5002
```

> O nome da env `PANELDX_PUBLIC_URL` pode permanecer no curto prazo (só muda o valor) ou ser renomeado depois para `MUDAEDU_PUBLIC_URL` com alias de compatibilidade.

### 3.2 Fallbacks hardcoded (código)

| Arquivo | Uso |
|---------|-----|
| `LeAction_SysF/app.py` | CORS/`https://paneldx.com.br`; default SES `consultant@paneldx.com.br`; `_resolve_paneldx_public_url()` → `https://paneldx.com.br` |
| `LeAction_SysF/routes/consultor.py` | Fallback `PANELDX_PUBLIC_URL` |
| `LeAction_Sys_FE/views/sprint-atual.ejs` | URL fixa evidências `https://paneldx.com.br/projetos/...` |
| `LeAction_Sys_FE/views/sprintmod.ejs` | idem |
| `LeAction_Sys_FE/views/sprints.ejs` | idem |

### 3.3 Seeds / e-mails de demo `@paneldx.com.br`

| Arquivo | Contas |
|---------|--------|
| `seed_dev_client.py` | `sistema@`, `executor@` |
| `scripts/fix_consultor_paneldx.py`, `seed_consultores_demo.py` | `consultor@` |
| `scripts/seed_prod_lead_paneldx.py` + `scripts/deploy/09|12|13-*.ps1` | seeds prod |
| `LeAction_SysF/rbac/admin_users.py` | hint senha executor |
| `LeAction_SysF/integrations/esim/admin_routes.py` | allowlist e-mail |
| `LeAction_Sys_FE/views/admin-esim.ejs` + `public/js/admin-esim.js` | label disparo |

Decisão a tomar: trocar para `@mudaedu.com.br` **ou** manter e-mails legados só em seed até SES verificar o domínio novo.

### 3.4 Deploy (scripts) — ainda apontam paneldx

| Arquivo | Trecho |
|---------|--------|
| `scripts/deploy/_config.ps1` | `BACKEND_URL`, `HUB_WEBHOOK_URL` → `https://paneldx.com.br` |
| `scripts/test_hub_e2e.*` | `PANELDX_BASE=https://paneldx.com.br` |
| `scripts/deploy/10-seed-esim-catalog.ps1` | URL admin |

---

## 4. AWS — inventário atual (leitura)

| Recurso | Situação |
|---------|----------|
| Route 53 `paneldx.com.br` | Zona `Z06247363OOVXV80UUV3U` |
| Route 53 `mudaedu.com.br` | Zona **já existe** `Z0980883GCQKXMRD2S10` (DNS Registro.br ainda em transição) |
| ACM `us-east-2` | Cert **ISSUED** só para `paneldx.com.br` — falta cert `mudaedu.com.br` |
| SES | `paneldx.com.br` verificado; `mudaedu.com.br` **ainda não** |
| ECS | Cluster `paneldx-cluster` (produção atual do PanelDX) |

### Ordem na AWS (depois do DNS estabilizar)

1. Confirmar NS da zona `mudaedu.com.br` no Registro.br  
2. ACM: emitir cert `mudaedu.com.br` + `www`  
3. ALB: trocar/adicionar listener cert  
4. SES: verificar domínio + remetentes  
5. ECS task env → URLs/e-mails mudaedu  
6. Action Hub (travado): webhooks/retorno  
7. Opcional: redirect 301 `paneldx.com.br` → `mudaedu.com.br`

---

## 5. Plano de trabalho local (próximos passos)

1. Ajustar envs locais do `mudaedu` para URL localhost + (opcional) e-mails `@mudaedu.com.br` em DEV.  
2. Substituir fallbacks `https://paneldx.com.br` no código do **mudaedu** por env ou `https://mudaedu.com.br`.  
3. Subir `start-local.ps1` e validar login/CORS/e-mail em modo dev.  
4. **Não** mexer em ACM/Route53/SES/ECS até o usuário confirmar DNS propagado.  
5. Só então: cert + listener + env ECS + SES + smoke em `https://mudaedu.com.br`.

---

## 6. Fora de escopo nesta fase

- Qualquer commit ou edição em `PanelDX/`  
- Alterações no Action Hub / inove4us / outros projetos travados  
- Cutover DNS forçado enquanto Registro.br ainda transita
