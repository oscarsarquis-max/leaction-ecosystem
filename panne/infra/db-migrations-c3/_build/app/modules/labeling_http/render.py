"""HTML de conferência A4. Sem arte-final gráfica."""


def render_candidate(detail: dict) -> str:
    current = detail.get("current") or {}
    candidate = current.get("candidate") or {}
    nutrition = current.get("nutrition") or {}
    front = current.get("front_of_pack") or {}
    lines = "".join(
        f"<tr><td>{item.get('nutrient_code')}</td>"
        f"<td>{item.get('presented') or '—'}</td>"
        f"<td>{item.get('declared_per_serving') or '—'}</td>"
        f"<td>{item.get('daily_value_percent') or '—'}</td></tr>"
        for item in nutrition.get("lines") or []
    )
    ingredients = ", ".join(item.get("display_name") or "" for item in current.get("ingredients") or [])
    warnings = " ".join(item.get("statement") or "" for item in current.get("warnings") or [])
    mandatory = "".join(
        f"<li>{item.get('label')}: {item.get('value') or 'pendente'}</li>"
        for item in current.get("mandatory") or []
    )
    watermark = candidate.get("watermark") or "Proposta técnica para revisão"
    high = ", ".join(front.get("nutrients_high") or []) or "nenhum nutriente alto concluído"
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Candidato de rótulo</title>
<style>
@page {{ size: A4; margin: 14mm; }}
body {{ font-family: Georgia, serif; color: #3a3228; background: #f3ead8; }}
.sheet {{ background: #fff; padding: 16px; border: 1px solid #3a3228; position: relative; }}
.mark {{ position: absolute; inset: 30%; opacity: 0.12; font-size: 28px; transform: rotate(-18deg); text-align: center; }}
h1,h2 {{ font-family: Arial, sans-serif; }}
table {{ width: 100%; border-collapse: collapse; }}
td,th {{ border: 1px solid #3a3228; padding: 4px; }}
</style></head><body>
<article class="sheet">
<p class="mark">{watermark}</p>
<h1>{(candidate.get("payload") or {}).get("title") or "Produto sem denominação"}</h1>
<p>Candidato para conferência. Não é rótulo final nem declaração de conformidade.</p>
<h2>Tabela nutricional candidata</h2>
<table><thead><tr><th>Nutriente</th><th>100 g</th><th>Porção</th><th>%VD</th></tr></thead>
<tbody>{lines}</tbody></table>
<p>Porção: {nutrition.get("portion_g") or "—"} g. Medida caseira: {nutrition.get("household_measure") or "não confirmada"}.</p>
<h2>Lupa candidata</h2>
<p>Alto em: {high}. Conclusão da lupa: {front.get("magnifier_required")}.</p>
<h2>Ingredientes e advertências</h2>
<p>{ingredients or "lista pendente"}</p>
<p>{warnings or "advertências pendentes"}</p>
<h2>Informações obrigatórias</h2>
<ul>{mandatory}</ul>
<p>Versão {(current.get("version") or {}).get("version_number")} · hash {(current.get("version") or {}).get("content_hash")}</p>
</article></body></html>"""
