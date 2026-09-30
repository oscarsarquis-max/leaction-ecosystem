# Ensaio HTTPS descartável (não é produção)

Este conjunto sobe Postgres, um IdP mock com TLS e o ActionFinance no perfil `production` atrás de Caddy. Portas e volume são próprios: `18443` (origem), `18444` (issuer), `15439` (Postgres só para `access-admin`).

## Pré-requisitos

1. Imagem local: `.\scripts\ops\build-production-image.ps1` (JAR compilado no host; a imagem não contém Maven nem credenciais).
2. Certificados de ensaio: `.\scripts\ops\generate-https-trial-certs.ps1` (CA e PKCS12 gitignorados).
3. Subida + bootstrap: `.\scripts\ops\run-https-trial.ps1`.

## Hostnames

O navegador de teste deve resolver `finance.trial.localhost` e `idp.trial.localhost` para `127.0.0.1` (Playwright usa `--host-resolver-rules`). Origem e issuer usam a mesma porta que o processo vê na rede Docker (`18443` / `18444`).

Senhas `runtime-change-me` / `migrator-change-me` vêm de `ops/compose/bootstrap-prod-like.sql` e existem só neste ensaio. Não as use como instrução de produção nem as copie para a imagem.
