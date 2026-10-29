# Adendo 96B — clareza no formulário “Precisa de outra data?”

09/10/2026. Sem envio, e-mail, pedido ou pagamento.

## Causa do 2

O campo “Quantidade pretendida” nascia com `useState("2")` em `DateRequestForm.tsx`. Não havia mínimo de dois no servidor (`intended_quantity` já aceitava 1). O 2 era só inicialização do formulário novo.

## Correção

- Formulário novo começa vazio, com placeholder “Informe quantos pães”.
- Validação no frontend e no servidor: inteiro ≥ 1; vazio/0/negativo/fracionário não viram 1 nem 2. Mensagem: “Informe a quantidade de pães: 1 ou mais.”
- Orientação permanente: “Sugira uma data. A Loja avalia a possibilidade e responde por e-mail. Esta solicitação ainda não confirma a fornada.”
- Aviso de fechamento reutilizado da Agenda (`public_closure_notice`). Não se repete se já está imediatamente acima do formulário. Nenhuma data da viagem foi fixada no código.
- Disposição, cores, campos e jornada intactos. Fechamento da Agenda não foi reconfigurado.

## Produção

| Item | Evidência |
|---|---|
| Imagem | `lojadepaes:prod-20261009b` |
| Rollback | `lojadepaes:prod-20261009a` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261009T114916Z.sql.gz` |
| Alembic | `d7e0f5a24b38` (sem migration nova) |
| Fechamento | intacto; aviso público: “Recebemos pedidos para as fornadas disponíveis a partir de 21 de outubro.” |

## Verificação

**Isolada:** `test_prompt96b.py` + `test_prompt96.py` + `test_prompt87.py` + `test_prompt87_date_request.py` = 24 passed. Frontend DateRequestForm/BakeCalendar = 14 passed. Browser isolado: quantidade vazia, placeholder, texto novo, aviso da Agenda uma vez, 1440/390/320 sem overflow. Quantidade 1 persiste na solicitação e no atendimento, sem duplicar.

**Produção (leitura, sem submit):** `verify-form.json`. Campo vazio, placeholder correto, texto novo, sem “inclusive para hoje”, aviso da Agenda visível, 1440/390/320 sem corte horizontal.

Capturas em `captures/` (`isolated-form-*`, `prod-form-*`, `prod-form-card-*`). A colagem de webfont nas imagens é o mesmo artefato de captura já visto; o DOM e o JSON confirmam os textos.
