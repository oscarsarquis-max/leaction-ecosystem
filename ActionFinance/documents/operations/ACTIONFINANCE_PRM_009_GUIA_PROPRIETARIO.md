# Guia — acompanhar Recebimentos do Pay

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_PRM_009_GUIA_PROPRIETARIO |
| Data | 01/10/2026 |
| Versão | 0.4 |

Há dois recortes. O local já foi exercitado. O público é a condição de aceite do proprietário. A implantação está **executada**; o aceite só depois desta jornada no seu browser. Não envie senha, MFA nem tokens neste chat.

## A. Roteiro público (aceite do proprietário)

| Tela | URL |
|---|---|
| ActionFinance | https://actionfinance.actionhub.com.br |
| Recebimentos do Pay | https://actionfinance.actionhub.com.br/pay-receipts |
| Monitor Spider | https://monitor.spider.actionhub.com.br |

Empresa: **Padaria de teste público** (`af-public-test-padaria`, id `9c2e0a10-4f11-4b8a-9c2e-0a104f11000c`). Ambiente de listagem: **HOMOLOG**. **Não** use a Loja de Pães.

1. Abra o Finance no seu browser e entre com a sessão Cognito que já usa nesse host.
2. Troque para a empresa de teste e abra **Recebimentos do Pay**.
3. Clique **Sincronizar recebimentos**. Anote o identificador da execução e a hora.
4. Clique **Ver execução na Spider**. Depois do login do Monitor (grupo `spider-sandbox-operators`), deve abrir **essa** execução.
5. Confira os factos Finance → Spider → ActionHub Pay → retorno.
6. Volte ao Finance e confira os registos importados com a **mesma** execução.

O principal do Monitor após o Edge é `owner:sandbox`: recorte compartilhado do sandbox, não o seu sujeito Cognito individual. Sem sessão o Monitor redireciona ao login; não há console anónimo.

Relato técnico: [REV_009_EXECUCAO_PUBLICA](../reviews/ACTIONFINANCE_REV_009_EXECUCAO_PUBLICA.md).

## B. Homologação local (aceite parcial técnico) — já executado

| Tela | URL |
|---|---|
| ActionFinance | http://127.0.0.1:5179/ |
| Recebimentos do Pay | http://127.0.0.1:5179/pay-receipts |
| Monitor Spider | http://127.0.0.1:5180/ |
| Exemplo já sincronizado | http://127.0.0.1:5180/?q=afm-e01b453b-6c39-4056-b4ba-60c61f0c4447&execution=afm-e01b453b-6c39-4056-b4ba-60c61f0c4447 |

Empresa local: **Padaria Exemplo** (`HOMOLOG`). Esta correlação **não** prova o público.

## O que não misturar

| Isto | Não é |
|---|---|
| Hosts públicos | Prova localhost |
| Empresa de teste | Loja de Pães / dados reais |
| Importação | Baixa, saldo ou cobrança |
| Aprovado no Pay | Dinheiro disponível |
| Badge FORWARD no Monitor | Produção nem “AMBIENTE MOCK” |
| `owner:sandbox` | Identidade Cognito individual |
| Autorização de implantação | Aceite do resultado |
| PRM_007 (sessões no restore) | Resolvido por esta demonstração |
