"""Remove referências a Andrea Filatro no conteúdo de leaf_dime."""
from __future__ import annotations

import os
import re
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "LeAction_SysF" / ".env")

REPLACEMENTS = [
    (re.compile(r"\bProfa\.?\s*Filatro\b", re.I), "padrões de mercado"),
    (re.compile(r"\bProf\.?\s*Filatro\b", re.I), "padrões de mercado"),
    (re.compile(r"\bAndrea\s+Filatro\b", re.I), "padrões de mercado"),
    (re.compile(r"\babordagem\s+de\s+Andrea\s+Filatro\b", re.I), "padrões de mercado"),
    (re.compile(r"\babordagem\s+Filatro\b", re.I), "padrões de mercado"),
    (re.compile(r"\bFilatro\b", re.I), "padrões de mercado"),
    (re.compile(r"\bAndrea\b", re.I), "padrões de mercado"),
    (re.compile(r"\s{2,}"), " "),
    (re.compile(r"\s+([,.;])"), r"\1"),
]


def sanitize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value)
    original = text
    for pattern, repl in REPLACEMENTS:
        text = pattern.sub(repl, text)
    text = re.sub(r"\(\s*padrões de mercado\s*&\s*padrões de mercado\s*\)", "(padrões de mercado)", text, flags=re.I)
    text = re.sub(r"padrões de mercado\s+e\s+padrões de mercado", "padrões de mercado", text, flags=re.I)
    text = text.strip()
    return text if text != original.strip() else None


def main() -> None:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        dbname=os.getenv("DB_NAME", "LeAction_SysF"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", ""),
    )
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id_dime, name_dime, desc_dime, long_description
        FROM public.leaf_dime
        WHERE long_description ILIKE '%filatro%'
           OR long_description ILIKE '%andrea%'
           OR desc_dime ILIKE '%filatro%'
           OR desc_dime ILIKE '%andrea%'
           OR name_dime ILIKE '%filatro%'
           OR name_dime ILIKE '%andrea%'
        ORDER BY id_dime
        """
    )
    rows = cur.fetchall()
    print(f"Registros com referência: {len(rows)}")

    updated = 0
    for id_dime, name_dime, desc_dime, long_description in rows:
        new_desc = sanitize_text(desc_dime) or desc_dime
        new_long = sanitize_text(long_description) or long_description
        new_name = sanitize_text(name_dime) or name_dime

        if (new_desc, new_long, new_name) != (desc_dime, long_description, name_dime):
            cur.execute(
                """
                UPDATE public.leaf_dime
                SET desc_dime = %s, long_description = %s, name_dime = %s
                WHERE id_dime = %s
                """,
                (new_desc, new_long, new_name, id_dime),
            )
            updated += 1
            print(f"  atualizado id_dime={id_dime} ({name_dime})")

    conn.commit()

    cur.execute(
        """
        SELECT count(*) FROM public.leaf_dime
        WHERE long_description ILIKE '%filatro%'
           OR long_description ILIKE '%andrea%'
           OR desc_dime ILIKE '%filatro%'
           OR desc_dime ILIKE '%andrea%'
        """
    )
    remaining = cur.fetchone()[0]
    print(f"Atualizados: {updated} | Restantes: {remaining}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
