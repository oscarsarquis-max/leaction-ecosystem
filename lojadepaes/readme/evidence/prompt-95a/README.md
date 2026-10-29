# Adendo 95A — logo da Loja nas páginas de planos

09/10/2026. Só frontend do Hub. Sem contratação, cobrança ou e-mail.

## Causa

O branding já apontava para `/brands/lojadepaes.png`. O arquivo oficial existia no repositório do Hub (`public/brands/lojadepaes.png`, SHA idêntico a `lojadepaes/frontend/images/lojadepaeslogo.png`, 125797 bytes) e **não estava no servidor**. Produção devolvia 404 HTML do Next. Não era falha de recorte nem de branding.

## Correção

O PNG oficial foi incluído no `public/brands/` publicado. O cabeçalho deixou o fundo preto (inadequado ao canvas branco da marca) e passou a usar `brand.logo`. O recorte é o mesmo da Loja, em escala do header de 40 px.

## Produção

| Item | Evidência |
|---|---|
| BUILD_ID | `RcbKeSmRZ78ehM6EjRi82` |
| Backup Hub | `leaction_hub_20261009T112552Z` + arquivos `p95a-20261009T112553Z` |
| Logo | https://actionhub.com.br/brands/lojadepaes.png → 200, `image/png`, 125797 bytes |
| Loja | sem republicação |

## Verificação

`/loja` nu, URL com `return_origin`/`return_to`, `/loja/contratar` mensal e avulso, desktop 1440 e celular 390. Imagem `complete`, 2000×2000 naturais. Cartões R$ 19/mês e R$ 10 avulso intactos. Sem submit.

Capturas em `captures/`. Relatório `verify-logo.json`.

Mercado Pago oficial continua não exercitado. Este ajuste não prova integração financeira.

## Rollback

Copiar de volta os arquivos em `/var/lib/leaction-platform/backups/p95a-20261009T112553Z` e rebuild do Hub FE. BUILD_ID anterior: `ODrRI9FZL2AwRMNrQtqEx`.
