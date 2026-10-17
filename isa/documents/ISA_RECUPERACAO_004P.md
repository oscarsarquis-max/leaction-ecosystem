# ISA — recuperação do piloto

Data: 16/10/2026. Candidata 0.5.2. A publicação não aconteceu.

## O que o piloto usa

A base do piloto é PostgreSQL, em `ISA_DATABASE_URL`. O processo de produção recusa subir com um arquivo SQLite no lugar dessa URL. O laboratório do 004 continua no arquivo `isa.sqlite`, fora do Git, e não é o procedimento do piloto.

O database previsto na instância RDS `actionfinance` é `isa`, com o papel `isa_app`. Ele não foi criado. A instância já tem cópia automática de 7 dias e o ponto mais recente lido em 16/10/2026 foi `2026-10-17T01:01:08Z`. Restaurar a instância também restaura o Finance. O procedimento da ISA é a cópia lógica só do database `isa`, seguida da reaplicação do livro de exclusões.

## Exclusão que a restauração não desfaz

Esquecer uma pessoa grava o identificador no livro `ISA_ERASURE_LEDGER` e só então apaga as linhas. O livro fica fora do banco e fora da cópia lógica. `connect()` e a restauração reaplicam esse livro antes de qualquer consulta.

A prova, com dados sintéticos e dois donos: cópia lógica, exclusão de um, restauração num database vazio e separado. O dono excluído não volta em compromisso nem em identidade. O outro dono permanece. Sem o livro ao lado da cópia, essa proteção não existe.

## O que está automatizado e o que não está

Os scripts são manuais:

```powershell
$env:ISA_DATABASE_URL = "postgresql://..."
$env:ISA_BACKUP_ROOT = "C:\Projetos\isa\data\backups"
python C:\Projetos\isa\scripts\ops\backup-isa.py nome-da-copia

$env:ISA_RESTORE_URL = "postgresql://.../isa_restore"
$env:ISA_ERASURE_LEDGER = "C:\caminho\erasure-ledger.jsonl"
python C:\Projetos\isa\scripts\ops\restore-isa.py C:\caminho\da-copia
```

`ISA_RESTORE_URL` precisa ser outro database. A restauração recusa usar o database ativo. O script termina dizendo que a agenda e o destino externo não estão implantados. Não há bucket, não há agenda e uma pasta no mesmo disco não protege contra a perda do equipamento.

O livro também precisa ir para o destino externo, separado do arquivo da cópia. Esse destino não foi escolhido. Até lá, a perda possível é o que mudou desde a última execução manual, e uma cópia antiga restaurada sem o livro recolocaria uma pessoa esquecida. Por isso a restauração de dado real não deve ocorrer antes do destino externo do banco e do livro.

A retenção externa continua por escrever do proprietário. A retenção de laboratório de 7 dias não vale para o dado da Eveline. A conta dela, quando for ativada, começa vazia. Marina, Paulo e o extrato usado na validação privada do leitor não entram nela.
