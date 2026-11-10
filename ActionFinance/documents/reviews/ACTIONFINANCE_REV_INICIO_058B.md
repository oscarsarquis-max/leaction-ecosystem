# ACTIONFINANCE_REV_INICIO_058B

10/11/2026. O Início do dono substitui a página provisória do 058A. Os números saem só da empresa da sessão. Ausência de fonte ou de dado aparece como "Não conectado" ou "Não apurado". Spider, Loja e Hub não foram alterados. Não houve mudança de banco.

A cópia do prompt está em [ACTIONFINANCE_PROMPT_INICIO_058B.md](../prompts/ACTIONFINANCE_PROMPT_INICIO_058B.md). O desenho continua em `documents/ux/desenho-001/`.

## SSH

Os security groups `actionfinance-svc` e `actionfinance-db` continuam sem regra na porta 22. O serviço roda em Fargate, sem SSH. Nenhuma regra foi aberta.

## O que a leitura entrega

`GET /api/v1/overview` exige a permissão de leitura de títulos e a empresa da sessão.

| Bloco | Origem | Quando não há base |
|---|---|---|
| Vendas | valor pago dos recebimentos integrados confirmados e reais, no período, por método | sem Pay autorizado: Não conectado; autorizado e sem linha: Não apurado |
| Taxas | tarifas das linhas ativas do extrato no período | sem extrato, ou extrato sem tarifa medida: Não apurado |
| Custos de produção | ainda sem fonte | Não conectado |
| Despesas | baixas de pagamentos não estornadas, por categoria | sem baixa: Não apurado |
| Sobrou | vendas menos taxas e despesas já apuradas | parcial, com a lista do que falta; só fica completo se as quatro partes estiverem apuradas |
| Caixa | posição das contas com saldo inicial, mais os títulos em aberto nas 8 semanas | sem conta: Não conectado; conta sem saldo inicial: Não apurado. A soma vazia não vira R$ 0,00 |
| Atenção | no máximo 5, nesta ordem: pagamento em até 2 dias, título vencido, extrato em revisão, lançamento sem conciliação, Pay parado há mais de 2 horas | cada item abre a tela que já existe |
| Horário | última sincronização concluída do Pay e último extrato confirmado | a frase não inventa "há 12 min" |

A menor semana do caixa fica marcada. Título vencido entra na primeira semana.

## Publicação 0.2.14

| Item | Valor |
|---|---|
| Versão | 0.2.14 |
| Banco | sem migração |
| Task web | `actionfinance-web:31`. Copiada da `:30`; só a imagem mudou |
| Flyway na web | `false` |
| Perfil | `production`. Sincronização de recebimentos ligada |
| Imagem na task | `sha256:8f97ee9ec8a9f871a2ab3ab46bc72f6c21ab25ea8af0c5f93c2af657a666d518` (linux/amd64) |
| Tag `0.2.14` no ECR | índice `sha256:5b0b485d36292b6e5961b86e5140efcada02cf9bee8782276c545542c81cf542`. A task usa o digest amd64, não o índice |
| Rollout | `COMPLETED`, desired 1, running 1, em 2026-11-10T14:38:33-03 |
| Health | `GET /actuator/health` 200, `{"status":"UP","groups":["liveness","readiness"]}` |
| SPA | `index-BizfEXnY.js`, `index-DMm-qFJp.css` |

Retorno da aplicação: `actionfinance-web:30`, a task do 058A, versão 0.2.13. Reverter a task não mexe no banco.

## Testes

Não rodei a suíte inteira.

- `OverviewServiceTest`: 8 testes, 0 falhas. Cobre cada bloco, ausência sem zero, Sobrou parcial e a ordem da atenção.
- `OverviewStoreIsolationTest`: 1 teste, 0 falhas. Cada consulta do overview filtra o tenant e a empresa da sessão.
- `HomePage.test.tsx`: 3 testes, 0 falhas. A segunda empresa da sessão não entra no pedido nem na tela; o item de atenção abre Pagamentos; Semana pede de novo só a empresa ativa.

O teste do menu, que ainda esperava o texto provisório "Em breve", foi alinhado à tela nova. Os 9 dele continuam passando.

## Capturas

Não havia sessão autenticada de produção, o mesmo limite do 054R1, do 055 e do 058A. Não redefini senha para fabricar uma sessão. A prova pública é o pacote no ar: `index-BizfEXnY.js` contém "Leitura do mês", "Não conectado", "Não apurado", "Pede sua atenção", "De onde veio o dinheiro", "Para onde foi" e "Caixa nas próximas 8 semanas".

## Diferenças em relação ao desenho

A estrutura é a do desenho: período, leitura, cinco números, oito semanas, atenção, origem, destino e a faixa da conta. O que muda é o dado, porque o desenho usa uma loja de exemplo.

- O cabeçalho permanece o do 058A: faixa `#1800AD`, CNPJ com máscara e logo de 28 px no celular. O desenho do celular usa 32 px e não mostra CNPJ.
- Custos de produção ficam "Não conectado". Por isso Sobrou é parcial e nomeia o que falta. Os R$ 2.140,00 e os 44% do desenho são números de exemplo, não um resultado fechado.
- "De onde veio" e "Para onde foi" listam os métodos e as categorias medidos. Não desenham Pix, crédito, ingredientes ou aluguel se essas linhas não existirem.
- A faixa da conta diz quantos lançamentos ativos estão conferidos e quantos faltam. Sem extrato, diz que ainda não foi apurado, em vez de "0 de 0".
- A atenção usa os fatos reais e leva à tela correspondente. Não cria o aviso de farinha nem o de taxa média do desenho quando o livro não tem esse fato.

## Aceite

O Início está no ar na 0.2.14. Os números são só da empresa da sessão. Fonte ausente ou sem dado não aparece como R$ 0,00.
