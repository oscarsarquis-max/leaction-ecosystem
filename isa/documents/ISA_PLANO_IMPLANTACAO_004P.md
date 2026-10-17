# ISA — plano de implantação do piloto

Data da publicação: 17/10/2026. Versão servida **0.5.3**, commit `d27dd88b2efbffc4ad639d628d8202a53d66daf1`, imagem `sha256:68b0ad25125f1bd46c189ba1d0a2936c16110d4438bd6b92a0888773820829e7`. Baseline proposta **1.2**. O endereço https://isa.actionhub.com.br está no ar. O convite do acesso inicial não foi enviado.

O texto da 0.5.1 dizia que a ISA não entrava no servidor nem no banco do Finance e apontava a máquina do Hub com o RDS `actionhub-prod`. O proprietário rejeitou essa exclusão. Separar a ISA é ter aplicação, identidade, permissão e dados próprios. Não é proibir o uso da infraestrutura que já hospeda o Finance.

O Prompt 005 continua reservado aos cartões.

## Destino publicado

O piloto entrou no ambiente que já executa o Finance, pelo balanceador existente `paneldx-alb`. Não há ALB novo.

| Peça | O que já existia | O que a ISA passou a usar |
| --- | --- | --- |
| Conta e região | `253137917703`, `us-east-2` | a mesma |
| Computação | cluster Fargate `actionfinance-cluster`, serviço `actionfinance`, task `actionfinance-web:27`, 512 CPU / 1024 MB, 1 tarefa | serviço, task definition, imagem e target group novos. Tamanho proposto: 256 CPU / 512 MB. A task do Finance não é editada |
| Rede da tarefa | sub-redes privadas `subnet-0693afdb3330b683a` e `subnet-0a1da7a0765588962`, sem IP público, security group `sg-02d2aacb3b77e4a41` | as mesmas sub-redes e o mesmo security group. Ele já é o único autorizado a abrir a porta 5432 |
| Entrada HTTPS | ALB internet-facing `paneldx-alb`, listener 443. A regra de prioridade 6 é só `actionfinance.actionhub.com.br` | regra nova, prioridade 7, host `isa.actionhub.com.br`. As prioridades 7, 8 e 9 estavam livres. A regra 6 não é editada |
| Certificado | o listener do ALB, não o nginx nem o Let's Encrypt da máquina do Hub | certificado público ACM só desse host, no listener que já existe |
| Banco | instância RDS `actionfinance`, PostgreSQL 17.9, `db.t4g.micro`, 20 GB gp3, máximo 50 GB, criptografada, sem acesso público, uma zona, proteção contra exclusão. O database atual também se chama `actionfinance`. Grupo `default.postgres17` | database `isa` e papel `isa_app`, só com esse database. Sem tabela, credencial ou usuário do Finance |
| Nome | zona `actionhub.com.br` (`Z01698931CEOITJ7YYMYX`) | um registro A ou alias para o ALB que já existe. Em 16/10/2026 `isa.actionhub.com.br` não existia na zona e o DNS público respondeu que o nome não existe. Isso não reserva o nome |

O RDS escuta 5432 somente a partir de `sg-02d2aacb3b77e4a41`, sem faixa de endereço aberta. Colocar a task nova nesse grupo alcança o banco sem acrescentar regra e sem alterar a task do Finance. O papel `isa_app` não recebe permissão sobre o database `actionfinance`. O usuário mestre da instância continua capaz de ler todos os databases; a aplicação da ISA não usa essa credencial e o segredo do Finance não é trocado.

A máquina `t3.micro` do Hub e o RDS `actionhub-prod` não são o destino. Também não são o plano reserva automático.

## Capacidade lida em 16/10/2026

Consulta só de leitura, 336 pontos horários nos 14 dias anteriores. Nada foi criado.

Instância `actionfinance`:

| Medida | Mediana da média horária | Pico observado |
| --- | --- | --- |
| CPU | 3,8% | 7,4% |
| Memória livre | 165.400.000 bytes, cerca de 158 MiB, numa instância de 1 GiB | 219.400.000 bytes |
| Disco livre | 18,32 GB dos 20 GB alocados | o disco permaneceu nessa faixa |
| Conexões | 10 | 20 no máximo horário; a maior média horária foi 12,2 |

O grupo de parâmetros é o padrão do PostgreSQL 17. A fórmula padrão de `max_connections` é a memória da classe dividida por 9.531.392, com teto de 5.000. Para 1 GiB isso dá cerca de 112 conexões. O valor efetivo não foi lido de dentro do banco. O pico visto, 20, cabe com folga nesse teto. Uma aplicação a mais, com poucas conexões, não esgota a CPU, o disco nem as conexões.

A memória livre é o limite apertado. Se a memória livre passar a permanecer abaixo de cerca de 100 MB, a database da ISA não deve ser criada nesta instância. Nesta leitura ela não estava nesse patamar.

Serviço `actionfinance` no mesmo período: CPU com mediana de 0,6% e um pico horário de 100%, compatível com uma publicação. Memória estável, mediana 30,9% de 1024 MB e pico 31,7%. A cota de vCPU Fargate on demand na região está em 140. Uma task de 0,25 vCPU não mexe nessa cota de modo relevante.

O ponto de restauração mais recente da instância, lido junto com a descrição, foi `2026-10-17T01:01:08Z`. A retenção automática é de 7 dias, janela 07:00–08:00 UTC, manutenção no domingo 08:00–09:00 UTC. Essa restauração é da instância inteira e devolveria também o Finance. Não é o procedimento da ISA.

## O que a candidata já faz

O processo de produção é `server/prod_serve.py`, Waitress, só em `127.0.0.1`. Ele recusa `ISA_ENV=lab` e recusa subir sem `ISA_DATABASE_URL` de PostgreSQL. Não abre `isa.sqlite`. O laboratório do 004 continua em `serve.py` e em SQLite, e não deve ser publicado.

O botão Entrar chama `GET /api/login/start`. O servidor guarda o `state` e o verificador PKCE, redireciona para o endereço de autorização obtido na descoberta e recebe o código em `/callback`. A troca ocorre no `token_endpoint` da descoberta. O emissor usado para validar o token não é concatenado com `/oauth2/authorize`. A API aceita token de acesso: uso `access`, emissor, validade e `client_id` ou audiência iguais ao cliente configurado. Token de identidade e token ou proprietário na URL são recusados. Uma chave desconhecida provoca nova leitura do JWKS. A sessão é um identificador aleatório em cookie `HttpOnly`, `SameSite=Lax`, e `Secure` quando a origem é HTTPS. Sair apaga a sessão. A recuperação abre o endereço do provedor. O cabeçalho de laboratório continua recusado e a lista de participantes continua fechada quando vazia.

O ensaio em `server/rehearsal_idp.py` exercita redirecionamento e troca. O health responde `auth: ensaio` quando `ISA_OIDC_REHEARSAL=1`. Isso não é o Cognito. A publicação recusa esse ensaio. O pool publicado é só da ISA. Os pools de outros produtos não foram reutilizados.

Na página pública, conta, prévia, confirmação do lote, consulta, edição, categoria, pendência e vínculo passam pela API. O sucesso aparece depois da resposta do servidor. A prévia pode ficar em rascunho no servidor. O `sessionStorage` não é a cópia financeira. Quem consulta é a sessão, não uma pessoa fictícia escolhida antes.

A prova pela tela, neste ensaio, importou o extrato sintético, deixou pendência, saiu, abriu outro contexto sem os dados da aba, entrou de novo e recuperou 9 lançamentos. Confirmou uma decisão, o processo foi reiniciado, a releitura não aumentou a lista e a segunda pessoa não viu esses registros. Foi emulação em 1280 e 390, não um celular físico.

As migrações até a versão 3, a transação, a importação repetida, a concorrência de duas gravações e a restauração foram executadas em PostgreSQL 17 local, na porta `127.0.0.1:5442`. Esse container não é o RDS e a senha dele não é credencial do Finance.

## O que ficou pendente depois da publicação

- O acesso de `oscar@oscarsarquis.com.br` foi criado com a mensagem automática suprimida e sem a posse do e-mail marcada como verificada. Entrar só fica possível depois que o proprietário pedir o envio do convite.
- A cópia diária cobre até 24 horas. Não é recuperação imediata.
- Cartões, foto, Open Finance, movimentação bancária e IA externa continuam fora. O Prompt 005 segue reservado aos cartões.

## Custo só desta arquitetura

Preços lidos na API de preços da AWS em 16/10/2026, região `us-east-2`. Nada foi contratado. Uma instância nova de banco não entra nesta conta.

| Peça | Fonte | Incremento |
| --- | --- | --- |
| Task Fargate Linux/x86, 0,25 vCPU e 0,5 GB, 730 horas | Price List: US$ 0,04048 por vCPU-hora e US$ 0,004445 por GB-hora | cerca de US$ 9,01 antes de log e de tráfego |
| Log e tráfego de dados | não medidos | não lançar como zero. O volume do piloto ainda não existe |
| ALB | o `paneldx-alb` já existe. Uma regra não cria outro balanceador | o aumento de LCU não foi isolado e não entra como zero |
| Instância RDS | já ligada para o Finance | US$ 0 de hora nova de instância |
| Armazenamento, se o disco de 20 GB crescer | GP3 PostgreSQL Single-AZ, US$ 0,115 por GB-mês | US$ 0,115 por GB que passar a ser alocado. O espaço livre atual, cerca de 17 GB, não é crédito novo |
| Cópia automática do RDS | retenção de 7 dias já ligada na instância | o armazenamento de backup acima do volume provisionado não foi medido e não entra como zero |
| Cópia lógica externa e livro de exclusões | destino não escolhido e não criado | sem preço fechado. A ausência do destino não é custo zero |
| Registro na zona já existente | zona `actionhub.com.br` já existe | sem zona nova |
| Certificado público ACM | certificado público do Certificate Manager, no listener já existente | sem cobrança de certificado público |
| Cognito Essentials, uma pessoa a mais | [perguntas frequentes do Cognito](https://aws.amazon.com/cognito/faqs/), 10 mil usuários ativos no mês sem cobrança por conta; depois, US$ 0,015 | o uso atual dos outros pools não foi medido. Não orçar US$ 0. Se a franquia da conta já estiver cheia, uma pessoa custa US$ 0,015 no mês |

## Volta atrás

Desligar a ISA é zerar a contagem do serviço novo e remover a regra 7 e o registro do host. A task e a regra do Finance ficam como estão. O database `isa`, se tiver sido criado, não é apagado nessa volta. O esquema não é revertido sozinho.
