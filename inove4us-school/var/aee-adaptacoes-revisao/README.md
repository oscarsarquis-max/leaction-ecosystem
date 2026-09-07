# Revisão humana — Adaptações AEE × metodologia (prompt 79)

Status do lote: **pendente_revisao**. Não publicar no Editor até o Oscar aprovar.

## Arquivos

| Arquivo | Uso |
|---|---|
| `relatorio-revisao.html` | Abrir no navegador: original vs adaptado, filtro por condição |
| `relatorio-original-vs-adaptado.csv` | Planilha (`;`, UTF-8 BOM) para Excel |
| `lote.json` | Insumo do apply |
| `auditoria-org.json` | Customizações de escola encontradas (não tocadas) |

## Depois da aprovação

```powershell
cd C:\Projetos\inove4us-school
$env:PEI_LLM_STUB='0'
python scripts\aplicar-aee-metodologias-canonico.py --approve
```

Isso marca `school_aee_metodologias_canonico.status = aprovado`. O Editor passa a servir o card modificado. Catálogo das 39 e `school_aee_matrizes` permanecem intactos. Linhas em `school_aee_metodologias_org` que forem customização real **não** são alteradas.

## Regenerar (nova metodologia ou condição)

```powershell
$env:PEI_LLM_STUB='0'
$env:BEDROCK_MODEL_ID='us.anthropic.claude-sonnet-4-6'
python scripts\gerar-aee-metodologias-canonico.py --resume
python scripts\gerar-aee-metodologias-canonico.py --condicao "TEA" --limit 1
```

Prompt e regras: `backend/aee_metodologia_adaptacao.py`.
