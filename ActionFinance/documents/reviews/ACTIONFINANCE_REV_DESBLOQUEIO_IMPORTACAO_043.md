# ACTIONFINANCE_REV_DESBLOQUEIO_IMPORTACAO_043

Data: 15/10/2026. Produto **0.2.3**. A conta produtiva já cadastrada não foi recriada, o arquivo real não foi importado e nenhum dinheiro foi movimentado. Schema permanece V23. Aceite continua com o proprietário.

Não havia um Prompt 042 separado no repositório. O acabamento pedido junto com este recorte é a retirada do formulário técnico e o resumo compacto da conta.

## Causa

A versão pública 0.2.2, bundle `index-CbYwmC0n.js`, continha «Gravar vínculo» e «Referência no relatório». O código fazia o mesmo: com conta selecionada e sem vínculo, `StatementPage` mostrava os dois campos; `StatementService.preview` chamava `requireLink` antes de ler o arquivo. Escolher o arquivo respondia que a conta não estava identificada.

No detalhe, o topo dizia «Saldo não apurado» quando não havia saldo inicial. A lista de movimentos usava `coalesce(sum(signed_amount_minor), 0)`. Sem lançamento, os três indicadores e o saldo após cada linha iam para a tela como R$ 0,00. Ausência de saldo-base era apresentada como saldo zero.

## Fluxo e API

`POST /api/v1/statement-previews` lê o arquivo com a conta e a empresa autorizadas, sem exigir vínculo prévio. O parser e os limites de tamanho permanecem os mesmos.

| Situação | Resposta |
|---|---|
| Vínculo existe e confere com a identificação do arquivo | Prévia, pronta para a confirmação da importação |
| Não há vínculo e o arquivo traz uma identificação | `identityConfirmationRequired`. As linhas não vêm nessa resposta |
| A identificação diverge do vínculo | `identityMismatch`, sem gravar prévia e sem trocar o vínculo |
| O arquivo não traz identificação confiável | Prévia, com a declaração do operador já prevista na confirmação da importação |

`POST /api/v1/statement-previews/{id}/identify` grava o vínculo com a identificação extraída, o arquivo, o operador, a empresa, a conta e a data. A proveniência é montada no servidor. Confirmar a conta não importa o relatório. `confirm` recusa a prévia enquanto a identidade estiver pendente. Troca de empresa ou de conta descarta a leitura no navegador; o lote só é encontrado na empresa autorizada. A mesma identificação não é copiada para outra conta.

A abertura não pede referência nem procedência. O arquivo escolhido permanece na etapa de identificação; «Sim, é esta conta» abre a prévia sem nova seleção.

## Saldo desconhecido

Quando a conta não tem movimento de abertura, `previousBalanceMinor`, `periodEndBalanceMinor`, `currentBalanceMinor` e `balanceAfterMinor` vão nulos. A tela mostra «Não apurado» nos três indicadores e no saldo após o movimento. Entradas e saídas registradas continuam visíveis. Um saldo inicial informado como zero continua «0» e aparece como R$ 0,00. Nenhum zero foi gravado para esconder a ausência.

O bloco se chama «Movimentos registrados» e diz que é o livro gerencial, não a atividade no Mercado Pago. «Ver extrato» abre o extrato daquela conta. Renomear e inativar ficam em «Gerenciar conta».

## Capturas

Ensaio isolado, empresa Padaria Exemplo, conta criada na hora sem saldo inicial e sem vínculo. Fixture sanitizada de uma linha, identificação `mp-conta-043`. Não é o arquivo real.

| Captura | O que mostra |
|---|---|
| [sem vínculo, 1440](evidence/extrato-043/01-sem-vinculo-1440.png) | Conta Mercado Pago e Importar relatório, sem os campos técnicos |
| [identificação, 1440](evidence/extrato-043/02-identificacao-1440.png) | Pergunta da conta, instituição Mercado Pago, período e identificação encontrada |
| [prévia, 1440](evidence/extrato-043/03-previa-1440.png) | Prévia depois de «Sim, é esta conta», sem escolher o arquivo de novo |
| [saldo, 1440](evidence/extrato-043/04-saldo-1440.png) | Posição, saldo anterior, saldo final e saldo atual em «Não apurado» |
| [saldo, 390](evidence/extrato-043/05-saldo-390.png) | O mesmo detalhe. Largura de rolagem 390 |
| [prévia, 390](evidence/extrato-043/06-previa-390.png) | Prévia no celular |

## Testes

| Prova | Resultado |
|---|---|
| `StatementPage` e `App` | 37 testes aprovados |
| `StatementObservationIT` | 2 testes aprovados. Inclui leitura sem vínculo, recusa da importação antes da identidade, identificação, reenvio que não pede a pergunta de novo, divergência sem trocar o vínculo, saldo nulo com movimento e saldo zero conhecido |
| Clique isolado | importar, arquivo, identificação, confirmar conta, prévia. O arquivo não foi escolhido duas vezes |
| Host público autenticado | Não percorrido |

A confirmação da importação no ensaio de integração não foi executada sobre a conta nova, para não misturar linhas com o teste já existente. O clique parou na prévia, antes de «Importar este relatório».

## Publicação

Código `8a57ce44c6779c55a63eff9ed9d87065d0fe19c7`, branch `feat/actionfinance-extrato-032`.

| Peça | Valor |
|---|---|
| Versão | 0.2.3 |
| Task | `actionfinance-web:20` |
| Tag | `0.2.3`. A tag `web` do repositório é imutável e não foi sobrescrita |
| Índice OCI | `sha256:84565d8b0257de55ee8c0b0cd879110d33ff196c609afafcb6b056c476244580` |
| Imagem linux/amd64 | `sha256:1ade891cb053d3314601516ba97a50d036221559a5f90c493c6bdd4ec70fca1a` |
| JAR | `sha256:fca4a4ce5dfdd80e9a30169d1018d44b300be2d6752c031b0e0e1d4bf8da2c5d` |
| Bundle | `/assets/index-Dlf7Kh7L.js` |
| Flyway da task | `false` |
| Rollback | `actionfinance-web:19`, `sha256:98942e11efae9774fb5df8244fb830a26fa10a1ec968dc1b56c3fded07b69611`, produto 0.2.2, bundle `index-CbYwmC0n.js` |

Depois do rollout, `system/info` respondeu `version=0.2.3`, o shell do extrato serviu `index-Dlf7Kh7L.js`, health respondeu 200 e as linhas sem sessão responderam 401. O bundle servido não contém «Gravar vínculo». Isso não é a jornada autenticada e não é aceite do proprietário.
