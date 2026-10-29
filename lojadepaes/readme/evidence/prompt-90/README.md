# GIGIO_REV_LIMITES_CONTEXTO_001

08/10/2026. Prompt 90. Sem pedido, e-mail ou pagamento real. Sem aceite integral do proprietário.

## Produção

| Peça | Valor |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261008c` (rollback: `prod-20261008b`) |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261008T130009Z.sql.gz` |
| Regras | `90` |
| Bundle | `/assets/index-DGjt2ALe.js` (só backend mudou) |

## Causa

O fallback `_contextual_lookup` e o anexo de CTA usavam o histórico inteiro e a resposta do modelo. Depois de um hambúrguer, «Onde compro um Fusca?» ainda herdava a mesa. O modelo mencionar o hambúrguer ao oferecer retorno reforçava o mesmo critério. Esconder o botão só no frontend não bastava.

## Regra aplicada

A mensagem atual decide se há `lookup_accompaniments`, CTA de vitrine, `propose_builder` ou **Montar esse pão**. O histórico só continua uma refeição real («Prefiro queijo, sem vinho», «E para beber?», «Voltando ao hambúrguer…»). Validação no backend, no caminho com ferramenta e no fallback sem ferramenta. Resposta do modelo sozinha não cria botão. Prompt 88 (sem `<invoke>` no chat) permanece.

## Prova pública Fusca

1. https://lojadepaes.com.br/ → **Conversar com Gigio**
2. «queremos fazer um hambúrguer… que sugestão de acompanhamento…»
3. Aparece **Ver acompanhamentos sugeridos** (hambúrguer, batatas e cervejas).
4. «Onde compro um Fusca?»
5. A resposta orienta canais de carro, explica a especialidade e oferece retomar. **Nenhum CTA novo** nessa mensagem. O botão do hambúrguer fica na mensagem anterior.

API ao vivo: `first_cta=Ver acompanhamentos sugeridos`; `fusca_cta=null`; `thanks_cta=null`. Capturas: `readme/evidence/prompt-90/prod/`.

## Testes

- Novos 90 + regressão 77/85/86/87/88/data/Gigio: **80 passed**
- Frontend GigioHost + BreadBuilder: **14 passed**
- Dica do Criador (89) no site: composição Branca + fermentação natural curta + Nozes + Pão de forma ainda responde.

## Rollback

`LOJADEPAES_API_IMAGE=lojadepaes:prod-20261008b` e recreate da API.
