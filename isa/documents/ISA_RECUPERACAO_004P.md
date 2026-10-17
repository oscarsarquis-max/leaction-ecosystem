# ISA — recuperação do piloto

Data: 16/10/2026. Candidata 0.5.1. A publicação não aconteceu. Este texto diz onde os dados ficam hoje e como devem ficar quando o piloto for autorizado.

## Hoje

A demonstração do 004 continua em `C:\Projetos\isa\data\lab`. O ensaio do processo de produção, vazio de pessoa real, fica em `data\prod-rehearsal`. As duas pastas estão fora do Git. Não há dado da Eveline em nenhuma delas.

Reiniciar o processo de produção não apaga o SQLite do `ISA_DATA`. O teste trocou o processo e releu o compromisso gravado.

A cópia manual é:

```powershell
$env:ISA_DATA = "C:\Projetos\isa\data\lab"
$env:ISA_BACKUP_ROOT = "C:\Projetos\isa\data\backups"
python C:\Projetos\isa\scripts\ops\backup-isa.py nome-da-copia
```

O destino não pode ser a pasta ativa. A restauração de ensaio continua sendo `store.restore_dir` para um diretório vazio, como no relato do 004. Não há rota HTTP de backup nem de esquecimento no processo de produção.

Uma cópia no mesmo disco não protege contra a perda do equipamento. Antes de dado real, a cópia diária precisa ir para outro armazenamento. Esse bucket não foi criado. Até lá, a perda possível é tudo o que mudou desde a última cópia manual.

O tempo de restauração no serviço publicado não foi medido. O ensaio do 004 recuperou a base sintética dentro do próprio teste, num diretório vazio. Isso não é o tempo do piloto.

## Quando o piloto existir

- Base em `/var/lib/isa`, ou no database `isa` se a migração para `actionhub-prod` tiver sido ensaiada e autorizada. Nos dois casos, fora da pasta que o deploy apaga.
- Arquivos no mesmo lugar durável, separados por dono, com identificador e SHA-256.
- Cópia automática uma vez por dia e outra imediatamente antes de migração. Retenção proposta: 30 dias no destino externo, ainda por escrito do proprietário. A retenção de laboratório de 7 dias não vale para o dado da Eveline.
- Perda máxima com a cópia diária: até 24 horas do que foi confirmado depois da última cópia. Se a medição do banco oferecer ponto de recuperação menor, o número medido substitui este.
- Voltar o programa não apaga `/var/lib/isa` e não desfaz o esquema.
- Esquecer uma conta, quando essa função existir para o piloto, apaga o ativo da pessoa e deixa a cópia até o fim da retenção. Restaurar a cópia traria esses dados de volta até a cópia expirar.
- A conta da Eveline começa vazia. Marina, Paulo e o extrato usado na validação privada do leitor não entram nela.
- Sugestões, eventos, contexto e a decisão de aceitar ou recusar entram na mesma cópia. Aceitar não paga.

O SQL em `server/schema.postgres.sql` descreve as tabelas para o PostgreSQL. Ele não foi executado. Enquanto o aplicativo gravar em SQLite, a recuperação é a do arquivo `isa.sqlite` mais a pasta `files`.
