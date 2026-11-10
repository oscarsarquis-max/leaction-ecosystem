# ACTIONFINANCE_REV_ACESSO_LOJA_060

10/11/2026. O acesso da Loja de Pães foi reenviado para oscar@oscarsarquis.com.br. O login é o username **admin@actionhub.com.br**. Nada foi apagado nem desativado. Spider, Loja, Hub e os outros pools não foram alterados.

## Empresas

O cadastro da empresa não tem campo de CNPJ. As duas linhas abaixo são as empresas que existem no Finance.

| Empresa | CNPJ | Pay | Último ciclo (10/11/2026, horário de São Paulo) |
|---|---|---|---|
| Loja de Pães | não cadastrado | ativa, produção | 11:23, automática, vazia: 0 incluídos, 0 atualizados |
| Padaria de teste publico | não cadastrado | ativa, homologação | 11:23, automática, falhou: 0 incluídos, 0 atualizados. A Spider recusou o pedido |

A Loja de Pães não é demonstração. A padaria está marcada como demonstração, no tenant "ActionFinance teste publico", código `af-public-test-padaria`.

## Usuários

O pool do Finance tem um único usuário. O mesmo username está ligado às duas empresas, como operador (leitura e escrita). Os dois vínculos estão ativos.

| Username | E-mail | Empresa | Status no Cognito | Permissão |
|---|---|---|---|---|
| admin@actionhub.com.br | oscar@oscarsarquis.com.br | Loja de Pães | RESET_REQUIRED, conta ativa, e-mail verificado | Operador, leitura e escrita |
| admin@actionhub.com.br | oscar@oscarsarquis.com.br | Padaria de teste publico | RESET_REQUIRED, conta ativa, e-mail verificado | Operador, leitura e escrita |

Antes do reenvio o status era CONFIRMED.

## O que foi feito

O usuário com oscar@oscarsarquis.com.br já existia e já era operador da Loja de Pães. Não foi criado outro usuário e o e-mail não foi trocado. O Cognito recebeu `admin-reset-user-password` para esse username, para enviar o código de redefinição ao e-mail verificado.

Depois do pedido o status ficou RESET_REQUIRED. O CloudTrail registrou `AdminResetUserPassword` em 10/11/2026 11:45 (−03), sem erro, no pool do Finance.

No login, o identificador é **admin@actionhub.com.br**. O e-mail é só o contato para onde o código foi enviado.

## A empresa que falha no ciclo

É a Padaria de teste publico. Parece de teste: o nome e o tenant dizem teste, a empresa está marcada como demonstração e a integração Pay está em homologação. A Loja de Pães, em produção, concluiu o ciclo das 11:23 sem inclusão nem atualização. Nada foi mudado na padaria.
