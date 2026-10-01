# Evidência — apply público PRM_009 (01/10/2026)

Sem senhas, MFA ou tokens. Contagens e códigos HTTP apenas.

## Isolamento Hub

```
localhost:4001 af-public-test-padaria 200 count=4 test=True env=HOMOLOG
localhost:4001 loja-de-paes 200 count=0 test=True env=HOMOLOG
public_orders=15
isolated_orders=4
api.actionhub.com.br no_key 401
api.actionhub.com.br af-public-test-padaria 200 count=4
api.actionhub.com.br loja-de-paes 200 count=0
```

## Hosts

```
af_root=200
af_pay_page=200 text/html  (após actionfinance-web:3)
af_me=401
af_pay_api=401
af_system_info homolog=false receiptSync=true OIDC RECEIPT_SYNC
monitor_root=302 Cognito hosted UI
hub_apex_lookup=404
hub_api_lookup=401
hub_api_health=200
```

## Migração e identidades (CloudWatch `/actionfinance/migrate`)

```
tenant=1
company=1
mapping=1
membership=1
flyway=1,2,3,4,5,6,7,8,9,10,11,12
```

## Git / imagens

| Item | Valor |
|---|---|
| `c407591d` | conjunto inicial do pacote |
| `e2a45cc2` | satellite sandbox 1.4 + helpers Hub |
| `03d051c5` | SPA `/pay-receipts` |
| AF digest publicado | `sha256:ec0c62c59c7936365f8aab2aa284bf52f310bd3c62c9fb9dd688b34d6532dfbc` |
| Spider digest | `sha256:8709085a9f96daedbab22ce3b200b4c5d20a02c5998eb93077935239ab99569a` |
| Monitor invalidação | `IDLVYWUQDUVI8X1JEF63MXWM6U` Completed |
