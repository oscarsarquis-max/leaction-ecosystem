# ISA — plano de implantação do piloto

Data: 16/10/2026. Candidata **0.5.1**, em cima do protótipo 0.5.0. Baseline proposta **1.2**. Não publicada. Nenhum recurso foi criado, nenhum DNS foi alterado e nenhum convite foi enviado.

O Prompt 005 continua reservado aos cartões. Cartão, Open Finance, agente pago e leitura de foto não são condição deste piloto.

## O que Eveline poderá testar, quando a publicação for autorizada

No endereço proposto, com a conta dela e a base vazia:

- entrar pela identidade da ISA, sem lista de participantes na página;
- registrar um lançamento digitado;
- importar um extrato e confirmar o que entra;
- responder quanto está disponível, quando recebe e o que precisa pagar;
- ver se o dinheiro falta antes da próxima entrada e comparar uma data, como no 004;
- sair, entrar de novo e reencontrar o que o servidor confirmou;
- mandar um recado sem anexar extrato.

As explicações continuam sendo regras locais. A tela diz que nenhuma IA foi chamada.

## O que ainda não existe

- O nome `isa.actionhub.com.br` não está registrado nesta zona. Em 16/10/2026 a consulta pública respondeu que o nome não existe, e a zona `actionhub.com.br` (`Z01698931CEOITJ7YYMYX`) não tem registro com esse nome. Isso não reserva o nome para amanhã.
- O certificado que hoje atende `actionhub.com.br`, `www` e `api` vale até 22/11/2026 e não inclui `isa`. Sem certificado novo, o endereço proposto não abre em HTTPS.
- Não há diretório de identidade da ISA. Os pools existentes são de outros produtos e não serão reutilizados. O botão Entrar do ensaio responde que o acesso não foi ligado e que nenhum convite foi enviado.
- O e-mail e o canal de ativação da Eveline não foram pedidos e não foram inventados.
- A base do ensaio é SQLite. O SQL de PostgreSQL em `server/schema.postgres.sql` não foi aplicado em RDS e o aplicativo ainda não grava nele.
- Aviso de privacidade com responsável, retenção e canal ainda precisa ser escrito antes de dados pessoais.
- A memória livre da máquina do Hub não foi medida.

## Consulta de 16/10/2026, só leitura

A zona pública `actionhub.com.br` existe na conta AWS `253137917703`, região `us-east-2`, com nove registros. Os nomes encontrados foram o ápice, `www`, `api`, `school`, `actionfinance` e a delegação `spider`. Não havia `isa`.

`actionhub.com.br`, `www`, `api` e `school.actionhub.com.br` apontam para a mesma máquina, um `t3.micro` em `us-east-2a`, disco gp3 de 30 GB. `actionfinance.actionhub.com.br` aponta para outros endereços. A ISA não entra no servidor nem no banco do Finance.

Bancos vistos, sem abrir dados:

| Instância | Motor | Classe | Disco |
| --- | --- | --- | --- |
| actionhub-prod | PostgreSQL 17.9 | db.t4g.small | 20 GB |
| actionfinance | PostgreSQL 17.9 | db.t4g.micro | 20 GB |

Pools de identidade vistos, sem listar pessoas: `actionfinance-operators`, `spider-sandbox-monitor`, `spider-prod-monitor`, `panne-prod`, `qmind-homolog-users`. Nenhum é da ISA.

A CLI da AWS usada já estava nesta máquina. Nada foi criado nem alterado.

## Caminho, quando houver autorização

1. Consultar de novo se `isa.actionhub.com.br` continua sem registro.
2. Medir memória livre do `t3.micro` e espaço livre em `actionhub-prod`. Se não couber, parar e escolher outro hospedeiro. Não colocar a ISA na máquina só porque a porta 443 já existe.
3. Criar o pool `isa-pilot`, plano Essentials, cliente público, autorização por código com PKCE, cadastro público desligado e redirecionamento só para `https://isa.actionhub.com.br/callback`. A lista de participantes começa vazia. A conta da Eveline só entra na lista com a instrução de ativação, que é outro passo.
4. Banco: criar o database `isa` e o papel `isa_app` em `actionhub-prod`, com credencial só da ISA, se o passo 2 mostrar espaço. Se não mostrar, a alternativa é uma instância nova `db.t4g.micro`, Single-AZ, PostgreSQL, citada no custo abaixo. Não usar `actionfinance`.
5. Um registro A na zona que já existe, apontando para o hospedeiro escolhido. Um arquivo novo do nginx, `server_name isa.actionhub.com.br` apenas, com proxy para `127.0.0.1:8099`. Não editar o `server_name` do Hub, da API, do Finance nem do school. Efeito esperado: só esse nome chega na ISA; os outros hosts seguem como estão.
6. Certificado só desse nome. Não reescrever o certificado atual do Hub.
7. Processo `server/prod_serve.py`, `ISA_ENV=production`, escutando só em `127.0.0.1`. Dados em `/var/lib/isa`, fora da pasta do código, usuário de sistema próprio. Segredos num arquivo de ambiente com permissão restrita, fora da imagem e do Git.
8. Cópia diária e uma cópia antes de migração, para um destino fora deste disco. Sem isso, não carregar dado real.
9. Jornada sintética no HTTPS: entrar, importar fixture, sair, entrar, reencontrar, salvar compromisso, ver projeção, recuperar sugestão. Health e versão não substituem esses passos.
10. Só então a instrução de ativação da Eveline. A conta dela começa vazia. Não copiar Marina, Paulo nem extrato de outra pessoa.

Voltar a versão do programa é trocar o artefato e recarregar o nginx da ISA. A pasta `/var/lib/isa` e o banco não são apagados nessa volta, e o esquema não é revertido sozinho.

## Custo incremental estimado

Preços lidos em 16/10/2026. Nada disto foi contratado.

| Peça | Fonte | Incremento |
| --- | --- | --- |
| Registro A na zona já existente | zona `actionhub.com.br` já existe | sem zona nova |
| Certificado do nome novo | Let's Encrypt, no mesmo modo do Hub | US$ 0 |
| Pool Cognito Essentials, uma pessoa | [preço do Cognito](https://aws.amazon.com/cognito/faqs/), consultado em 16/10/2026: 10 mil usuários ativos no mês ficam sem cobrança por conta; acima disso, US$ 0,015 por usuário ativo | US$ 0 se a conta ainda estiver na franquia; US$ 0,015 se a franquia dos outros pools já estiver cheia. O uso atual não foi medido |
| Database `isa` dentro de `actionhub-prod` | instância já ligada; armazenamento gp3 PostgreSQL US$ 0,115 por GB-mês, vigência da tabela 01/10/2026 | US$ 0 de instância se o disco de 20 GB não precisar crescer. O espaço livre não foi lido |
| Instância nova, só se a anterior não couber | tabela AWS, vigência 01/10/2026: US$ 0,016 por hora de `db.t4g.micro` PostgreSQL Single-AZ em us-east-2, cerca de US$ 11,68 em 730 horas, mais 20 GB × US$ 0,115 = US$ 2,30 | cerca de US$ 14 por mês, antes de cópia que exceda o disco |
| Processo na máquina atual | `t3.micro` já pago, também atende o Hub e o school | US$ 0 somente se a medição de memória autorizar. Sem essa medição, o custo de outra máquina não está fechado |
| Bucket de cópia | não consultado e não criado | conferir na calculadora antes de criar |

## Como a candidata se comporta

O laboratório continua em `serve.py`, com `http.server`, na porta 8098. Ele não deve ser publicado trocando host e porta. A [documentação do Python](https://docs.python.org/3/library/http.server.html) não recomenda esse servidor para produção.

`prod_serve.py` sobe com Waitress, só em `127.0.0.1`, e recusa `ISA_ENV=lab`. Em produção:

- `X-ISA-Lab-Person` recebe 401, mesmo acompanhado de token;
- `/api/fixtures`, `/api/forget` e `/api/backup` respondem 404;
- a página pública não lista Marina, Paulo nem Eveline;
- o dono sai do `sub` validado, não de nome, e-mail ou cabeçalho;
- pessoa fora da lista recebe 403;
- mais de 60 pedidos no minuto, do mesmo endereço, recebe 429;
- base ocupada recebe 503 com o texto para tentar de novo, sem gravar duas vezes por esse erro;
- origem diferente de `ISA_ORIGIN` recebe 403;
- arquivos servidos são a página, os quatro scripts, a folha de estilo e os CSV sintéticos de `prototype/fixtures`. Banco, cópia, documento e código não saem por essa rota.

O botão **Entrar como Eveline** fica só na demonstração e grava a pessoa sintética `pessoa-eveline-demo`. Não é a conta do piloto.

Ensaio local, sem publicação: `.\scripts\dev\start-isa-prod.ps1` abre `http://127.0.0.1:8099`.

## Verificação desta preparação

Quatro testes de `server/test_prod.py` passaram: recusa do cabeçalho de laboratório, fixture e limpeza invisíveis, duas pessoas sem ver o compromisso uma da outra, token expirado, URL de autorização com PKCE e sem segredo de cliente, e compromisso que continua depois de matar e subir o processo. Os quinze testes do 004 tinham passado na rodada imediatamente anterior.

No navegador, emulação 390 e 1280, a página de produção mostra **Entrar** e o aviso de que o convite não foi enviado. A demonstração em 8098 continua com Marina e com o botão de Eveline da demonstração. Não é um celular físico.

Capturas: `documents/prototipo/390-piloto-entrar.png` e `1280-piloto-entrar.png`.
