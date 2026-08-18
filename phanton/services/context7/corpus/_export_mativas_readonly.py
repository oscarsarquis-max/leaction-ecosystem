"""Export read-only: problema_mativa + biblioteca_passos.json → corpus consolidado."""

from __future__ import annotations

import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
BIB_PATH = Path(r"C:\Projetos\MAtivas\database\biblioteca_passos.json")


def chave(s: str) -> str:
    texto = unicodedata.normalize("NFKD", s or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.strip().lower()


def chave_limpa(s: str) -> str:
    c = chave(s)
    c = re.sub(r"\s*\([^)]*\)\s*", " ", c)
    c = re.sub(r"\s+", " ", c).strip()
    return c


def fetch_metodologias() -> list[dict]:
    sql = (
        "SELECT COALESCE(json_agg(row_to_json(t) ORDER BY t.id), '[]'::json) FROM ("
        " SELECT id, metodologia, grupo, problemas_combinados, observacao_automatizacao,"
        " publico_preferencial, publico_complementar, modalidade_preferencial,"
        " modalidades_alternativas"
        " FROM problema_mativa"
        ") t;"
    )
    cmd = [
        "docker",
        "exec",
        "-e",
        f"PGPASSWORD={os.environ['DB_PASSWORD']}",
        "leaction_db",
        "psql",
        "-U",
        os.environ["DB_USER"],
        "-d",
        os.environ["DB_NAME"],
        "-At",
        "-c",
        sql,
    ]
    raw = subprocess.check_output(cmd, text=True, encoding="utf-8")
    return json.loads(raw.strip())


def match_passos(
    nome: str, bib: dict[str, list], bib_limpa: dict[str, list]
) -> tuple[list | None, str | None, str]:
    # Espelha MAtivas/biblioteca_passos.py — sem inventar conteúdo.
    c = chave(nome)
    cl = chave_limpa(nome)
    for cand in (c, cl):
        if cand in bib:
            return bib[cand], cand, "exact"
        if cand in bib_limpa:
            return bib_limpa[cand], cand, "exact_limpa"
    for k, passos in bib.items():
        if cl.startswith(k) or k.startswith(cl):
            return passos, k, "prefix"
        if len(cl) >= 8 and (k in cl or cl in k):
            return passos, k, "contains"
    return None, None, "missing"


def main() -> None:
    metodologias = fetch_metodologias()
    bib_raw = json.loads(BIB_PATH.read_text(encoding="utf-8"))
    bib = {chave(k): v for k, v in bib_raw.items() if isinstance(v, list)}
    bib_limpa = {
        chave_limpa(k): v for k, v in bib_raw.items() if isinstance(v, list)
    }

    out: list[dict] = []
    missing: list[str] = []
    for m in metodologias:
        passos, matched_key, how = match_passos(m.get("metodologia") or "", bib, bib_limpa)
        item = dict(m)
        if passos is None:
            item["passos"] = []
            item["_passos_match"] = {"status": "missing"}
            missing.append(m.get("metodologia") or "")
        else:
            enriched = []
            for i, p in enumerate(passos):
                step = {"ordem": i + 1}
                # Preserva campos originais do JSON exatamente.
                if isinstance(p, dict):
                    step.update(p)
                else:
                    step["valor"] = p
                enriched.append(step)
            item["passos"] = enriched
            item["_passos_match"] = {
                "status": how,
                "chave_json": matched_key,
                "n_passos": len(passos),
            }
        out.append(item)

    export = {
        "_meta": {
            "fonte_metodologias": (
                "Postgres leaction_db / database MAtivas / tabela problema_mativa"
            ),
            "fonte_passos": str(BIB_PATH).replace("\\", "/"),
            "n_metodologias": len(out),
            "n_com_passos": sum(1 for x in out if x["passos"]),
            "n_sem_passos": len(missing),
            "sem_passos": missing,
            "nota_ordem": (
                "Campo ordem nao existe no JSON fonte; derivado da ordem do array "
                "(1-based), igual biblioteca_passos.formatar_passos_para_prompt."
            ),
            "somente_leitura": True,
        },
        "metodologias": out,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "mativas_base_conhecimento.json"
    out_path.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    raw_path = OUT_DIR / "problema_mativa_raw.json"
    raw_path.write_text(json.dumps(metodologias, ensure_ascii=False, indent=2), encoding="utf-8")

    print("exported", out_path)
    print(
        "n=",
        len(out),
        "com_passos=",
        export["_meta"]["n_com_passos"],
        "sem=",
        missing,
    )
    for item in out:
        print(f"{item['id']:2d} | passos={len(item['passos']):2d} | {item['metodologia']}")


if __name__ == "__main__":
    main()
