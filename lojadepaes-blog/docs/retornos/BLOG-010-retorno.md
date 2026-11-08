# BLOG-010 — retorno

Data: 08/11/2026.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Cherry-pick do `249541b4` no `main` e push | **Feito.** Hash `b45e4e00`. |
| 2 | `tsc`, testes, merge e push | **Feito, com uma ressalva.** O `tsc` passou. 89 de 90 testes passaram. O que falhou já vinha assim na produção. O merge `dedac001` está no `origin/main`. |
| 3 | Comparação de `sha256` e proposta do script | **Feito.** Nenhum arquivo de código diverge no conteúdo. A proposta está abaixo e não foi aplicada. |
| 4 | Regras de SSH do Hub | **Feito.** |
| 5 | Este retorno, commit e push | **Feito** neste commit. |

## 1. Commit da Loja

O cherry-pick de `249541b4` entrou no `main` como `b45e4e00` e foi enviado (`09509dfc..b45e4e00`). No `main` a pasta `lojadepaes/infra` não existia, então o cherry-pick criou `lojadepaes/infra/caddy/Caddyfile` (com `import /etc/caddy/sites/*.caddy`), `lojadepaes/infra/caddy/sites/.gitkeep` e `lojadepaes/infra/docker-compose.prod.yml` (monta `./caddy:/etc/caddy:ro`).

`feat/actionfinance-extrato-032` continua em `249541b4`. A branch não foi reescrita. Ela está 1 commit à frente da origem e não foi enviada.

## 2. Hub

`sync/producao-20261108` recebeu os arquivos de (a) e o `admin-api.ts` da produção (`revenue?: number` e os campos de cobrança). Os 28 de (b) ficaram como no `main`. `next-env.d.ts` está no `.gitignore` do frontend e não entrou no commit. O commit da branch é `91f6b5e8` (68 arquivos).

`npx tsc --noEmit` no frontend do Action Hub saiu 0. A única menção a `revenue` no `src` é o campo opcional. Nada mais foi ajustado.

Testes: 90 no total, 89 passaram, 1 falhou. Passaram checkout, créditos, assinatura, Spider Pay, a listagem admin, os do CMS e os três da Loja no frontend.

Falhou `services/gateway-api/domain/pay-regression.test.js`, no teste `sessão/plano continua em valor_negociado e não é confundida com checkout avulso`. Esperava `paidAmountAbsent === true` e recebeu `undefined`. `publicListItem` só define esse campo quando o pago está confirmado. O `spider-pay-lookup.test.js` da mesma cópia da produção espera o campo ausente, e esse teste passou. Os dois arquivos vieram da produção, não de uma mistura com o `main`. Por isso o merge seguiu.

Merge sem squash: `dedac001`. Pais: `48da913b` e `91f6b5e8`. Push: `48da913b..dedac001` em `origin/main`.

## 3. Comparação

O pacote foi montado na máquina local com a mesma lista do `deploy-remote.ps1` (`ecosystem.config.js`, `nginx.conf`, `docker-compose.yml`, `.env.production.example`, `.gitignore`, `scripts`, `services`, `shared`, `frontend`, `backend`), sem `node_modules`, sem `.next` e sem `services/analysis-engine`. O script não rodou e nada foi enviado.

No servidor ficaram de fora, como no 009: `node_modules`, `.next`, `.next.bak-*`, `dist`, `build`, `uploads`, `logs`, `.dev-logs`, `.venv`, `__pycache__`, `.pytest_cache`, `chaves`, `.env`, `.env.production`, `.env.local` e `*.pem`. Cinco pastas de build foram puladas.

| Conta | Arquivos |
|---|---|
| No pacote local | 409 |
| No servidor, com essas exclusões | 408 |
| Bytes iguais | 392 |
| Mesmo conteúdo, só a quebra de linha diferente | 14 |
| Conteúdo diferente | 0 |
| Só no pacote | 3 |
| Só no servidor | 2 |

Só no pacote, porque o `main` tem e a produção não. Um deploy os acrescentaria:

- `services/gateway-api/domain/cms-lepain-instagram-patch.test.js`
- `services/gateway-api/domain/cms-lepain-patch.test.js`
- `services/gateway-api/domain/cms-posts.test.js`

Só no servidor:

- `GIT_SHA` (marcador da produção, fora da lista que o script copia)
- `frontend/action-hub/next-env.d.ts` (gerado pelo Next e ignorado pelo git)

Os 14 em que só a quebra de linha difere (o pacote local está com CRLF, o servidor com LF):

- `backend/app/services/contextual_vitrine.py`
- `backend/app/services/mercadolivre_fallback.py`
- `frontend/action-hub/src/app/dashboard/cms/[id]/page.tsx`
- `frontend/action-hub/src/app/marketplace-api/offers/route.ts`
- `frontend/action-hub/src/app/marketplace-api/vitrine/route.ts`
- `frontend/action-hub/src/components/admin/CmsPostsList.tsx`
- `frontend/action-hub/src/lib/admin-api.ts`
- `scripts/deploy/bootstrap-school-db-remote.sh`
- `scripts/deploy/remote-db-init.sh`
- `scripts/deploy/remote-db-migrate.sh`
- `scripts/deploy/remote-install.sh`
- `scripts/deploy/remote-school-install.sh`
- `services/gateway-api/crm-funis.js`
- `services/gateway-api/crm-tracking.js`

### Proposta, não aplicada

O `deploy-remote.ps1` passaria a fazer isto, nesta ordem:

1. No começo, ler o IP público atual e abrir a porta 22 do Hub para esse `/32`.
2. Testar o SSH. Se falhar, parar e deixar a regra anterior no lugar.
3. Só então fechar a regra anterior da porta 22.
4. Testar o SSH de novo. Se falhar, repor a regra anterior.
5. Não apagar `/var/www/leaction-platform` antes do envio. Subir o zip numa pasta nova, em `/var/www/leaction-platform-releases/<data>`, e só trocar o caminho publicado por um symlink quando essa pasta estiver completa. A pasta que estava no ar permanece até a troca.

## 4. SSH do Hub

Antes: porta 22 aberta para a internet (`0.0.0.0/0`), uma regra. Portas 80 e 443 abertas para a internet, uma regra cada.

A regra do IP atual foi aberta primeiro. O SSH respondeu. A regra `0.0.0.0/0` da porta 22 foi fechada depois. O SSH respondeu de novo.

Depois: a porta 22 tem uma única regra, o IP público desta máquina. As portas 80 e 443 seguem abertas para a internet, como estavam.

Se o IP desta máquina mudar, a porta 22 deixa de aceitar a conexão até a regra ser atualizada para o IP novo.
