# Evidência — complemento INC_001 (01/10/2026)

Sem code/state de callback, senhas ou tokens.

## AF — tentativas preservadas

```
run=b433dd29-5e69-4a1f-a60a-bb846f8515dc FAILED 21:51:32Z "A Spider não devolveu a listagem." imp=0 msg=none
run=9d147f2c-3774-4244-978d-31a5be4537c3 FAILED 21:50:05Z mesma mensagem
run=1396596a-7ce7-41fd-bb76-27599a9a64ad FAILED 21:49:34Z mesma mensagem
run=5092b7c9-66d5-4c11-8f35-ccfbd1ae230a FAILED 21:07:20Z transporte 403
txn=0
flyway=1,2,3,4,5,6,7,8,9,10,11,12
```

## Hub publicado

```
antes: POST api.actionhub.com.br/v1/provider/capabilities/LIST_PAYMENT_TRANSACTIONS/executions → 404 HTML Cannot POST
depois: mesmo POST sem key → 401 JSON
loopback POST com credencial: 200 COMPLETED count=4
ids=9c2e0a10-4f11-4b8a-9c2e-0a104f110101..0104
public_orders=15 isolated_orders=4
secret_sha12 coincidente Spider/Hub=13cd91b51f52
```

## Monitor Edge

```
:3 associado → 401 API com Set-Cookie a limpar __Host-SpiderSt
:4 Deployed → 401 API sem Set-Cookie; Cache-Control: no-store
callback sem código: 403 "inválido ou já foi usado" (esperado)
```
