# ACTIONFINANCE_REV_CORRIGE_OVERVIEW_064

10/11/2026. O Início da Loja de Pães falhava porque o `GET /api/v1/overview` quebrava inteiro. A correção ficou no backend do overview. Spider, Loja e Hub não foram alterados. Não houve mudança de banco. A tela não foi alterada.

A cópia do prompt está em [ACTIONFINANCE_PROMPT_CORRIGE_OVERVIEW_064.md](../prompts/ACTIONFINANCE_PROMPT_CORRIGE_OVERVIEW_064.md).

## SSH

Os security groups `actionfinance-svc` e `actionfinance-db` continuam sem regra na porta 22. O serviço roda em Fargate, sem SSH. Nenhuma regra foi aberta.

## Causa

Entre 18:00 e 18:10 UTC, o log do serviço web registrou a mesma falha às 18:03:49 e às 18:04:59. A requisição não terminou: `NullPointerException` em `JdbcOverviewStore.load`, na leitura de `max(confirmed_at)` do lote de extrato confirmado.

Essa consulta devolve uma linha com valor nulo quando não há lote confirmado. A lista com um elemento nulo passava por `findFirst()`, que não aceita nulo. A sincronização dos recebimentos tinha horário, por isso a consulta anterior não quebrou. O extrato sem linhas é o que deixou o máximo nulo. A conta sem saldo inicial não foi a causa: esse caso já respondia "Não apurado" e a exceção aconteceu antes. Não foi permissão nem período inválido.

A frase da tela é a mensagem genérica do cliente quando a resposta não vem completa.

## Correção

Um máximo nulo passa a ser ausência de horário, não uma queda. Cada fonte do overview fica isolada: se a consulta falha, o log registra só o nome do bloco e a classe da exceção, sem dado pessoal, e aquele bloco volta como não apurado. Os demais respondem.

## Testes

Não rodei a suíte inteira. `OverviewServiceTest` e `OverviewStoreIsolationTest`: 12 testes, 0 falhas.

- A forma da Loja (recebimentos integrados, nenhum título, extrato sem linhas, conta sem saldo inicial) devolve vendas apuradas e taxas, despesas e caixa como não apurado. O horário do extrato nulo não derruba a resposta.
- A linha nula do máximo confirmado é ausência.
- A falha de um bloco devolve o substituto e não escapa.
- Cada consulta continua filtrando o tenant e a empresa da sessão.

## Publicação 0.2.16

| Item | Valor |
|---|---|
| Versão | 0.2.16, em `GET /api/v1/system/info` |
| Banco | sem migração |
| Task web | `actionfinance-web:33`. Copiada da `:32`; só a imagem mudou |
| Flyway na web | `false` |
| Perfil | `production`. Sincronização de recebimentos ligada |
| Imagem na task | `sha256:bca5e837d53054903e8a236aad76515b74c7fd471d9b30a4c8cc8330608714b0` (linux/amd64) |
| Tag `0.2.16` no ECR | índice `sha256:cba3721d78389c13b11c64e02d71bfe69ec67101b810ef6aaa97656c2e2186fd`. A task usa o digest amd64, não o índice |
| Rollout | `COMPLETED`, desired 1, running 1, em 2026-11-10T15:18:55-03 |
| Health | `GET /actuator/health` 200, `{"status":"UP","groups":["liveness","readiness"]}` |

Retorno da aplicação: `actionfinance-web:32`, a task da 0.2.15. Reverter a task não mexe no banco.

## Conferência do Início

Depois do rollout não houve nova linha de `/api/v1/overview` no log. O 200 da sessão do gestor fica para a próxima abertura do Início.
