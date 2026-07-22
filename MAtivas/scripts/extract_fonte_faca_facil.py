"""Extrai do transcript a mensagem com o texto completo Faça Fácil."""
from __future__ import annotations

import json
from pathlib import Path

TRANSCRIPT = Path(
    r"C:\Users\Oscar Sarquis\.cursor\projects\c-Projetos\agent-transcripts"
    r"\c073fef1-7154-4535-8126-7795e76e0b6d\c073fef1-7154-4535-8126-7795e76e0b6d.jsonl"
)
OUT = Path(__file__).resolve().parents[1] / "database" / "fonte_faca_facil.txt"


def blob_from_obj(obj: dict) -> str:
    content = obj.get("content") or obj.get("text")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, str):
                parts.append(c)
            elif isinstance(c, dict):
                parts.append(str(c.get("text") or c.get("content") or ""))
        return "\n".join(parts)
    msg = obj.get("message")
    if isinstance(msg, dict):
        return blob_from_obj(msg)
    return ""


def main() -> None:
    best = ""
    for line in TRANSCRIPT.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        blob = blob_from_obj(obj)
        if (
            "Metodologias (cri)ativas" in blob
            and "Passo a passo" in blob
            and "Dog or Cat" in blob
            and len(blob) > len(best)
        ):
            best = blob
    if not best:
        raise SystemExit("fonte nao encontrada no transcript")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(best, encoding="utf-8")
    print(f"saved {OUT} chars={len(best)}")


if __name__ == "__main__":
    main()
