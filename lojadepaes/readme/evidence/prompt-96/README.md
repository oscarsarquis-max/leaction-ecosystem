# Prompt 96 — fechamento de período na Agenda

09/10/2026. Sem pedido, e-mail ou pagamento real. Pay, fidelidade, preço, catálogo e Hub/planos não foram alterados.

## Semântica

O período administrativo da viagem é **10–18/10/2026**. A primeira fornada elegível é **21/10/2026**. O bloqueio de novas datas vai até **20/10** inclusive. Recebimento de pedidos permanece aberto: o cliente pode encomendar agora para 21/10 em diante, se a rotina/capacidade permitir.

Não é pausa geral. 19 e 20/10 não voltam como retorno antecipado. Datas anteriores a 10/10 não mudam. Pedidos e solicitações já persistidos não são cancelados.

Aviso público: “Recebemos pedidos para as fornadas disponíveis a partir de 21 de outubro.” Motivo interno “Viagem” fica só no admin.

## Modelo

Tabela aditiva `schedule_closures` + `schedule_closure_events`. Não zera capacidade, não apaga dias semanais, não cria dezenas de exceções soltas.

Precedência no servidor: fechamento vigente ganha da rotina e de exceção que abra o dia. Reabrir um bloqueio remove só aquele intervalo. Clique duplo reusa o mesmo registro.

## Produção

| Item | Evidência |
|---|---|
| Imagem | `lojadepaes:prod-20261009a` (rollback de app: `prod-20261008g`) |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261009T111435Z.sql.gz` |
| Alembic | `d7e0f5a24b38` |
| Fechamento | `7fd19b92-ad98-4d91-9052-4c72348c3f9f` · programado · bloqueio até 20/10 · `pause_intake=false` |
| Autor | `admin:admin@lojadepaes.com.br` |
| Compromissos 10–20/10 | 0 pedidos, 0 solicitações abertas |

## Calendário público

Antes: 14/10 e 18/10 elegíveis; sem aviso de 21/10. `calendar-before.json`.

Depois: 10–20/10 `period_closed`; 21/10 `available`; aviso público presente; sem a palavra viagem. `calendar-after.json`.

Cotação (sem persistir pedido): 18/10 e 20/10 → 409 com o aviso de 21/10. 21/10 → 200 (a data passa; a composição específica pode seguir as regras de tipo).

Capturas: `captures/prod-home-calendar-1440.png` / `390` (antes), `prod-home-after-1440.png` / `390` e Fazedor depois. A webfont pode colar letras na foto; o DOM e a API têm o texto.

A Agenda administrativa não foi capturada com sessão: a prova do bloco e do histórico é a API autenticada no deploy (`created_by` real). Não há captura fingida do painel.

## Testes isolados

`test_prompt96.py` (8) + regressão `test_prompt87_date_request.py` + `test_schedule.py` = 24. Frontend Agenda/calendário: 16. 10, 18, 19 e 20 bloqueados; 21 aberto; envio durante a viagem para 21/10 permitido quando o recebimento não está pausado; reabertura não solta outro intervalo; clique duplo não duplica; data excepcional fora do fechamento segue o fluxo 87.

## Rollback

Voltar `LOJADEPAES_API_IMAGE=lojadepaes:prod-20261008g` e recreate. A tabela e o registro de fechamento **permanecem**; o app antigo **não aplica** o bloqueio. Não restaurar dump. Não apagar o histórico para “desfazer”.

## O que não foi feito

Pedido, e-mail ou cobrança reais. Sem captura autenticada da Agenda. Sem mudança no Pay, planos/Hub ou Spider.
