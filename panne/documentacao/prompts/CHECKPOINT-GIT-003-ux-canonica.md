# CHECKPOINT-GIT-003 — Versionar a direção UX canônica

Este é um checkpoint operacional de UX-001 e UX-002. Não autoriza implementação produtiva nem CURSOR-017.

## Base esperada

- Branch: `main`
- Upstream: `origin/main`
- HEAD: `7f5045772101217bc1ae1a92762e1797ebbd2c5f`
- Working tree contendo somente os artefatos legítimos de UX-001 e UX-002, além dos arquivos preexistentes conhecidos fora da Panne

## Objetivo

Versionar e enviar:

- laboratório visual;
- documentação;
- evidências;
- derivados autorizados dos logos;
- direção canônica Oficina + Atelier;
- handoff do CURSOR-017.

Comprovar que frontend produtivo, backend, API, banco e logos mestres permaneceram intactos.

## Restrições

- Não iniciar CURSOR-017.
- Não aplicar a direção ao frontend produtivo.
- Não alterar backend, API, banco, migrações ou dependências.
- Não acessar legado, serviços externos ou aplicações irmãs.
- Não fazer deploy, PR, tag ou release.
- Não usar push forçado, rebase ou reset destrutivo.
- Não limpar arquivos preexistentes.
- Não versionar `.env`, segredos, dados reais, caches ou builds.
