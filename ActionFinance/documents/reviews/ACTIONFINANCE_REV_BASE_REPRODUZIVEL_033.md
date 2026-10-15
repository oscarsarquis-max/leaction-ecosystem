# ACTIONFINANCE_REV_BASE_REPRODUZIVEL_033

Data: 15/10/2026. Candidata **0.2.0**. Não publicada. O produto no ar permanece **0.1.2**. A ISA permanece pausada. Nenhuma migration foi aplicada no RDS. O arquivo real não foi importado. Spider, Hub, Mercado Pago e Cognito não foram alterados.

## Decisão

A candidata é reproduzível a partir do Git e sobe num banco isolado de V20 para V23 sem perder cadastros, títulos, baixas ou movimentos. **Não está pronta para publicar no RDS atual.** O Flyway 11.10.1 recusa a versão 20 porque o histórico público guarda o CRC32 do arquivo, não o checksum do algoritmo Flyway. Esta rodada não fez repair, não editou o script e não alterou o banco público.

## Git

Branch local `feat/actionfinance-extrato-032`. Sem upstream. Não houve push.

| SHA | Papel |
|---|---|
| `6c7028bfee93bb09cd01b6a1b9038bea125c18aa` | Candidata de extrato do 031, preservada |
| `fce19386bf5ebb5f0887fcbd87de2918aeb9235d` | Preservação das ocorrências do 032, preservada |
| `4c2a67e9db23af32720b269c3d67dd240df31249` | Só a linha do hash no relato 032. Conferido |
| `34e1b59b33ff8f8e054a83f277b301f7ad4e613b` | Scripts V13–V20 |
| `3baf7a25206562744a3db6467049580376febe06` | Cadastros, logout e apresentação de recebimentos já públicos |
| `44a8319d1ecaf616e07ea7753363c4292f93e43d` | Tipo da lista de extrato aceito pelo `tsc` |
| `e160996f34f2d08bdc6ac29b8055a3b0e9167b64` | Commit de código citado pelo manifesto. O script de imagem passa a esperar o JAR 0.2.0 |

O manifesto e este relato ficam num commit documental posterior. Esse commit não contém o próprio hash.

## Produto publicado

Leitura da task em execução `actionfinance-web:16`, rollout `COMPLETED`.

| Peça | Valor |
|---|---|
| Imagem | `253137917703.dkr.ecr.us-east-2.amazonaws.com/actionfinance@sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec` |
| Índice OCI local `apresentacao-028` | `sha256:4bb3af69b0260166696c24d32274c4c36db8e4147abf1ead6611ce2896b91d14` |
| JAR dentro da imagem | `sha256:47f6c770f2e3ea1e549671848ec0d9cef743b3b21f721d25d3977e4c65d645a3` |
| Versão no JAR | `actionfinance.app.version=0.1.2` |
| SPA citada pela task | `index-B0699gCh.js` |
| Flyway efetivo | `ACTIONFINANCE_FLYWAY_ENABLED=false`. O default do JAR é `true`; a task desliga |

O JAR publicado contém V1–V20 e não contém V21–V23. O bundle `index-B0699gCh.js` tem cadastros, recebimentos e logout Cognito. A palavra “Extrato” nesse bundle é o extrato gerencial, não a rota `/financial-accounts/statement`.

## Histórico Flyway

Leitura de 15/10/2026, somente `version`, `checksum`, `success`, `type` e `script`, pelo papel que já podia ler o segredo do migrator. V1–V20 `success=true`. Nenhuma linha foi alterada.

O checksum Flyway 11 é o CRC32 das linhas em UTF-8, sem o fim de linha e sem o BOM. V1–V19 do RDS coincidem com esse cálculo sobre o texto recuperado. V1 também coincide com o valor histórico `1488219560`.

## Matriz V13–V20

O texto do Git é o do JAR com fins de linha LF. O JAR publicado está em CRLF. O algoritmo Flyway ignora essa diferença. O SHA-256 não ignora.

| Versão | Checksum no RDS | Checksum Flyway 11 | SHA-256 do arquivo no JAR | SHA-256 do blob Git |
|---|---|---|---|---|
| V13 | `728072343` | `728072343` | `0750833efbb7658e86963931b7fac4e7d1d0361311b403d2c7eddf0700d1a1ef` | `5134d267f09516685cb7a6aad1090ea15a2a2d5362eafdf7440f5e4a3a4184f6` |
| V14 | `109302982` | `109302982` | `57f1b7a95825f79eede251488d4d9e9448c5b042affc1705ff050e2b39b3fbee` | `49c87762567ebcdb428aeaf2b710dff87cd80f9c0dd2bbc7a0d1ca8b3d84c785` |
| V15 | `-1691782262` | `-1691782262` | `34c9816e7b3cdccae07ed3045112ec4efd99b9c2666b6f29dbe5acd9d91ea19d` | `b64cf7ada11406a64a6ddec77955130775f80f987e78907aa5d0dab9ebffc2a5` |
| V16 | `-79702917` | `-79702917` | `7f8c1b4fc08704db35e9f5ad53f487461fe4a1c1df07711af67f577bdd2f3416` | `78dccbca8d8ce3cbca61f38f411e66e6cd4983ef90fe9658b9bdb32e5bcd4d63` |
| V17 | `798396481` | `798396481` | `bc6897f9ddb8eecdc25feda84f10db36eaf725e3c617178dea768cda789ebc0b` | `001649570f0a49847fc4aec5749cf9736d80e8f3009e380537cf7e0466a4e2fa` |
| V18 | `-582836574` | `-582836574` | `a936eb0b1aed78bc280c0d24d2883a7513dab86e967d236d952d9e243bdc5e09` | `1dff5bb859e6efaf9dee35e8456b1d68cb6c1022aec26ba73eac2fb8ab513838` |
| V19 | `716721883` | `716721883` | `a8276ed112ad4990b6163c493a6e607aeea0198080d1332b14fa441f5ef0a995` | `1cb4b4305873fb2529b961e729534c431898ea88fd93cc4976fd77b16fa6d580` |
| V20 | `-145522935` | `-1282662839` | `5589c6ddec3cad6d468f32453f9d30fe076f97deaed90a8367831fe99079e6a3` | `b581f93083bbe63ff14fc8bbecdbfc9495ee75e63929a4d606fe27c74cdfe6a2` |

V20: o valor gravado no RDS é o CRC32 dos bytes CRLF do JAR. O mesmo arquivo nas imagens `production-spider-20261014`, `receipt-enrich-027` e `apresentacao-028` produz esse CRC e o checksum Flyway `-1282662839`. Não há um segundo script. A divergência é o tipo do número gravado na versão 20, aplicada fora do Flyway no relato 025.

Num banco isolado cuja história copia esse número, a candidata para em `Migration checksum mismatch for migration version 20`. Aplicado no banco: `-145522935`. Resolvido localmente: `-1282662839`.

## O que entrou da versão pública

O commit `3baf7a25` traz o código cujo comportamento está no JAR 0.1.2: diretório de clientes e fornecedores, logout Cognito, apresentação dos recebimentos, `receiptSyncSuspended` e o `PUT` de catálogos que a classe publicada já autoriza. Os 109 tipos públicos do JAR têm fonte nesse checkout.

Não entrou o CSV real, plano Terraform, dump, evidência de outra frente, nem alteração de Spider, Hub, Mercado Pago ou Cognito. O working tree do monorepo continua sujo fora desse recorte e não foi apagado.

## Candidata

Construída só do checkout `e160996f`.

| Peça | Valor |
|---|---|
| Tag local | `actionfinance:candidate-033` |
| Índice | `sha256:fcce948d9ba074b75af0352d1bb5a29c9f27e240e2c341039312a80318089256` |
| Manifesto da plataforma | `sha256:2e6ccb8fed8dd65f7b1547a1ef65cd8c0ff70b889454163b536f066183ecd31f` |
| JAR | `sha256:c242c6c7e6cdf8749b082ceb764320e1cfeaa1972688ee8e99a17c49ebd34338` |
| SPA | `index-DzYbnxZv.js` |
| Parser / perfis | `1` · `mp-account-money-csv-1` · `mp-settlement-v2-csv-1` |
| Schema mínimo | V23 |

## Ensaio V20 → V23

Postgres 17.6 isolado em `127.0.0.1:5442`. O JAR candidato aplicou 20 migrations com alvo V20 e validou as 23. A semente local deixou 14 títulos, 3 baixas, 7 movimentos, 5 cadastros, 3 contas e 0 recebimentos. O hash dos ids dos títulos foi `c95f38f7c349cfc3e51b7ff669e0664f`.

Sem o alvo, o mesmo processo aplicou V21–V23. Contagens e o hash dos títulos permaneceram. `statement_line` e `statement_occurrence` passaram a existir.

O JAR publicado 0.1.2, com Flyway desligado, subiu contra esse banco já em V23. `system/info` devolveu `version=0.1.2`. A versão instalada continuou 23. Títulos 14 e linhas de extrato 6. Voltar a imagem não desfaz o schema.

## Regressão e T1

No processo de demonstração, sem login humano no endereço público:

- Lista e detalhe de «Cliente Balcão» responderam 200.
- A página de recebimentos ActionHub Pay respondeu 200. A sincronização local está desligada, então a lista não recebe página nova.
- Navegação Contas → Extrato e o botão Sair devolveram a tela do token.
- `CognitoLogoutUrlsTest` e `DocumentNumbersTest` passaram. Isso não substitui um logout Cognito feito por uma pessoa.

A jornada sanitizada de 22 ocorrências imprimiu `journey-ok`. Antes e depois: títulos 14, baixas 3, movimentos 7. Depois: 6 eventos, 47 ocorrências, 36 em revisão e 11 consolidadas. O hash dos títulos não mudou. Os nove pares continuam em revisão, sem total integral.

## Pacote para a decisão de publicação

| Item | Conteúdo |
|---|---|
| Artefato | `actionfinance:candidate-033`, manifesto `sha256:2e6ccb8fed8dd65f7b1547a1ef65cd8c0ff70b889454163b536f066183ecd31f` |
| Migrations ainda não aplicadas no RDS | V21, V22 e V23 |
| Pré-requisito | O histórico público precisa aceitar o checksum Flyway 11 de V20, ou a migração precisa de uma decisão que esta rodada não executa |
| Modo | A task web permanece com Flyway desligado. A migração é passo separado, antes da imagem nova |
| Recuperação | Recolocar `actionfinance-web:16` / `sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec`. Isso não apaga V21–V23 nem linhas de extrato |
| Fora desta decisão | Publicar a imagem e importar o arquivo real |
