# Segurança do banco demo

- Ambiente só `local`, `demo` ou `test`.
- Host só loopback / `host.docker.internal`.
- Nome exatamente `*_demo` ou `*_smoke`.
- Recusa explícita de `panne` e `production`.
- Credenciais só no ambiente do processo. Nada versionado.
- Sem senha local criada pelo seed.
- E-mails `.invalid`. Sem CPF/CNPJ.
- Dois tenants para RLS.
- Fake auth e gateway falso bloqueados em produção.
- Seed não desliga trigger, imutabilidade nem check.
- Smoke sem rede.
