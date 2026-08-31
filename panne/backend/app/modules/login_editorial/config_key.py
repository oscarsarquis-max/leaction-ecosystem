"""Seleção determinística da config_key editorial (servidor apenas)."""

from __future__ import annotations

ALLOWED_KEYS = frozenset({"panne-demo", "panne"})
PROD_ENVS = frozenset({"prod", "production"})


def resolve_login_editorial_config_key(
    *,
    env: str,
    override: str = "",
    allow_demo_override_in_prod: bool = False,
) -> str:
    """
    - PANNE_ENV=demo → panne-demo
    - produção → sempre `panne`, salvo override administrativo protegido
      (allow_demo_override_in_prod=True + override explícito) — documentado;
      default False impede panne-demo em produção.
    - local/test: override panne-demo|panne; senão panne-demo
    Nunca aceita key do navegador.
    """
    raw = (override or "").strip().lower()
    normalized = (env or "local").strip().lower()
    is_prod = normalized in PROD_ENVS

    if is_prod:
        if (
            allow_demo_override_in_prod
            and raw == "panne-demo"
        ):
            # Mecanismo administrativo explícito (homologação controlada em env prod).
            return "panne-demo"
        # Override inesperado panne-demo em produção é ignorado.
        return "panne"

    if raw in ALLOWED_KEYS:
        return raw
    if normalized == "demo":
        return "panne-demo"
    return "panne-demo"
