# Ameaças e riscos residuais

- Cognito User Pool e app client ainda não existem neste ciclo. Sem recurso AWS real.
- Guardrail do Bedrock continua sem identificador.
- O papel `admin` local é superusuário com `BYPASSRLS` — apenas migração e testes de regressão.
- JWKS depende de disponibilidade da rede no verificador Cognito; sem cache a API autentica com 503.
- Bootstrap do primeiro proprietário é manual e administrativo; erro operacional pode vincular o `sub` errado.
- Múltiplos papéis por associação estão no ciclo 014 (`organization_membership_role`). Grupos do IdP continuam sem autorizar.
- Cabeçalhos do cliente nunca são verdade: só o token verificado e o contexto transacional.
- Análise da Panne não é certificado nem parecer jurídico (ciclo 009).
- `setuptools` no *build*: o alerta 79.0.1 é **CVE-2026-59890** / GHSA-h35f-9h28-mq5c, não o CVE-2025-47273. Piso elevado a `>=83`.
