# ACTIONFINANCE_REV_PUBLICACAO_EXTRATO_034

Data: 15/10/2026. Produto **0.2.0** publicado. Schema público em Flyway **V23**. A importação do relatório real **não** foi feita. A sessão autenticada do proprietário **não** percorreu a tela. Spider, Hub, Mercado Pago, Cognito e Loja não foram alterados.

## Decisão

O checksum de V20 foi realinhado ao script que já estava aplicado. Em seguida o migrator aplicou somente V21–V23 e a task web passou a servir a imagem da candidata 033, com Flyway desligado. Não houve seed, clean, baseline, DROP nem correção de outra versão.

## Conferência de V20 antes da correção

O script V20 só acrescenta colunas, a restrição `pay_receipt_txn_payer_kind_chk` e comentários. Não contém `INSERT`, `UPDATE` nem `DELETE`.

Leitura produtiva, sem conteúdo de linha:

| Efeito | Presente |
|---|---|
| `commercial_application` varchar 80, nula | sim |
| `commercial_description` varchar 200, nula | sim |
| `payer_kind` varchar 16, nula | sim |
| `payer_label` varchar 200, nula | sim |
| `payer_provenance` varchar 40, nula | sim |
| `payment_method` varchar 40, nula | sim |
| `processor_name` varchar 40, nula | sim |
| `provider_status` varchar 40, nula | sim |
| `paid_amount_minor` numeric, nula | sim; a coluna é de V13, o comentário é de V20 |
| `pay_receipt_txn_payer_kind_chk` | `EMAIL`, `SUBJECT`, `ABSENT` ou nulo |
| Comentários de `payer_label`, `commercial_application`, `processor_name` e `paid_amount_minor` | texto do script |
| `statement_line` | ausente |

Contagens antes da manutenção: títulos 0, baixas 0, movimentos 0, recebimentos 16. V20 estava `success=true`, descrição `pay receipt commercial identity`, tipo `SQL`, script `V20__pay_receipt_commercial_identity.sql`, checksum `-145522935`, `installed_on` `2026-10-15 10:43:47.924579`, `installed_by` `actionfinance_admin`. V1–V19 coincidiam com o ensaio, inclusive descrição, tipo e checksum.

A recuperação já existente era a janela de restauração pontual de 7 dias e o snapshot automático `rds:actionfinance-2026-10-15-07-09`. Não foi criado snapshot novo. A cópia do histórico ficou nos logs da leitura, sem segredo.

## Ensaio isolado

Postgres 17.6 descartável e Flyway **11.10.1**, com V1–V23 do repositório. Depois de aplicar até V20, só o checksum de V20 foi trocado para `-145522935`. O `repair` registrou uma única correção, a versão 20, para `-1282662839`. Descrição, tipo, script, sucesso, autor e tempo de execução das vinte linhas permaneceram iguais. Nenhuma linha foi removida ou marcada como apagada. A validação seguinte aceitou 23 migrations e aplicou só V21–V23. O container foi removido.

## Correção produtiva

Imediatamente antes, a mesma leitura se repetiu: V20 ainda em `-145522935`, descrição e tipo iguais, contagens iguais, sem tabela de extrato. A única task em execução era a web `actionfinance-web:16`.

| Peça | Valor |
|---|---|
| Mecanismo | `repair` do Flyway 11.10.1, locations com V1–V23 |
| Imagem | `sha256:d2fa21655a79dfc1d327439639e3d93ab17e72ee6ed2bb9b9f5ee9109177ee49` |
| Task | `36859feb01c945759570c723f0f01988` |
| Relógio | início `2026-10-15 18:19:15 -03`, fim `18:19:55 -03`, saída 0 |
| Papel no banco | `actionfinance_migrator` |
| Efeito registrado | só a versão 20, descrição e tipo inalterados, checksum `-1282662839` |

A leitura seguinte manteve V1–V19 e o `installed_on` de V20. O `installed_by` de V20 continuou `actionfinance_admin`: o repair não reaplicou a versão. Checksum novo: `-1282662839`. Sucesso continuou verdadeiro.

## V21–V23

Task `d04e31af26804779a70be4413e8ff956`, mesma imagem, comando `migrate`. Início `2026-10-15 18:21:59 -03`, fim `18:22:47 -03`, saída 0. O log validou 23 migrations, partiu da versão 20 e aplicou 21, 22 e 23.

| Versão | Checksum | Sucesso | Instalada em | Autor |
|---|---|---|---|---|
| 20 | `-1282662839` | true | `2026-10-15 10:43:47.924579` | `actionfinance_admin` |
| 21 | `1478367557` | true | `2026-10-15 21:22:19.062471` | `actionfinance_migrator` |
| 22 | `-352324955` | true | `2026-10-15 21:22:20.559714` | `actionfinance_migrator` |
| 23 | `-528332928` | true | `2026-10-15 21:22:20.858887` | `actionfinance_migrator` |

Os checksums de V21–V23 são os do ensaio. Depois: títulos 0, baixas 0, movimentos 0, recebimentos 16, lotes 0, linhas 0, ocorrências 0, vínculos 0.

## Publicação

Código `e160996f34f2d08bdc6ac29b8055a3b0e9167b64`. A imagem local `actionfinance:candidate-033` foi enviada sem reconstrução.

| Peça | Valor |
|---|---|
| Índice no registro | `sha256:fcce948d9ba074b75af0352d1bb5a29c9f27e240e2c341039312a80318089256` |
| Manifesto linux/amd64 servido | `sha256:2e6ccb8fed8dd65f7b1547a1ef65cd8c0ff70b889454163b536f066183ecd31f` |
| JAR na imagem | `sha256:c242c6c7e6cdf8749b082ceb764320e1cfeaa1972688ee8e99a17c49ebd34338` |
| Task | `actionfinance-web:17`, execução `9a14f6e1f2e54f05a7355db3c3ce4ab1` |
| Rollout | `COMPLETED`, desejada 1, em execução 1, falhas 0, `HEALTHY` |
| Flyway da task web | `ACTIONFINANCE_FLYWAY_ENABLED=false`, perfil `production` |
| Health e readiness | `UP` |
| `GET /api/v1/system/info` | `version=0.2.0`, `stage=FOUNDATION`, `accessMode=OIDC` |
| HTML e `/financial-accounts/statement` | shell 200, script `/assets/index-DzYbnxZv.js` |
| Bundle servido | `index-DzYbnxZv.js`, SHA-256 `793bd3fdfb0a64e45efce914998acb0a7c8f80a730ca23cb2e396343100aa948` |

O bundle contém a rota `/financial-accounts/statement`, «Em revisão», «Clientes e fornecedores», «Recebimentos ActionHub Pay» e «Sair». Sem sessão, lotes, linhas, cadastros e recebimentos respondem 401. HTTP 200 do shell não é jornada autenticada.

Rollback da aplicação, ainda no registro: `actionfinance-web:16`, `sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec`, produto 0.1.2. Voltar a imagem não apaga o schema V23.

## O que ficou separado

Publicação: feita. Verificação autenticada de Contas → Extrato: pendente do login já existente do proprietário em `https://actionfinance.actionhub.com.br/financial-accounts/statement`. Importação real: não feita; as tabelas de extrato estão vazias. Os nove pares ambíguos não foram resolvidos.
