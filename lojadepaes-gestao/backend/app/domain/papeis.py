"""Papéis (por organização) e o que cada um pode fazer.

dono             tudo na organização, inclusive os usuários dela
operador         consulta e lança (entradas, ingredientes, ajustes, junções); não administra usuários
somente_leitura  só consulta

O `admin_plataforma` não é um papel: fica fora das organizações e não tem nenhuma destas permissões.
"""

DONO = "dono"
OPERADOR = "operador"
SOMENTE_LEITURA = "somente_leitura"

PAPEIS = (DONO, OPERADOR, SOMENTE_LEITURA)

PERMISSOES: dict[str, frozenset[str]] = {
    "ver_hoje": frozenset({DONO, OPERADOR, SOMENTE_LEITURA}),
    "ver_estoque": frozenset({DONO, OPERADOR, SOMENTE_LEITURA}),
    "lancar": frozenset({DONO, OPERADOR}),
    "ajustar": frozenset({DONO, OPERADOR}),
    "juntar": frozenset({DONO, OPERADOR}),
    "gerenciar_usuarios": frozenset({DONO}),
}


def pode(papel: str | None, acao: str) -> bool:
    return papel is not None and papel in PERMISSOES.get(acao, frozenset())


def permissoes_do_papel(papel: str | None) -> list[str]:
    if papel is None:
        return []
    return sorted(acao for acao, papeis in PERMISSOES.items() if papel in papeis)
