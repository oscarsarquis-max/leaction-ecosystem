# CURSOR-011 — Descobrir o domínio de chão de fábrica e ordens de produção

## Estado

- Estado: aprovado para execução
- Executor: Cursor
- Dependência: CURSOR-010 aceito
- Próximo prompt: bloqueado até retorno e revisão (não executar CURSOR-012)

## Objetivo

Descoberta técnica e arquitetural do domínio de chão de fábrica da Panne: planejamento, ordens, bateladas, quadro digital, execução, ficha impressa, apontamentos, rastreabilidade e relatórios derivados.

Este ciclo **não** implementa o domínio, **não** cria migração e **não** abre frontend ou CRUD de produção.

## Princípios confirmados

1. Relatórios importam; o chão de fábrica é prioritário.
2. O legado não atende bem às ordens de produção.
3. Hoje imprime-se uma ficha com ingredientes nas proporções corretas.
4. A Panne deve melhorar o fluxo com quadro digital.
5. A ficha impressa permanece.
6. Digital e impresso representam a mesma ordem e fonte de verdade.
7. Custos, markup e preços são domínio separado.

## Regras absolutas

- somente `panne/`;
- sem FTP, sem linhas de negócio MySQL, sem escrita no legado;
- sem alteração de schema PostgreSQL e sem migração;
- sem frontend ou endpoints de produção;
- sem copiar tabelas, telas ou fluxos do legado;
- sem commit, push ou deploy;
- sem registrar credenciais ou valores de `.env`.

Únicas alterações de código ou dependência autorizadas: (1) provar/corrigir ausência de fallback silencioso de `PANNE_RUNTIME_DATABASE_URL` para `PANNE_DATABASE_URL`; (2) `pip-audit` com identificação exata do alerta de `setuptools` — não atribuir a CVE-2025-47273.

## Entregas

1. Pendências 010: runtime sem fallback; `pip-audit` documentado.
2. Matriz do estado atual (aproveitar / estender / separar / lacuna). `trial` não é ordem.
3. DDL legado somente metadados, se conexão segura existir; senão registrar limitação sem procurar credenciais.
4. Crítica preservar / repensar / descartar / criar. Sem portar DDL.
5. Fluxo `demanda → plano → ordem → batelada → pesagem → execução → apontamentos → conclusão → projeções`.
6. Modelo conceitual sem tabelas físicas.
7. Invariantes 1–16.
8. Máquinas de plano, ordem, batelada e etapa.
9. Arquitetura do quadro (sem implementar).
10. Ficha impressa e anti-obsolescência.
11. Relatórios como projeções.
12. Fronteira com custos.
13. Permissões e RLS futuras (sem alterar o esquema de papéis).
14. Contingência e offline (sem arquitetura offline definitiva).
15. Documentação em `panne/documentacao/` e atualização do `INDICE.md`.
16. Regressão completa; Python 3.12; head Alembic `0009_identity_authorization_rls`.

O texto integral do contrato é a mensagem de execução deste ciclo.
