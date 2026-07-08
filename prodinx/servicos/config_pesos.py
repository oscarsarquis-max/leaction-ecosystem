DIMENSOES_PADRAO = {
    "Satisfação": 0.25,
    "Performance": 0.25,
    "Atividade": 0.20,
    "Comunicação": 0.20,
    "Eficiência": 0.10,
}

CONFIG_PESOS_IAPS = {
    "pesos_niveis": {
        "Individual": 0.4,
        "Equipe": 0.6,
    },
    "pesos_dimensoes": {
        "Técnica": dict(DIMENSOES_PADRAO),
        "Gestão Técnica": dict(DIMENSOES_PADRAO),
        "Gerência Técnica": dict(DIMENSOES_PADRAO),
        "Gestão Geral": dict(DIMENSOES_PADRAO),
    },
    "pesos_dimensoes_subpapel": {},
    "pesos_niveis_subpapel": {},
}

MAPA_GRUPO_PARA_PAPEL = {
    "Técnica": "Técnica",
    "Gerência Técnica": "Gestão Técnica",
    "Gestão Geral": "Gestão Geral",
}


def normalizar_papel(papel: str | None) -> str | None:
    if not papel:
        return None

    valor = str(papel).strip()
    if valor in CONFIG_PESOS_IAPS["pesos_dimensoes"]:
        return valor

    return MAPA_GRUPO_PARA_PAPEL.get(valor, valor)


def map_nome_grupo_para_papel(nome_grupo: str | None) -> str | None:
    if not nome_grupo:
        return None

    return normalizar_papel(MAPA_GRUPO_PARA_PAPEL.get(nome_grupo, nome_grupo))


def resolver_pesos_niveis(papel: str | None = None, subpapel: str | None = None) -> dict:
    if subpapel and subpapel in CONFIG_PESOS_IAPS["pesos_niveis_subpapel"]:
        return CONFIG_PESOS_IAPS["pesos_niveis_subpapel"][subpapel]

    return CONFIG_PESOS_IAPS["pesos_niveis"]


def resolver_pesos_dimensoes(papel: str | None = None, subpapel: str | None = None) -> dict:
    papel_normalizado = normalizar_papel(papel)

    if subpapel and subpapel in CONFIG_PESOS_IAPS["pesos_dimensoes_subpapel"]:
        return CONFIG_PESOS_IAPS["pesos_dimensoes_subpapel"][subpapel]

    if papel_normalizado and papel_normalizado in CONFIG_PESOS_IAPS["pesos_dimensoes"]:
        return CONFIG_PESOS_IAPS["pesos_dimensoes"][papel_normalizado]

    return dict(DIMENSOES_PADRAO)


def indicador_aplica_ao_subpapel(
    subpapeis_aplicaveis: list[str] | None,
    subpapel: str | None,
) -> bool:
    if not subpapeis_aplicaveis:
        return True

    if not subpapel:
        return True

    return subpapel in subpapeis_aplicaveis
