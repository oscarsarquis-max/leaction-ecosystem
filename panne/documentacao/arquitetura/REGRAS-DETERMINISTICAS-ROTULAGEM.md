# Regras determinísticas

Estados: `pass`, `fail`, `insufficient_evidence`, `insufficient_context`, `manual_review_required`, `not_applicable`.

Cada achado registra regra, resultado, fato, esperado, encontrado, evidência, fonte, versão, localizador, data, explicação e ação. A soma dos achados não vira selo.

Operadores numéricos da lupa passam pelo motor `compliance.engine` (`gte` nos limites de sólido/semissólido).
