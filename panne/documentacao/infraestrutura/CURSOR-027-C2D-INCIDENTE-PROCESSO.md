# CURSOR-027-C2D — Incidente de processo (gate de scan)

## Resumo

Bootstrap C2 partiu com imagem contendo **8 CRITICAL** porque o gate de scan **não era fail-closed**: falha de parse PowerShell foi tratada como ruído em vez de bloqueio.

## Linha do tempo (sanitizada)

1. Build/push imagem `db-bootstrap-027-c2-86374c3908f3`.
2. ECR scan COMPLETE → CRITICAL=8.
3. Script de orquestração tentou ler/imprimir findings; encoding Windows (`charmap`) quebrou em caractere Unicode do relatório.
4. Fluxo **continuou** e registrou/iniciou task ECS `panne-db-bootstrap:1`.
5. Task: roles OK → `ProgrammingError` (autocommit) → exit 2.
6. C2D: deregister TD; parser fail-closed; **não** reexecutar imagem; fechar inbound/master.

## Causa raiz de processo

- Gate dependente de parse frágil (PowerShell + Unicode).
- Ausência de “qualquer falha = não executar”.
- Contagem CRITICAL não era condição hard-stop no caminho feliz.

## Correção de processo (aplicada em código auxiliar)

- `scan_gate.py` decide só com JSON estruturado e regras explícitas.
- Testes unitários cobrem critical, high, campos ausentes, JSON inválido, falha AWS, scan incompleto.
- **Não** usado para autorizar retry nesta passagem.

## Lições

1. Contagens de severidade vêm de `findingSeverityCounts` (paginação da lista de findings pode truncar nomes, não a contagem).
2. Imagem com CRITICAL nunca sobe task — mesmo one-shot.
3. Logs de exceção devem incluir tipo + mensagem sanitizada + sqlstate quando existir.
