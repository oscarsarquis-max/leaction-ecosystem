# Revisão — temas BNCC (prompt 85)

Status: **pendente_revisao**. Abrir `relatorio-revisao.html` ou a planilha CSV.

Fonte oficial: [bncc-dev/bncc-dados](https://github.com/bncc-dev/bncc-dados) `dados-2026.07.1` (1.721 aprendizagens). Recorte: Escola Teste, 16 pares disciplina×ano, 539 temas.

O enunciado e o código da habilidade vêm só do import. O tema é rótulo extraído de campo oficial (objeto único ou unidade temática / competência específica). A ementa livre da escola não foi alterada.

Depois do OK do Oscar, no School:

```
python scripts/aplicar-bncc-temas-canonico.py --approve
```

Isso marca `school_bncc_temas_canonico.status = aprovado`. O seletor do Dia a Dia passa a oferecer esses temas **além** da ementa livre.
