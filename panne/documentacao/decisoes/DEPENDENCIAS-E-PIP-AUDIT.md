# Dependências e pip-audit

Ciclo: CURSOR-011. Scanner: `pip-audit` no venv de `panne/backend`. Sem valores de ambiente.

## Achado em 79.0.1

| Campo | Valor |
|---|---|
| Pacote | `setuptools` |
| Versão encontrada no venv | 79.0.1 |
| Identificadores | **PYSEC-2026-3447** = **CVE-2026-59890** = **GHSA-h35f-9h28-mq5c** |
| Severidade | CVSS 3.1 **6.1 (média)** |
| Intervalo afetado | `< 83.0.0` (inclui 79.0.1) |
| Correção | `setuptools >= 83.0.0` |
| Advisory | https://github.com/pypa/setuptools/security/advisories/GHSA-h35f-9h28-mq5c |

O defeito é bypass de exclusão do `MANIFEST.in` por normalização Unicode (NFC/NFD) ao gerar *sdist* em APFS/HFS+ (macOS). Não é falha de runtime da API FastAPI.

## O que este alerta **não** é

**Não é o CVE-2025-47273** (GHSA-5rjg-fvgr-3xxf, path traversal em `PackageIndex.download`). Esse advisory afeta setuptools **anteriores a 78.1.1**. A 79.0.1 já está fora desse intervalo. Atribuir o alerta do scanner ao CVE-2025-47273 seria incorreto.

## Classificação

| Hipótese | Conclusão |
|---|---|
| Vulnerabilidade real no pacote apontado | Sim, no *build* de sdist |
| Dependência de runtime da API | Não; `setuptools` é ferramenta de *build* |
| Scanner desatualizado | Não; o ID PYSEC-2026-3447 confere com OSV |
| Falso positivo | Não |

## Decisão

Elevar o piso do *build-system* da Panne para `setuptools>=83`. No venv desta estação, atualizar apenas `setuptools` para **84.0.0**. Não adicionar `setuptools` às dependências de runtime. Não alterar outras aplicações do workspace.

## Resultado do scanner após a correção

`pip-audit` no venv de `panne/backend` (setuptools **84.0.0**): **nenhuma vulnerabilidade conhecida**. O pacote local `panne 0.1.0` foi ignorado por não existir no PyPI. Nenhum alerta residual de CVE-2025-47273 nem de CVE-2026-59890.

A imagem oficial `python:3.12-slim-bookworm` traz `pip 25.0.1` (ferramenta do *container*, não dependência da Panne). Esse `pip` dispara vários PYSEC-2026-*; não entra em `pyproject.toml`. Na validação 3.12 o `pip` do container é elevado antes do scanner.
