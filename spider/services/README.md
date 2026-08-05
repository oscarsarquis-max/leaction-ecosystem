# Serviços auxiliares

| Serviço | Porta | Papel |
|---------|-------|--------|
| `service-originador` | **8081** | Origem da intenção + `/api/callback` JWT |
| `service-legado-financeiro` | **8082** | Legado `POST /api/legado/processar` |
| `mock-sistema-cadastro` | 8091 | Stub legado antigo (opcional) |
| `mock-sistema-credito` | 8092 | Stub legado antigo (opcional) |

```powershell
cd service-legado-financeiro; npm install; npm start
cd service-originador; npm install; npm start
```

Teste rápido (com Spider em `:8080`):

```powershell
Invoke-RestMethod -Method POST http://localhost:8081/api/iniciar -ContentType 'application/json' -Body '{}'
```
