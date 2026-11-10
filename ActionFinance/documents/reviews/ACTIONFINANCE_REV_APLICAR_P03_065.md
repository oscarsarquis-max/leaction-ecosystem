# ACTIONFINANCE_REV_APLICAR_P03_065

10/11/2026. O Início do uso real entrou na 0.2.17, e "De onde veio o dinheiro" nomeia os códigos conhecidos do Pay. Spider, Loja e Hub não foram alterados. Não houve mudança de banco.

A cópia do prompt está em [ACTIONFINANCE_PROMPT_APLICAR_P03_065.md](../prompts/ACTIONFINANCE_PROMPT_APLICAR_P03_065.md).

## SSH

Os security groups `actionfinance-svc` e `actionfinance-db` continuam sem regra na porta 22. O serviço roda em Fargate, sem SSH. Nenhuma regra foi aberta.

## Patch

`git am -3` de `P03-inicio-uso-real.patch` sobre `ff9f6f2c`, sem conflito. O commit aplicado é `2721c33f6a0a0b97667f7349651f30513cec9dce`. A base declarada era `92ecd1a`. O patch só entra em `frontend/src` (HomePage e app.css).

## Métodos

| Código | Nome |
|---|---|
| `pix` | Pix |
| `card` | Cartão |
| `credit_card` | Cartão de crédito |
| `debit_card` | Cartão de débito |
| `account_money` | Saldo Mercado Pago |
| `ticket`, `bolbradesco` | Boleto |

Código desconhecido continua "Outros" e o log registra só esse código.

## Testes

Não rodei a suíte inteira.

- `App.test.tsx` e `HomePage.test.tsx`: 32 testes, 0 falhas.
- `OverviewServiceTest` e `OverviewStoreIsolationTest`: 13 testes, 0 falhas. `card` aparece como Cartão.

## Publicação 0.2.17

| Item | Valor |
|---|---|
| Versão | 0.2.17, em `GET /api/v1/system/info` |
| Banco | sem migração |
| Task web | `actionfinance-web:34`. Copiada da `:33`; só a imagem mudou |
| Flyway na web | `false` |
| Perfil | `production`. Sincronização de recebimentos ligada |
| Imagem na task | `sha256:9d01d7e9876970d40da1469ccb4b824200f5f542bc9bf0c2013586804b6fe1d3` (linux/amd64) |
| Tag `0.2.17` no ECR | índice `sha256:d5c67d5316970597300349ece152beab104c6b77f1e4390f75eae75ab2d73b46`. A task usa o digest amd64, não o índice |
| Rollout | `COMPLETED`, desired 1, running 1, em 2026-11-10T17:11:31-03 |
| Health | `GET /actuator/health` 200, `{"status":"UP","groups":["liveness","readiness"]}` |

Retorno da aplicação: `actionfinance-web:33`, a task da 0.2.16. Reverter a task não mexe no banco.

A tela fica para o Oscar conferir.
