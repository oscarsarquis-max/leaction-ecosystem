# BLOG-016 — retorno

Data: 09/11/2026.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Capturas em 1280 e 390, com hover em 1280 | **Feito.** |
| 2 | O clique abre o LePain com a UTM, na mesma aba | **Feito.** |
| 3 | Teste novo, só o `infra-api-1` recriado, queda medida, Gestão e LePain em 200, SSH fechado | **Feito.** |
| 4 | Commit da Loja, push e merge no `main` | **Commit e push feitos. O merge no `main` não.** |

## O selo

Na coluna de texto do hero, 28 px abaixo do parágrafo. Pílula com o fundo creme, borda de 1 px no bordô a 35%, logo azul do LePain a 28 px, a palavra NOVO no estilo do rótulo e o texto com a seta. No hover a borda fica no bordô inteiro e a seta anda 3 px. Em 390 px o selo quebra em duas linhas e a página não ganha rolagem lateral. O clique dispara `lepain_hero_click` pelo `trackEvent` que a Loja já tinha.

Link: `https://lepain.lojadepaes.com.br/pt?utm_source=lojadepaes&utm_medium=hero&utm_campaign=lancamento-lepain`

Nome acessível: Conheça o LePain, o blog da Loja de Pães.

## Teste

`src/app/App.lepain.test.tsx` passou. O teste da vitrine também passou; a checagem das imagens passou a aceitar `lepain-logo`, senão o logo novo quebraria o teste que já existia.

## Produção

Imagem `lojadepaes:prod-20261109-blog016`. Recriado só o serviço `api` (`infra-api-1`), sem migração e sem mexer em Caddy, banco, Gestão ou LePain.

A homepage pública deixou de responder por 7,4 segundos e voltou em 200.

| Contêiner | StartedAt |
|---|---|
| infra-api-1 | 2026-11-09T14:13:21.298150492Z |
| infra-caddy-1 | 2026-11-08T20:34:12.590952489Z |
| gestao-api | 2026-11-07T15:12:10.777531884Z |
| infra-db-1 | 2026-09-20T18:14:08.677061212Z |
| lepain | 2026-11-09T13:30:29.506091996Z |

Loja, Gestão e LePain responderam 200. A porta 22 ficou fechada. 80 e 443 seguem abertas.

Capturas em `C:\Projetos\claude\2026-11-08-lepain-blog\evidencias\BLOG-016\`: `hero-1280.png`, `hero-1280-hover.png`, `hero-390.png`.

O clique medido chegou em `https://lepain.lojadepaes.com.br/pt?utm_source=lojadepaes&utm_medium=hero&utm_campaign=lancamento-lepain`, na mesma aba.

## Git

O código da Loja não está no `main`. No `main` a pasta `lojadepaes` só tem `infra`. O fonte está em `feat/actionfinance-extrato-032`, no commit `249541b4`. Por isso a branch `feat/blog-016-hero` sai desse commit, não do `main`. O commit é `a389319e`. A branch foi enviada. Não fiz o merge no `main`: ele traria a Loja inteira e o trabalho do ActionFinance que não é deste ciclo. O mesmo limite já estava no retorno do BLOG-009.
