# CURSOR-027-C2D — Relatório de vulnerabilidades (imagem DO_NOT_RUN)

| Campo | Valor |
|---|---|
| Repositório | `panne/backend` |
| Tag | `db-bootstrap-027-c2-86374c3908f3` |
| Digest | `sha256:87d4cef31efb840834f842103997b3a50f455b4e434073567013075c5b5da65e` |
| Status | **`DO_NOT_RUN`** |
| Base | `python:3.12.8-slim-bookworm@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0` |
| Scan | COMPLETE |
| Contagens | CRITICAL **8**, HIGH 49, MEDIUM 45, LOW 6, UNDEFINED 2 |

## CRITICAL (8) — lista completa (paginada)

Pacotes presentes no **runtime OS** (camadas Debian bookworm da imagem slim). Versão corrigida: atualizar pacotes Debian / trocar tag base; **não** executar este digest.

| CVE | Pacote | Versão na imagem | CVSS3 | Runtime? |
|---|---|---|---|---|
| CVE-2026-33845 | gnutls28 | 3.7.9-2+deb12u3 | 9.1 | Sim (OS) |
| CVE-2026-42010 | gnutls28 | 3.7.9-2+deb12u3 | 9.8 | Sim (OS) |
| CVE-2026-31789 | openssl | 3.0.15-1~deb12u1 | 9.8 | Sim (OS) |
| CVE-2026-34182 | openssl | 3.0.15-1~deb12u1 | 9.1 | Sim (OS) |
| CVE-2025-15467 | openssl | 3.0.15-1~deb12u1 | 9.8 | Sim (OS) |
| CVE-2026-13221 | perl | 5.36.0-7+deb12u1 | 9.1 | Sim (OS) |
| CVE-2026-12087 | perl | 5.36.0-7+deb12u1 | 9.1 | Sim (OS) |
| CVE-2026-57433 | perl | 5.36.0-7+deb12u1 | 9.8 | Sim (OS) |

Fonte bruta: [`_c2-critical-findings.json`](_c2-critical-findings.json).

**Decisão:** CRITICAL > 0 **bloqueia** execução. Aceite de risco **não** autorizado.

## Controles fail-closed (parser)

Implementação: `panne/infra/db-bootstrap-c2/scan_gate.py`.

| Condição | Ação |
|---|---|
| Falha de consulta AWS | bloquear |
| JSON inválido / vazio | bloquear |
| Campo `imageScanStatus` ausente | bloquear |
| Scan IN_PROGRESS / não COMPLETE | bloquear |
| `CRITICAL > 0` | bloquear |
| `HIGH > 0` sem override documentado | bloquear |
| Resultado desconhecido | bloquear |

Testes: `python -m unittest test_scan_gate` — **10 OK**.
