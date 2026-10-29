# Chamelleon Bedrock — validação mínima (56B)

- API: `invoke_model` (não Converse)
- Região: `us-east-1`
- Modelo: `us.anthropic.claude-sonnet-4-20250514-v1:0`
- Chamada culinária: 4303 ms, tokens in/out 89/115, 276 chars
- Chamada fermentação/sova: 3971 ms, tokens in/out 88/220, 673 chars
- Sem dados de cliente, SES, pedido ou Pix.

Produção (identidade `lojadepaes-prod`, mesma conta): `invoke_model` ok após grant estreito de `bedrock:InvokeModel` no perfil/modelo acima. Chat público: ideia culinária com links reais da vitrine; fermentação vs sova; pedido LP sem token não autoriza. Flag `LOJADEPAES_GIGIO_ENABLED=true`.
