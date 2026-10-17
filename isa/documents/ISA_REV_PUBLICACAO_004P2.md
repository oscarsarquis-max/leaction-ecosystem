# ISA — publicação 004P2

Data: 17/10/2026.

## O que está no ar

| Item | Valor |
| --- | --- |
| Endereço | https://isa.actionhub.com.br |
| Versão | isa-piloto 0.5.3 |
| Commit | `d27dd88b2efbffc4ad639d628d8202a53d66daf1` |
| Imagem | `sha256:68b0ad25125f1bd46c189ba1d0a2936c16110d4438bd6b92a0888773820829e7` |
| Task | `isa-web:7`, 256 CPU / 512 MB, porta 8091, sem IP público |
| Cluster | `actionfinance-cluster` |
| Ingresso | `paneldx-alb`, regra de prioridade 7, host exato |
| Banco | database `isa`, papel `isa_app`, schema 3, PostgreSQL 17 |
| Identidade | pool próprio `isa`, cliente público com PKCE |
| Cópia | bucket `isa-pilot-253137917703`, agenda diária 09:00 UTC, retenção de 7 dias |

O health público respondeu versão 0.5.3, diretório real e PostgreSQL. Sem sessão, a API devolve 401. O cookie de sessão conferido no navegador foi `Secure`, `HttpOnly`, `SameSite=Lax`, restrito ao host da ISA.

## Acesso inicial

O usuário `oscar@oscarsarquis.com.br` foi criado no diretório da ISA. A mensagem automática foi suprimida. A posse do e-mail não foi marcada como verificada. O convite da Eveline, enviado depois, está em `ISA_REV_CONVITE_ACESSO_004P3.md`. Receber a cópia não ativa o acesso de Oscar.

A identidade de prova usada no navegador foi removida, junto com os lançamentos sintéticos. A lista passou a ter o acesso inicial e o da Eveline.

## O que foi conferido

No navegador, em 390 e 1280 px: entrada com Entrar e recuperação, sem Marina, Paulo ou Eveline; conta vazia orientando a registrar ou importar; importação de um CSV sintético com prévia e gravação; os mesmos lançamentos numa sessão nova; a segunda pessoa não viu esses lançamentos. O planejamento perguntou o disponível e a data, sem o botão do exemplo de outubro. A página não inventou saldo.

A restauração isolada preservou um registro sintético e não devolveu o excluído. O database de ensaio foi apagado. A primeira cópia lógica no bucket terminou com sucesso.

## Finance

Antes e depois: serviço `actionfinance` desejado 1 e em execução, task `actionfinance-web:27`, regra 6 de `actionfinance.actionhub.com.br` para o mesmo target group, alvo saudável. O `paneldx-alb` não foi substituído. Nenhum balanceador novo foi criado.

## Custo incremental

A task web, 0,25 vCPU e 0,5 GB, fica em cerca de US$ 9,01 a cada 730 horas, pelos preços lidos em 16/10/2026 em `us-east-2`. A cópia diária usa a mesma taxa por um tempo curto, não por outro mês inteiro. Não há hora nova de RDS nem ALB novo. Log, tráfego, LCU e o armazenamento pequeno do bucket não foram medidos como zero. O Cognito da conta pode já ter consumido a franquia; uma pessoa, se for cobrada, custa US$ 0,015 no mês.

## Pendências

Publicação: o endereço responde. Ativação: o convite não foi enviado. Aceite: o proprietário ainda não aceitou a tela nem o uso financeiro. Cartões, foto, banco automático e IA externa não entram neste release.
