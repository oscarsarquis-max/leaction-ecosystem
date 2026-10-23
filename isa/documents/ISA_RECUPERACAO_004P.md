# ISA — recuperação do piloto

Data: 17/10/2026. Versão 0.5.3. O database `isa` existe na instância RDS `actionfinance`, PostgreSQL 17. O papel da aplicação é `isa_app`, com limite de 8 conexões. A aplicação não usa a credencial mestre nem a credencial do Finance. Uma leitura de tabela do Finance com `isa_app` foi recusada.

A cópia automática da instância continua valendo para o Finance e para a ISA juntos. Restaurar a instância inteira não é o procedimento da ISA.

## Cópia da ISA

Destino: bucket privado `isa-pilot-253137917703`, criptografia AES-256, sem acesso público. O prefixo `backups/` expira em 7 dias. O prefixo `erasures/` não expira com essa regra.

Agenda: EventBridge `isa-backup-daily`, todo dia às 09:00 UTC, task `isa-backup`. Falha de execução deixa rastro no log `/ecs/isa-backup` e no alarme `isa-backup-failure`. A primeira cópia terminou com sucesso em 17/10/2026, 21 tabelas, sem sessão e sem verificador PKCE. O piloto não aceita anexo; a cópia recusa sucesso se houver arquivo armazenado.

O intervalo entre cópias é de um dia. O que mudar depois da última cópia pode se perder. Isso não é recuperação em tempo real.

A 0.6.7 acrescenta as tabelas `work_batch`, `work_member`, `work_event` e `work_preference`. A cópia lógica da aplicação nova inclui essas tabelas. Uma cópia anterior à migration 7 não as contém, porque ainda não existiam; a aplicação nova cria as tabelas vazias e preserva os lançamentos. O retorno para 0.6.6 abre o schema 7 e continua lendo os lançamentos, sem mostrar os lotes de trabalho e sem apagá-los.

## Exclusão

O livro fica em `erasures/`, fora da cópia restaurável. Falha ao ler o livro interrompe a abertura da base; não é tratada como livro vazio. A restauração reaplica o livro antes de qualquer consulta.

Prova em database isolado `isa_restore_004p2`, depois removido: um registro sintético permaneceu e o registro esquecido não voltou. A instância compartilhada não foi restaurada sobre o Finance.

## O que não entra na cópia

Sessões, códigos de autorização, verificadores PKCE e tokens ficam de fora. O script manual `scripts/ops/backup-isa.py` continua sendo uma cópia local e não substitui a agenda.
