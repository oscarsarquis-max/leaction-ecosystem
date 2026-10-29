# Adendo 95B — autorização compreensível e identidade da Loja (09/10/2026)

Correção de contratação e login. Sem refazer planos, sem Pay de pães, sem Agenda, sem cobrança, assinatura, cancelamento ou e-mail reais. Tentativa do proprietário não foi aberta nem alterada.

## Causa confirmada

Não foi falha do Mercado Pago. Também não faltava campo de cartão na captura cortada — o cartão só aparece depois de criar o checkout.

1. O título “Pedido da fornada” vinha do rótulo genérico da marca (`productLabel`) aplicado a qualquer checkout `lojadepaes`, inclusive Biblioteca.
2. No dashboard, pedido `PENDING` mostrava “Renovação automática mensal autorizada neste cartão” **antes** do brick ser enviado. O status “Aguardando autorização da recorrência” não dizia onde autorizar.
3. Textos de orientação citavam ActionHub (“Cancele no ActionHub”, identificação do contrato). O cliente se relaciona com a Loja.
4. A autorização da recorrência **não** é e-mail. É o formulário CardPayment do Mercado Pago no dashboard, depois de “Ir para autorizar a assinatura”. Código de acesso à conta é outra coisa.
5. O popover Identifique-se só oferecia “Receber código”. Sem campo de código e sem Entrar, o cliente era obrigado a pedir e-mail a cada acesso. CPF aceitava texto incompatível com documento.

“Preparando…” na etapa anterior: no 95B o clique em “Quero este plano” só navega para `/loja/contratar`. Em produção o CTA voltou a aparecer (não ficou preso). “Preparando o pagamento…” só depois do submit de e-mail, com timeout de 20s e recuperação sem cobrança. Não foi criado checkout para medir demora real do gateway.

## Onde o cliente autoriza

Não há e-mail de autorização. Não orientar a esperar a caixa de entrada.

| Etapa | O que acontece | Ação |
|---|---|---|
| Planos | R$ 19/mês e R$ 10 avulso | Escolher o plano |
| `/loja/contratar` (assinatura) | Consentimento + e-mail cadastrado. Ainda **não** autorizou | **Ir para autorizar a assinatura** |
| Dashboard + brick Mercado Pago | Formulário de cartão. Aqui ocorre o consentimento da recorrência (`POST /subscriptions/preapproval`) | Preencher e confirmar no brick |
| Após submit do brick | “Processando sua autorização” só enquanto processa | Esperar ou recuperar se falhar |
| Autorizada, 1º pagamento pendente | “Assinatura autorizada. Aguardando confirmação do primeiro pagamento.” | Direitos ainda **não** valem |
| Pago + direito vigente | Assinatura confirmada | 20 consultas / ciclo e 10% |

Retorno do navegador ou clique não concede crédito nem desconto. Pacote avulso não mostra autorização de recorrência.

## Onde gerencia a renovação

Na Loja de Pães, painel da conta (Identifique-se / situação), botão **Gerenciar assinatura** quando a assinatura é cancelável. Reusa `POST /api/v1/biblioteca/assinatura/cancelar`. Visitante sem conta não vê o botão — correto. Não há “Cancele no ActionHub”.

## Login do cliente

No mesmo painel: e-mail **ou** CPF (documento), campo **Código de acesso**, **Entrar** e **Receber código** separados.

- Abrir o painel, mudar campo ou clicar Entrar **não** envia e-mail (zero requests `identificar` na verificação).
- Código anterior ainda válido pode ser usado. Código é temporário (15 min) e se consome no uso — não virou senha permanente.
- Sessão da Loja continua 30 dias.
- Admin permanece no formulário próprio (Usuário / Senha), separado do código do comprador.

## Publicado

| Peça | Versão |
|---|---|
| Hub FE | BUILD_ID `CDuEURE9hD2FC62PJaE4U` (rollback de arquivos `p95b-20261009T121347Z`) |
| Backup Hub | `leaction_hub_20261009T121346Z` + `inove4us_school_20261009T121346Z` |
| Loja | `lojadepaes:prod-20261009c` (rollback `prod-20261009b`) |
| Bundle Loja | `/assets/index-Uh8gIpqm.js` + `index-B-OHCpeh.css` |
| Backup Loja | `/opt/lojadepaes/backups/lojadepaes-20261009T121733Z.sql.gz` |
| Alembic | `d7e0f5a24b38` — sem migração nova |
| Logo | `/brands/lojadepaes.png` 200 / 125797 bytes (95A preservado) |
| Gateway / Pay / Agenda / Spider | intocados |

## Jornada visual em produção (sem submit)

Chrome real, desktop 1440 e celular 390. Sem spinner permanente, sem crash UI, sem ActionHub no texto do cliente, sem “Pedido da fornada” na Biblioteca.

| Passo | Resultado |
|---|---|
| Home Loja → Identifique-se | E-mail, CPF, código, Entrar e Receber código visíveis. Admin à parte |
| `/loja` e URL com `return_origin` | Planos da Biblioteca · R$ 19,00/mês · R$ 10,00 avulso · logo oficial |
| Contratar mensal | “Sua assinatura da Biblioteca” · consentimento R$ 19 · “não enviamos e-mail para autorizar” · Mercado Pago citado · CTA utilizável |
| Contratar avulso | “Suas consultas de IA” · R$ 10 · sem autorização de recorrência · CTA do pacote |

Capturas: `captures/`. Relatórios: `verify-95b.json`, `check-assets.json`. A webfont cola letras na foto; o DOM tem espaços.

## Fronteira financeira — não comprovada no provedor

`GET /hub-api/config/payments`: `sandbox_mode=false`, `allow_payment_simulation=false`, credenciais `APP_USR`. Qualquer submit aqui cobra de verdade. Não há par `TEST-` nesta estação. Não foi criado checkout, tokenizado cartão, autorizada assinatura, reenviada cobrança nem lido o pedido do proprietário.

Estados de recusa / cancelamento da tentativa / falha técnica foram cobertos em teste isolado do copy e do login, não no percurso oficial do Mercado Pago.

## O que não foi feito

Cobrança, nova assinatura, cancelamento, concessão de direito, e-mail real, mutação da tentativa existente, Pay de pães, Agenda, catálogo de pães, planos comerciais.
