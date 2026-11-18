# ACTIONFINANCE_REV_ESTADO_PUBLICADO_055

09/11/2026. Leitura do que está servido em https://actionfinance.actionhub.com.br, comparada com [ACTIONFINANCE_REV_PUBLICACAO_CONTAS_054R1.md](ACTIONFINANCE_REV_PUBLICACAO_CONTAS_054R1.md). Nada foi publicado, migrado ou alterado.

## Tabela

| Item | Registrado no 054R1 | Encontrado hoje | OK/Divergente |
|---|---|---|---|
| Versão pública | 0.2.11 | 0.2.11 em `GET /api/v1/system/info` | OK |
| SPA | `index-Dd2g04DF.js`, `index-DdIcnaWp.css` | os mesmos nomes no HTML | OK |
| `GET /actuator/health` | 200 | 200, `status` UP | OK |
| `GET /api/v1/financial-accounts` sem sessão | 401 | 401 | OK |
| Task definition | `actionfinance-web:28` | `actionfinance-web:28` | OK |
| Imagem em execução | `sha256:f4fe545976b6dded0c9a3c4cab0d16c4eefcac21c077230ce3851505d0edf208` | o mesmo digest | OK |
| Flyway na task web | `false` | `false` | OK |
| Rollout | `COMPLETED`, uma task, `HEALTHY` | `COMPLETED`, desired 1, running 1, `HEALTHY` | OK |
| Deployment | publicação de 22/10/2026 | criado em 2026-10-22T13:04:53-03; atualizado em 2026-11-09T00:29:33-03 | Divergente no horário de atualização |
| Processo | task `HEALTHY` | a task atual subiu em 2026-11-09T00:28:21-03, com a mesma definição | Divergente no processo |
| `actionfinance-px-tg` | não detalhado; a task estava `HEALTHY` | 1 alvo, `healthy` | OK |
| Regra de host, prioridade 6, `paneldx-alb` | não detalhada; o host já respondia | presente no listener 443, encaminha para `actionfinance-px-tg` | OK |
| Snapshot `actionfinance-pre-v25-20261022` | `available`, criptografado, progresso 100, início 2026-10-22T15:47:59Z | igual | OK |
| RDS `actionfinance` | não registrado | `available`, postgres 17.9, `db.t4g.micro`, Multi-AZ não, retenção 7 dias | sem base no 054R1 |
| Último snapshot automático | não registrado | `rds:actionfinance-2026-11-09-07-09`, `available`, 2026-11-09T07:09:11Z. Último ponto restaurável 2026-11-09T17:50:34Z | sem base no 054R1 |
| Branch e commit | `5be64152` em `feat/actionfinance-extrato-032` | a mesma branch; HEAD `249541b4`; `5be64152` está no histórico | Divergente no git |
| Versão no código | 0.2.11 na candidata | `backend/pom.xml` e `frontend/package.json` em 0.2.11; esses arquivos não mudaram desde `5be64152` | OK |
| Árvore de trabalho | não registrada | 8 arquivos sujos em `ActionFinance` | sem base no 054R1 |
| Logs de 7 dias | não registrados | 32 eventos no grupo do serviço web; 0 ERROR; 0 linhas com código 5xx; nenhuma mensagem de erro | sem base no 054R1 |
| Schema V25 | aplicada, checksum `318546030` | não verificado | não verificado |

Entre `5be64152` e o HEAD há 417 arquivos em `ActionFinance`. Nenhum está em `backend/src`, `frontend/src`, `backend/pom.xml` ou `frontend/package.json`. São 330 em `documents` e 87 fora disso (scripts, capturas de prova e o Terraform em `ops/aws/terraform`, 13 arquivos, cerca de 823 linhas inseridas e 210 removidas).

## Divergências e riscos

O artefato público é o do 054R1: versão 0.2.11, os mesmos `index-*`, task `actionfinance-web:28` e o mesmo digest. Flyway segue desligado.

A task que responde hoje não é o processo de 22/10. Ela subiu em 09/11 às 00:28 (−03). O log das 00:34 (−03) é o encerramento gracioso da task anterior. A definição e a imagem não mudaram. A causa da troca não foi investigada.

O HEAD da branch passou de `5be64152` para `249541b4`. A versão declarada continua 0.2.11 e o código da aplicação não mudou, mas o Terraform no git mudou. Publicar a partir deste HEAD não seria o mesmo commit da imagem que está no ar. Esta leitura não comparou esses arquivos com o que está aplicado.

O grupo de log só guarda a subida de hoje e o encerramento da task anterior. Não há ERROR. O serviço não grava log de acesso, então uma resposta 5xx sem exceção não apareceria aqui.

## Não verificado

- Schema V25 e o checksum Flyway: o banco não foi aberto. O prompt proíbe escrita e não pediu consulta.
- Jornada autenticada (Dados da conta): esta leitura é sem sessão, como a prova pública do 054R1.
- Se o Terraform do HEAD está aplicado: fora dos itens do passo 3. A conta foi lida só na task, no alvo, na regra de host e no RDS.
- Causa da substituição da task em 09/11: só há o horário do deployment e o log de encerramento gracioso.
