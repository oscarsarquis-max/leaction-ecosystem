"""Crystal Ball — proveniência, what-if (shadow) e prévia preditiva.

Subsistema estritamente aditivo: lê runs oficiais; nunca escreve em
pipeline_runs / phase_executions.
"""

from __future__ import annotations

from services.crystal_ball import service as crystal_ball_service

__all__ = ["crystal_ball_service"]
