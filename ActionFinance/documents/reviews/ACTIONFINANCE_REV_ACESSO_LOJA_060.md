# ACTIONFINANCE_REV_ACESSO_LOJA_060

10/11/2026. O gestor da Loja de Pães entra com o username **gestor@lojadepaes.com.br**. O convite, com senha temporária, foi para **oscar@oscarsarquis.com.br**. O administrador do Finance continua sendo admin@actionhub.com.br. Nada foi apagado nem desativado. Spider, Loja, Hub e os outros pools não foram alterados.

## Empresas

O cadastro da empresa não tem campo de CNPJ. As duas linhas abaixo são as empresas que existem no Finance.

| Empresa | CNPJ | Pay | Último ciclo (10/11/2026, horário de São Paulo) |
|---|---|---|---|
| Loja de Pães | não cadastrado | ativa, produção | 11:23, automática, vazia: 0 incluídos, 0 atualizados |
| Padaria de teste publico | não cadastrado | ativa, homologação | 11:23, automática, falhou: 0 incluídos, 0 atualizados. A Spider recusou o pedido |

A Loja de Pães não é demonstração. A padaria está marcada como demonstração, no tenant "ActionFinance teste publico", código `af-public-test-padaria`.

## Usuários

| Username | E-mail | Empresa | Status no Cognito | Permissão |
|---|---|---|---|---|
| gestor@lojadepaes.com.br | oscar@oscarsarquis.com.br | Loja de Pães | FORCE_CHANGE_PASSWORD, conta ativa, e-mail verificado | Operador, leitura e escrita |
| admin@actionhub.com.br | oscar@oscarsarquis.com.br | Loja de Pães | RESET_REQUIRED, conta ativa, e-mail verificado | Operador, leitura e escrita |
| admin@actionhub.com.br | oscar@oscarsarquis.com.br | Padaria de teste publico | RESET_REQUIRED, conta ativa, e-mail verificado | Operador, leitura e escrita |

## O que foi feito

O primeiro envio foi para o administrador, admin@actionhub.com.br. O Cognito mandou um código de redefinição, e a tela de entrada só pede usuário e senha. Por isso o código não entrou. Esse username permanece ativo, agora em RESET_REQUIRED. O e-mail dele não foi alterado.

Em seguida foi criado o gestor da loja. O username é gestor@lojadepaes.com.br e o e-mail de contato, verificado, é oscar@oscarsarquis.com.br. O Cognito enviou o convite com senha temporária para esse e-mail. O CloudTrail registrou `AdminCreateUser` em 10/11/2026 12:06 (−03), sem erro, com entrega por e-mail. O status ficou FORCE_CHANGE_PASSWORD. No Finance, o vínculo novo é operador da Loja de Pães, com leitura e escrita. A padaria de teste não foi ligada a esse usuário.

No login da loja, o identificador é **gestor@lojadepaes.com.br**. A senha temporária vai no campo Password. O Cognito pede em seguida uma senha nova.

## A empresa que falha no ciclo

É a Padaria de teste publico. Parece de teste: o nome e o tenant dizem teste, a empresa está marcada como demonstração e a integração Pay está em homologação. A Loja de Pães, em produção, concluiu o ciclo das 11:23 sem inclusão nem atualização. Nada foi mudado na padaria.
