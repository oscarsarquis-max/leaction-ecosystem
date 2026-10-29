# Pedido único ao proprietário — cópia restaurada dos cadastros

Data: 05/10/2026. Documento de autorização. Não pede senha, MFA, cookie nem secret pelo chat. Não autoriza restore no origin nem infraestrutura paga.

## O que já foi feito sem esta autorização

Ensaio sintético em destino descartável (`rehearse-isolated-restore-015.ps1 -Synthetic`): V13→V19 com os arquivos da candidata, invariantes de IDs, vínculos, valores, contagens, grants e documento pendente. Checksum local de V13 = `728072343` (igual ao origin inspecionado em 05/10/2026). Isso **não** é a cópia do origin.

## Pedido

Autorizar **uma** operação de leitura do origin para ensaio isolado, com estes limites:

| Campo | Valor pedido |
|---|---|
| Origem | Instância RDS `actionfinance`, conta `253137917703`, região `us-east-2`, host `actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com`, banco `actionfinance`, schema `actionfinance` |
| Acesso | Papel **somente leitura** capaz de `pg_dump` (não o papel de escrita da aplicação). Credencial entregue pelo canal operacional já usado para inspect 012, **não** pelo chat |
| Conteúdo | Dump custom (`--format=custom`) só do schema `actionfinance`. Sem outros bancos |
| Destino | Postgres descartável no operador local, volume `actionfinance_restore_015` (ou equivalente), **distinto** de `actionfinance_pgdata_17` e do RDS. Identidade conferida pelo script 015 (DNS/data_directory/rótulo) **antes** de escrever |
| Proteção | SHA-256 na origem e no destino; dump só no host do ensaio; sem cópia para notebook pessoal, repositório ou chat |
| Retenção | Até a decisão de publicar ou arquivar este recorte; depois apagar dump e volume |
| Responsável | Proprietário nomeia quem executa o script; o agente não assume autorização |
| Custo | Este pedido usa Docker local. **Não** cria RDS, NAT nem tarefa paga |
| Operações previstas | 1) dump leitura; 2) restore no destino isolado; 3) `flyway migrate` até V19 com os arquivos da candidata; 4) comparar IDs, vínculos, `amount_minor`, contagens, grants e cobertura de documentos; 5) apagar dump/volume ao encerrar |

## O que este pedido não autoriza

Migrar o RDS público. Restaurar por cima do origin. Publicar imagem. Trocar `actionfinance-web:11`. Cobrar, ligar Pay/Spider/Panne ou alterar Cognito. Infraestrutura com custo. Entrega de senha neste chat.

## Como recusar sem bloquear o restante

Se a cópia for recusada ou o acesso de leitura não existir, o estado permanece: procedimento pronto; ensaio sintético aprovado; cópia do origin **não executada**. Isso não é falha da interface do recorte 014.
