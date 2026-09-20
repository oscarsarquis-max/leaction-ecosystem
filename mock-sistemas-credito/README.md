# Mock de Sistemas de Crédito

Serviço independente, local, **TEST DOUBLE / ILLUSTRATIVE / MOCK_ONLY**. Representa um sistema executor da última coluna da imagem discutida, e não o Spider ou todo o processo de crédito.

Nesta fatia de teste, um único sistema lógico `credit-provider-mock` atende os passos 2–6 do plano demonstrativo. Isso é uma escolha explícita de teste, não uma afirmação de que todos os sistemas reais serão um único provider.

| Capability | Contrato local | Finalidade |
|---|---|---|
| `GET_CUSTOMER_PROFILE` | `credit-mock/0.2` | `WORKING_CAPITAL_ASSESSMENT` |
| `CHECK_CUSTOMER_REGISTRATION` | `credit-mock/0.2` | `WORKING_CAPITAL_ASSESSMENT` |
| `GET_CREDIT_PROFILE` | `credit-mock/0.2` | `WORKING_CAPITAL_ASSESSMENT` |
| `FIND_ELIGIBLE_PRODUCTS` | `credit-mock/0.2` | `WORKING_CAPITAL_ASSESSMENT` |
| `SIMULATE_WORKING_CAPITAL` | `credit-mock/0.1` | `WORKING_CAPITAL_SIMULATION` |

`credit-mock/0.1` do passo 6 permanece compatível. `credit-mock/0.2` é versão **local de teste** da avaliação; não publica contrato oficial de produção.

## Saúde versus prontidão da cadeia

`GET /health` identifica o processo e as capabilities suportadas. Continua com `integratedWithSpider: false` e `chainReadiness: determined_by_spider`. Esse indicador **não** prova integração: a prontidão da cadeia é determinada no Spider, que conhece registro, resolução e conectividade.

A afirmação histórica de que o mock “não está integrado ao Spider” descreve a primeira entrega isolada. Não apague essa evidência; ela é histórica. A prova ponta a ponta desta segunda entrega vive no SpiderBank/Monitor, não neste flag.

## Executar

Requer Node.js 20 ou superior. Não possui dependências externas. Shell suportado: Windows PowerShell 5.1+.

```powershell
$env:CREDIT_MOCK_CREDENTIAL = node -e "process.stdout.write(require('node:crypto').randomBytes(32).toString('hex'))"
$env:PORT = '8096'
npm start
```

Ou, com a credencial já no ambiente:

```powershell
.\scripts\start-local.ps1
.\scripts\check-health.ps1
```

O serviço escuta apenas em `127.0.0.1`. A credencial deve ter ao menos 16 caracteres. Verifique a porta 8096 antes de reutilizá-la.

## Verificar

```powershell
npm test
```

Exemplo do passo 6, com a mesma credencial do servidor:

```powershell
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8096/v1/provider/capabilities/SIMULATE_WORKING_CAPITAL/executions' -Headers @{'X-Credit-Mock-Credential' = $env:CREDIT_MOCK_CREDENTIAL} -ContentType 'application/json' -InFile 'examples/request.json'
```

## Contrato local

Veja [a especificação](documents/SPIDERBANK-MOCK-001.md), [o pedido 0.1](examples/request.json) e [o pedido 0.2](examples/assessment-request.json). Essas versões são deliberadamente locais: não são versões oficiais do Satellite Contract ou do Provider Contract do Spider.

O cliente/satélite não deve chamar este serviço diretamente. A chamada cabe ao Spider, após resolução governada.
