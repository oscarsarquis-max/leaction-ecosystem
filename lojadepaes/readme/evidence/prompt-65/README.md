# Prompt 65 — Navegação e página principal

## Inventário

| Superfície | Rota | Layout | Retorno |
|---|---|---|---|
| Home | `/` | `StorefrontLayout` | «Página principal» no menu, item atual |
| Receita | `/receitas/{slug}` | `StorefrontLayout` | faixa «Página principal»; «Voltar à vitrine»/resultados no fim |
| Acervo | `/receitas` | `StorefrontLayout` | faixa |
| Produto | `/paes/{slug}` | `StorefrontLayout` | faixa |
| Revisão | `/pedido/novo` | `StorefrontLayout` | faixa |
| Acompanhamento | `/pedido/{ref}` | `StorefrontLayout` | faixa |
| Ativação | `/ativar/{token}` | página própria | faixa nativa |
| Gestão | `/admin/*` | `AdminApp` | faixa nativa; «Voltar à lista» nos editores |
| Login antigo | `/admin/login` | redireciona à home `#acesso` | — |
| Receita inexistente | `/receitas/…` | `StorefrontLayout` | faixa |
| URL desconhecida | qualquer outra | home | item atual do menu |

Causa do menu na receita: os itens apontavam para `#paes` nesta URL. As âncoras existem só na home. Nas páginas de pão isso já virava `/#paes`.

## Isolado

Jornada em `test_prompt65_browser.py` (Playwright, SPA construída). Sem pedido, e-mail ou receita real.

- Home → receita → cada item do menu: seção visível (`#paes`, `#criacao`, `#mural`, `#biblioteca`).
- Acesso direto à receita → «Página principal» e logo → home.
- Menu móvel em 768/390/320; teclado; voltar/avançar.
- Carrinho com fixture permanece com 2 itens após navegar.
- Gigio não cobre a faixa de retorno.
- Produto, acervo, revisão, receita 404, ativação e gestão: faixa com `href="/"`.
- Editor com texto não salvo: cancelar «Voltar à lista» e o aviso ao sair conservam o título.

Capturas: `recipe-1440.png`, `recipe-768.png`, `recipe-390.png`, `recipe-320.png`. Relato: `isolated.json`.

## Produção

Imagem `lojadepaes:prod-20261001j`, bundle `/assets/index-jFJV6_6c.js`. Rollback `prod-20261001i`. Alembic `c8e2f1a90b64` inalterado. Sem migrate, seed, cobrança ou gravação de receita real.

Sessão nova em `https://lojadepaes.com.br/receitas/sardinhas-e-homus-de-grao-de-bico-fresco-tartine-bread`:

- Menu: `/#paes`, `/#criacao`, `/#mural`, `/#biblioteca`
- «Página principal» → `/`; clique leva à home
- «Nossos pães» deixa `#paes` visível
- 390 px: faixa visível sem abrir o menu; «Crie seu pão» abre `#criacao`

Capturas: `prod-recipe-1440.png`, `prod-home-390.png`. Relato: `prod.json`.

O bundle inclui a correção do Prompt 64 (rascunho salva; publicação bloqueada sem alt não diz «Erro ao salvar»).
