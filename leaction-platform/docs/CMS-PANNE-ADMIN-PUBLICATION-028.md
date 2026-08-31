# Action Hub — publicação admin CMS Panne (CURSOR-028)

Registro operacional da publicação do frontend administrativo do Micro-CMS
com keys `panne-demo` / `panne`, após o gateway já aceitar essas keys em produção.

## Código funcional

Já em `main` via commit `4dcc5cb` (`feat(action-hub): add Panne editorial CMS keys`):

- allowlist gateway: `default` | `inove4us` | `inove4us-school` | `panne-demo` | `panne`
- defaults editoriais Panne em `cms-landing.js`
- seletor no admin (`CmsSiteForm`): PanelDX, inove4us, School, **Panne — Demonstração**, **Panne — Produção**
- scripts `promote-cms-site` / `apply-cms-site-json` alinhados às keys

Não há commit funcional adicional nesta passagem.

## Publicação do frontend admin (fora da EC2)

### Contexto ENOSPC

A EC2 do Action Hub (`/` ~6.7G) esgotou disco durante `next build` remoto.
Não foi feita limpeza ampla (sem apagar imagens Docker, volumes ou releases alheios).
Mitigação: build **local** do `frontend/action-hub` e envio apenas do artefato `.next`.

### Versão publicada

| Campo | Valor |
|-------|--------|
| Editor | https://actionhub.com.br/dashboard/cms/site |
| `VERSION` (stamp de publish) | `4dcc5cb+3bbe9f0-cms-fe` |
| `GIT_SHA` de referência | `3bbe9f0` (ancestral inclui `4dcc5cb`) |
| `BUILD_ID` (Next) | `FHvqQY066waZoBksrscsw` |
| Processo | `pm2 restart action-hub` apenas (gateway já saudável) |

### Rollback desta publicação

- Cópia do `.next` publicado: `/var/lib/leaction-platform/fe-published-028-cms`
- Backup de source pré-publish: `/var/lib/leaction-platform/fe-source-backup-pre-028-cms-publish`
- O `.next` anterior em memória (inode deletado pós-ENOSPC) **não** era recuperável; por isso a cópia `fe-published-028-cms` é o ponto de rollback desta release de FE.

### Prova do seletor (bundle estático)

No `.next/static` publicado constam as labels:

- `PanelDX (default)`
- `inove4us` / `inove4us School`
- `Panne — Demonstração`
- `Panne — Produção`

Keys públicas: `default`, `inove4us`, `inove4us-school`, `panne-demo` → HTTP 200.

## Homologação editorial reversível (`panne-demo` apenas)

Escopo: key `panne-demo`. **Não** ativar produção Panne; key `panne` permaneceu preparatória e inalterada no conteúdo.

Fluxo executado:

1. Registrar baseline completo da key (Postgres + snapshot S3 `cms/site/panne-demo.json`).
2. Alteração temporária: título coluna esquerda, texto coluna direita, imagem no bucket CMS S3, visibilidade explícita.
3. Publish via `apply-cms-site-json.js` (Postgres + S3 site JSON).
4. Após TTL do consumidor Panne Demo (~30s): `source=hub`, textos/imagem refletidos em `/api/v1/public/login-editorial`; `/entrar` 200 (desktop/mobile); formulário de login não afetado.
5. Teste controlado: `pm2 stop gateway-api` breve → editorial Demo `source=cache` → gateway restabelecido (health 200).
6. Restaurar baseline byte-a-byte na key `panne-demo`; confirmar retorno na Demo (`source=hub`, títulos originais, sem imagem de homolog).

Mídia: objeto no bucket central `paneldx-cms-assets-2026` (prefixo `cms/`), não persistência só em disco EC2. Ver também [CMS-SITE-S3-PERSISTENCE.md](./CMS-SITE-S3-PERSISTENCE.md).

## Fora de escopo / não versionar

Artefatos de build (`.next`, `node_modules`, tarballs), logs, backups brutos da EC2, JSON de conteúdo editorial, imagens de homologação (já no S3), credenciais, e qualquer mudança Panne API/FE/DB ou outros produtos.
