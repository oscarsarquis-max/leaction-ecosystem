# ACTIONFINANCE_REV_CABECALHO_NAVEGACAO_058A

10/11/2026. O ActionFinance 0.2.13 publica o cabeçalho com o CNPJ da empresa, a navegação nova e o login no Início. A leitura do mês fica para o 058B. Spider, Loja e Hub não foram alterados.

A cópia do prompt está em [ACTIONFINANCE_PROMPT_CABECALHO_NAVEGACAO_058A.md](../prompts/ACTIONFINANCE_PROMPT_CABECALHO_NAVEGACAO_058A.md). O desenho usado está em `documents/ux/desenho-001/`.

## SSH

Os security groups `actionfinance-svc` e `actionfinance-db` não têm regra na porta 22. O serviço roda em Fargate, sem SSH. Nenhuma regra foi aberta. A publicação usou a API da AWS.

## Cabeçalho e navegação

A faixa usa o token `--brand-mark` (`#1800AD`). O logo é `af-logo-azul.png`, com 40 px no desktop e 28 px até 767 px. À direita ficam o nome da empresa, a linha do CNPJ, o usuário e Sair. Com 14 dígitos a linha é `CNPJ 69.423.547/0001-04`. Sem número, a linha é `CNPJ não informado`. Quem tem mais de uma empresa continua podendo trocar; quem tem uma só vê o nome.

O menu é Início, Caixa, Vendas, Pagamentos, Bancos e Cadastros.

| Área | Submenu | Tela que já existia |
|---|---|---|
| Início | — | página simples, até o 058B |
| Caixa | Resumo, Agenda | resumo da tesouraria e agenda |
| Vendas | A receber, Recebimentos integrados | contas a receber e recebimentos do Pay |
| Pagamentos | A pagar | contas a pagar |
| Bancos | Contas, Extratos, Conciliação | contas, extrato e conciliação |
| Cadastros | como hoje | clientes e fornecedores, categorias, iniciativas e regras de rateio |

O login, a volta da sessão e a troca de empresa abrem `/`. O Início mostra o título "Início" e o texto "Em breve: a leitura do mês da sua loja." O `GET /api/v1/overview` não entrou nesta versão. O código ficou só na máquina, fora do commit e da imagem.

## CNPJ

A V27 só cria a coluna opcional `actionfinance.company.cnpj`, texto de 14 dígitos, sem máscara e sem número de cliente no script. O número `69423547000104` foi confirmado pelo Oscar. Ele já estava gravado na Loja de Pães antes desta migração, no mesmo dia, quando o 058 ainda não tinha fechado. O snapshot abaixo foi tirado depois dessa gravação e antes de o Flyway registrar a V27.

| Item | Valor |
|---|---|
| Versão | 0.2.13 |
| Snapshot | `actionfinance-pre-v27-20261110`, `available`, progresso 100, antes da task de migração |
| Migração | `actionfinance-migrate:9`, Flyway ligado só nessa task. Schema estava em 26. A coluna já existia, o script pulou o `ADD` e aplicou a checagem de 14 dígitos. "now at version v27" |
| Task de migração | parada de propósito depois da V27. Código de saída 143 |
| UPDATE | depois da V27, um único `UPDATE` no código `loja-de-paes`. Resultado `UPDATE 1`. A outra empresa autorizada continua sem CNPJ |
| Task web | `actionfinance-web:30`. Copiada da `:29`; só a imagem mudou |
| Flyway na web | `false` |
| Perfil | `production`. Sincronização de recebimentos ligada |
| Imagem na task | `sha256:16204a39c35bf23944fa14b8122ebc9db237467c5fef30140de1cc719acb4713` (linux/amd64) |
| Tag `0.2.13` no ECR | índice `sha256:954857b9b419f34bf175c5c2ebc17021cbb6d2c08361acff4ab45e6ebf33e003`. A task usa o digest amd64, não o índice |
| Rollout | `COMPLETED`, desired 1, running 1, em 2026-11-10T13:07:11-03 |
| Health | `GET /actuator/health` 200, `{"status":"UP","groups":["liveness","readiness"]}` |
| SPA | `index-CDdqg9PA.js`, `index-HBV6Ialw.css` |

Retorno da aplicação: `actionfinance-web:29`, versão 0.2.12, imagem `sha256:f194e9991b1d3196706ba7f98a5e6bbf17c766cea392dd2152fad378a5ae8553`. Reverter a task não remove a coluna da V27 nem o número já gravado.

## Testes

Não rodei a suíte inteira.

- `AppShell.test.tsx`: 9 testes, 0 falhas. Cobre a máscara, o texto "CNPJ não informado", o login parado no Início e o caminho de cada tela antiga pelo menu novo.
- `CompanyCnpjMigrationV27Test`: 1 teste, 0 falhas. O script da V27 só adiciona a coluna e não contém `INSERT` nem `UPDATE`.

## Capturas

Não havia sessão autenticada de produção, o mesmo limite do 054R1 e do 055. Não redefini senha para fabricar uma sessão. A prova pública é o pacote no ar: `index-CDdqg9PA.js` contém "Início", "Em breve: a leitura do mês da sua loja.", "CNPJ não informado" e "Recebimentos integrados"; a folha `index-HBV6Ialw.css` contém `#1800ad`; o logo `af-logo-azul-CLtv74jP.png` responde 200.

## Aceite

A 0.2.13 está no ar em `actionfinance-web:30`. O CNPJ da empresa entra no cabeçalho de todas as telas autenticadas, com máscara quando existe e com "CNPJ não informado" quando não existe. O menu novo alcança as telas que já existiam. O login abre no Início.
