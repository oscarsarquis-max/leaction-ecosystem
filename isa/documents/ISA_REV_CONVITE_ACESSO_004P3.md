# ISA — convite de acesso 004P3

Data: 17/10/2026, 11:16 UTC.

## Resultado

O Amazon SES em `us-east-2` aceitou uma mensagem. Isso confirma o envio ao provedor, não a chegada à caixa de entrada. Não havia conjunto de configuração nem evento de entrega para consultar.

| Item | Valor |
| --- | --- |
| Identificador | `010f01a14993b248-047df88f-688e-4136-8c0c-2b9a1a777873-000000` |
| Para | evelineghg12@gmail.com |
| Cópia | oscar@oscarsarquis.com.br |
| Assunto | Seu acesso ao piloto da ISA Finanças Fáceis |
| Remetente | ISA Finanças Fáceis \<noreply@inove4us.com.br\> |
| Responder para | oscar@oscarsarquis.com.br |
| Destino da aplicação | https://isa.actionhub.com.br/ |
| Logo | `ActionFinance/ops/aws/cognito-hosted-ui/logo-hosted-ui.png`, incorporado por CID `finance-logo`, 280×142 sobre fundo `#1603ad` |
| Subtítulo | ISA Finanças Fáceis |

A senha temporária não foi gravada. O corpo enviado também não. O marcador abaixo ocupa o lugar dela no modelo.

## Estado conferido antes do envio

A usuária já existia, habilitada, em `FORCE_CHANGE_PASSWORD`. A posse do e-mail não foi marcada como verificada. Uma senha temporária nova, não permanente, foi definida na hora do envio. A política do pool `isa` confirma validade de 7 dias, com troca obrigatória no primeiro acesso.

A lista restrita já continha o acesso dela e o de Oscar. A task `isa-web:7` em execução tinha começado depois da última alteração dessa lista, na implantação `ecs-svc/9545503152528834259`, estado `COMPLETED`. Não houve nova implantação. O health público respondeu `isa-piloto 0.5.3`. A conta dela não foi aberta e permanece vazia.

O Finance continuou em `actionfinance-web:27`. O domínio `actionhub.com.br` não é identidade verificada no SES. O remetente usa `inove4us.com.br`, com DKIM válido e envio de produção habilitado. Não havia comprovante anterior para os mesmos destinatários.

Depois do aceite, os dois usuários continuavam em `FORCE_CHANGE_PASSWORD`, sem posse de e-mail marcada. A cópia não ativa o acesso de Oscar e não compartilha a conta da Eveline.

## Como repetir, sem duplicar

Não criar outra usuária e não redefinir senha se o estado já for `CONFIRMED`. Não reenviar se existir comprovante aceito para os mesmos destinatários e o mesmo assunto. Não republicar a ISA quando a task atual já tiver carregado a lista. Não imprimir a senha fora da mensagem autorizada.

## Modelo

Substituir `SENHA TEMPORÁRIA` somente na mensagem enviada. O texto simples repete a saudação, os três passos, o e-mail, a senha temporária, o prazo de 7 dias, o endereço, a conta vazia, o limite do piloto e a orientação para responder o e-mail.

```html
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#f4f3f8;font-family:Arial,Helvetica,sans-serif;color:#202039">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="580" cellpadding="0" cellspacing="0" style="width:100%;max-width:580px;background:#fff;border-radius:16px;overflow:hidden">
<tr><td align="center" style="background:#1603ad;padding:12px 24px 26px"><img src="cid:finance-logo" width="280" height="142" alt="Action Finance Capital" style="display:block;width:280px;max-width:100%;height:auto;border:0"><p style="margin:0;color:#fff;font-size:22px;line-height:1.3;font-weight:bold">ISA Finanças Fáceis</p></td></tr>
<tr><td style="padding:30px 28px 24px"><h1 style="font-size:24px;line-height:1.3;margin:0 0 16px">Olá, Eveline!</h1>
<p style="font-size:16px;line-height:1.65;margin:0 0 16px">Seu acesso ao piloto da ISA está preparado. A ideia é simples: ajudar você a organizar ganhos e gastos e enxergar se o dinheiro vai cobrir os próximos compromissos.</p>
<h2 style="font-size:18px;margin:24px 0 12px">Como entrar pela primeira vez</h2>
<ol style="padding-left:22px;font-size:16px;line-height:1.7;margin:0 0 20px"><li>Abra a ISA pelo botão abaixo e toque em <strong>Entrar</strong>.</li><li>Informe seu e-mail e a senha temporária deste convite.</li><li>Quando solicitado, escolha uma senha só sua.</li></ol>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f2effb;border-radius:10px"><tr><td style="padding:18px"><p style="margin:0 0 5px;font-size:13px;color:#5c5870">E-mail de acesso</p><p style="margin:0 0 16px;font-size:16px;word-break:break-all"><strong>evelineghg12@gmail.com</strong></p><p style="margin:0 0 5px;font-size:13px;color:#5c5870">Senha temporária</p><p style="margin:0;font-size:20px;font-family:Consolas,monospace;letter-spacing:1px;word-break:break-all"><strong>SENHA TEMPORÁRIA</strong></p><p style="margin:12px 0 0;font-size:13px;line-height:1.5;color:#5c5870">Válida por 7 dias. A troca é obrigatória no primeiro acesso. Não use esta senha em outros serviços.</p></td></tr></table>
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px 0"><tr><td style="background:#24219b;border-radius:9px"><a href="https://isa.actionhub.com.br/" style="display:inline-block;padding:15px 24px;color:#fff;text-decoration:none;font-size:16px;font-weight:bold">Acessar a ISA</a></td></tr></table>
<p style="font-size:13px;line-height:1.5;margin:0 0 24px;color:#5c5870">Se o botão não abrir, copie este endereço: <a href="https://isa.actionhub.com.br/" style="color:#24219b">https://isa.actionhub.com.br/</a></p>
<h2 style="font-size:18px;margin:0 0 10px">Comece no seu ritmo</h2><p style="font-size:16px;line-height:1.65;margin:0 0 16px">Sua conta começa vazia. Você pode registrar um ganho ou gasto, importar manualmente um extrato CSV do Banco do Brasil e informar o dinheiro disponível e os próximos compromissos para começar a planejar.</p>
<p style="font-size:14px;line-height:1.6;color:#5c5870;margin:0">Esta é uma versão piloto. Ela não movimenta dinheiro. Cartões, leitura de fotos e inteligência artificial ainda não fazem parte desta versão.</p>
<hr style="border:0;border-top:1px solid #eceaf2;margin:24px 0"><p style="font-size:13px;line-height:1.6;color:#5c5870;margin:0">Oscar recebe a mesma mensagem para acompanhar o piloto. A senha pessoal deve ser escolhida somente por você. Se precisar de ajuda, responda a este e-mail.</p>
</td></tr></table></td></tr></table></body></html>
```
