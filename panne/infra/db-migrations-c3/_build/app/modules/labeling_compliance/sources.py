"""Metadados oficiais. Orientação não vira obrigação."""

from datetime import date

OFFICIAL_SOURCES = (
    {
        "code": "rdc-429-2020",
        "title": "RDC nº 429/2020 — Rotulagem nutricional",
        "authority": "ANVISA/MS",
        "jurisdiction": "BR",
        "force": "in_force_act",
        "effective_from": date(2022, 10, 9).isoformat(),
        "accessed_at": "2026-08-23",
        "url": "https://bvs.saude.gov.br/bvs/saudelegis/anvisa/2020/RDC_429_2020_.pdf",
        "locator": "RDC 429/2020 arts. 18–22; Anexo XV via IN 75",
        "normative": True,
    },
    {
        "code": "in-75-2020",
        "title": "IN nº 75/2020 — Requisitos técnicos da rotulagem nutricional",
        "authority": "ANVISA/MS",
        "jurisdiction": "BR",
        "force": "in_force_act",
        "effective_from": date(2022, 10, 9).isoformat(),
        "accessed_at": "2026-08-23",
        "url": "https://anvisalegis.datalegis.net/action/ActionDatalegis.php?acao=abrirTextoAto&numeroAto=00000075&orgao=DC%2FANVISA%2FMS&tipo=INM&valorAno=2020",
        "locator": "IN 75/2020 Anexos I, V, VI e XV",
        "normative": True,
    },
    {
        "code": "rdc-727-2022",
        "title": "RDC nº 727/2022 — Rotulagem geral de alimentos",
        "authority": "ANVISA/MS",
        "jurisdiction": "BR",
        "force": "in_force_act",
        "effective_from": date(2022, 9, 1).isoformat(),
        "accessed_at": "2026-08-23",
        "url": "https://anvisalegis.datalegis.net/action/ActionDatalegis.php?acao=abrirTextoAto&numeroAto=00000727&orgao=RDC%2FDC%2FANVISA%2FMS&tipo=RDC&valorAno=2022",
        "locator": "RDC 727/2022 informações obrigatórias",
        "normative": True,
    },
    {
        "code": "lei-10674-2003",
        "title": "Lei nº 10.674/2003 — Declaração de glúten",
        "authority": "União",
        "jurisdiction": "BR",
        "force": "in_force_act",
        "effective_from": date(2003, 5, 19).isoformat(),
        "accessed_at": "2026-08-23",
        "url": "https://planalto.gov.br/ccivil_03/leis/2003/l10.674.htm",
        "locator": "Lei 10.674/2003 art. 1º",
        "normative": True,
    },
    {
        "code": "anvisa-noticia-2022-10-09",
        "title": "Anvisa — novas regras de rotulagem nutricional",
        "authority": "ANVISA",
        "jurisdiction": "BR",
        "force": "official_guidance",
        "effective_from": date(2022, 10, 9).isoformat(),
        "accessed_at": "2026-08-23",
        "url": "https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/2022/rotulagem-nutricional-novas-regras-entram-em-vigor-em-120-dias",
        "locator": "Tabela de limites da lupa",
        "normative": False,
    },
)


def official_sources() -> list[dict]:
    return [dict(row) for row in OFFICIAL_SOURCES]


def source_by_code(code: str) -> dict:
    match = next((row for row in OFFICIAL_SOURCES if row["code"] == code), None)
    if match is None:
        raise ValueError("fonte oficial inexistente")
    return dict(match)
