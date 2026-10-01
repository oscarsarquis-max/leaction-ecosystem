# Guia — acompanhar Recebimentos do Pay

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_PRM_009_GUIA_PROPRIETARIO |
| Data | 01/10/2026 |
| Versão | 0.3 |

Há dois recortes. O local já foi exercitado. O público é a condição de aceite do proprietário. A implantação está **autorizada**; o aceite só depois da jornada nos hosts.

## A. Hosts públicos (aceite do proprietário)

| Tela | URL |
|---|---|
| ActionFinance | https://actionfinance.actionhub.com.br |
| Recebimentos do Pay | https://actionfinance.actionhub.com.br/pay-receipts |
| Monitor Spider | https://monitor.spider.actionhub.com.br |

Quando o pacote for aplicado e a jornada for validada, o roteiro será:

1. Entrar no Finance público com a sessão Cognito (login no próprio browser; não enviar senha neste chat).
2. Abrir a empresa **Padaria de teste público** (`af-public-test-padaria`, id `9c2e0a10-4f11-4b8a-9c2e-0a104f11000c`) — **não** a Loja de Pães — e **Sincronizar recebimentos**.
3. Anotar o identificador da execução e a hora.
4. Clicar **Ver execução na Spider**. Depois do login do Monitor, deve abrir **essa** execução.
5. Conferir os factos Finance → Spider → provider ActionHub Pay → retorno.
6. Voltar ao Finance e ver os registos importados com a mesma execução.

Até lá: o Finance público está no digest `7c4cc0de` (sem esta ecrã). O Monitor público pede Cognito e usa a engine de 28/09, sem o contrato 1.4. A listagem Pay pública responde 404.

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
| PRM_007 (sessões no restore) | Resolvido por esta demonstração |
