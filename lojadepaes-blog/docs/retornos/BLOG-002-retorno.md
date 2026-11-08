# BLOG-002 — Retorno

Data: 08/11/2026. Só local. Nada foi publicado, e nada mudou na Loja, na Gestão, no ActionHub, no Caddy, no DNS ou nos bancos.

O esqueleto está em `C:\Projetos\lojadepaes-blog`, branch `feat/blog-002-esqueleto`, nascida de `origin/main` (`49b2a839`) no worktree `C:\Projetos\_blog-002`. O checkout principal continua na branch em que já estava.

Para abrir: `pip install -r requirements.txt` e `uvicorn app.main:app --host 127.0.0.1 --port 8091`. A raiz manda para `/pt` ou `/en` pelo `Accept-Language`. O padrão de dados é `LEPAIN_CMS_SOURCE=fixtures`.

## Checklist

| Item | Estado | Evidência |
|---|---|---|
| 1. Testes novos | Feito | `pytest tests` — 5 passed |
| 2. Capturas 1280 e 390 | Feito | `docs/evidence/blog-002/` — Home PT, Insight PT, Insight EN, Right Now EN, filtro Som |
| 3. PNG do card | Feito | `card-pt.png` e `card-en.png`, 1080×1350 |
| 4. Head do Insight | Feito | trecho abaixo, de `/pt/insights/a-casca-que-canta` |
| 5. Commit e push | Feito | neste ciclo, com o retorno e as capturas |

## O que a página entrega

FastAPI e Jinja2, HTML no servidor. O único JavaScript é o botão "Baixar PNG" / "Download PNG", que espera `document.fonts.ready`, desenha o cartaz num canvas e salva `lepain-{slug}-{idioma}.png`.

Cores, raios assimétricos, chips e os desenhos (pão, ondas, miolo) seguem o canvas. Logos em `app/static/img`. Fontes woff2 locais, licença OFL em `app/static/fonts`: Fraunces com eixos SOFT, WONK, opsz e wght; Literata; Caveat Brush; Syne.

`GET /api/v1/health` responde `{"ok": true, "service": "lepain"}`.

Fixtures no modelo novo: três Insights em PT e EN (a casca, a focaccia, o sovado), um só em PT (o silêncio da massa) e três itens do Right Now (promoção, evento, notícia) nos dois idiomas. O que o canvas não tinha texto ficou `[PLACEHOLDER]`. Há também uma fornada com `valido_ate` em 2020, que não aparece na lista.

`/en/insights/o-silencio-da-massa-descansando` mostra o texto em português e o aviso "English version coming soon". O seletor de um post com as duas versões aponta para o slug irmão.

O Right Now esconde o item vencido. O filtro `?sentido=som` é um link, resolvido no servidor. Em 390 px o cabeçalho fica logo, PT·EN e menu; a navegação abre sem JavaScript. Sem rolagem lateral nas capturas.

O `nh3` aceita as marcas pedidas. O `iframe` só permanece se o endereço for embed do YouTube ou do Vimeo. `<script>` sai.

No modo `hub`, a leitura é `GET https://api.actionhub.com.br/api/cms/posts?sistema_destino=lepain&limit=100`. Linha com destino `todos` é descartada. A lista fica 5 minutos em memória; se o Hub falhar, fica a última cópia boa. Os campos que o Hub ainda não tem (seção, idioma, sentidos) só entram quando a migração existir. Até lá o modo útil é `fixtures`.

## Head do Insight

A página começa com `<html lang="pt-BR">`. No `<head>`:

```html
<link rel="canonical" href="https://lepain.lojadepaes.com.br/pt/insights/a-casca-que-canta">
<link rel="alternate" hreflang="pt" href="https://lepain.lojadepaes.com.br/pt/insights/a-casca-que-canta">
<link rel="alternate" hreflang="en" href="https://lepain.lojadepaes.com.br/en/insights/the-crust-that-sings">
<link rel="alternate" hreflang="x-default" href="https://lepain.lojadepaes.com.br/pt/insights/a-casca-que-canta">
<meta property="og:title" content="A casca que canta — LePain">
<meta property="og:locale" content="pt_BR">
<meta property="og:image" content="https://lepain.lojadepaes.com.br/static/img/lepain-logo.png">
```

A capa desta fixture está vazia, então a imagem do Open Graph é o logo. `sitemap.xml` lista as alternâncias e o `lastmod`. `robots.txt` libera o site. O card manda `noindex`.

## Comandos executados

Testes, o servidor em `127.0.0.1:8091` para as capturas, e o push desta branch. Nenhum deploy, nenhum SQL, nenhum reload de Caddy.
