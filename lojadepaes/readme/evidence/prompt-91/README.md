# Prompt 91 + Adendo 91A — evidência

Publicado em 08/10/2026. Imagem `lojadepaes:prod-20261008d`. Backup `20261008T135317Z`. Regras `91`.

Artigos e calculadora são a entrega pública. O plano único R$ 19,00/mês vive no ActionHub.

## O que ficou ativo na Loja

- Home `#biblioteca` com três cadernos em rotas próprias
- `/biblioteca/o-comeco`, `/biblioteca/as-maos-na-massa`, `/biblioteca/a-mesa`
- `/biblioteca/calculadora` (F=1000 H=70 sal=2 PFF=20 L=100 → 1720 g)
- Painel “Aprofundar com o Gigio” consulta o Hub; sem plano publicado não há checkout

## O que depende do Hub

- Publicar `LOJADEPAES_BIBLIOTECA_MENSAL` no editor (`scripts/p91-hub-plan-sandbox.md`)
- Assinatura, renovação, cancelamento e entitlement no sandbox do Hub
- Franquia de consultas e excedente: não definidos; só medição técnica (`gigio_usage_events`)

## Fontes dos artigos

- Hamelman, *Bread* (2012) — porcentagem de padeiro
- Calvel, *The Taste of Bread* (2001) — fermentação e ponto
- Embrapa Alice `cbcta170.pdf` — processo de pão de forma integral
- Anvisa / gov.br — alimentos e mofo

## Rollback

Imagem anterior de app (Prompt 90). Alembic `a4b7c2d91e05` só adiciona medição e cache; downgrade remove essas tabelas sem tocar pedidos.
