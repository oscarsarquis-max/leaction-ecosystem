"""Papéis e o que cada um pode fazer.

dono             tudo, inclusive usuários
operador         consulta e lança (estoque, produção); não administra usuários
somente_leitura  só consulta
"""

DONO = "dono"
OPERADOR = "operador"
SOMENTE_LEITURA = "somente_leitura"

PAPEIS = (DONO, OPERADOR, SOMENTE_LEITURA)

PERMISSOES: dict[str, frozenset[str]] = {
    "ver_hoje": frozenset({DONO, OPERADOR, SOMENTE_LEITURA}),
    "lancar": frozenset({DONO, OPERADOR}),
    "gerenciar_usuarios": frozenset({DONO}),
}


def pode(papel: str, acao: str) -> bool:
    return papel in PERMISSOES.get(acao, frozenset())


def permissoes_do_papel(papel: str) -> list[str]:
    return sorted(acao for acao, papeis in PERMISSOES.items() if papel in papeis)
