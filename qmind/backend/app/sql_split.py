"""Split PostgreSQL scripts on ';' outside dollar-quotes, strings and comments."""

from __future__ import annotations


def split_sql_statements(script: str) -> list[str]:
    stmts: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(script)
    in_single = False
    in_line_comment = False
    in_block_comment = False
    dollar_tag: str | None = None

    while i < n:
        ch = script[i]
        nxt = script[i + 1] if i + 1 < n else ""

        if in_line_comment:
            buf.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            buf.append(ch)
            if ch == "*" and nxt == "/":
                buf.append("/")
                i += 2
                in_block_comment = False
                continue
            i += 1
            continue

        if dollar_tag is not None:
            if script.startswith(dollar_tag, i):
                buf.append(dollar_tag)
                i += len(dollar_tag)
                dollar_tag = None
                continue
            buf.append(ch)
            i += 1
            continue

        if in_single:
            buf.append(ch)
            if ch == "'" and nxt == "'":
                buf.append("'")
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue

        if ch == "-" and nxt == "-":
            in_line_comment = True
            buf.append(ch)
            i += 1
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            buf.append(ch)
            i += 1
            continue

        if ch == "'":
            in_single = True
            buf.append(ch)
            i += 1
            continue

        if ch == "$":
            j = i + 1
            while j < n and (script[j].isalnum() or script[j] == "_"):
                j += 1
            if j < n and script[j] == "$":
                tag = script[i : j + 1]
                dollar_tag = tag
                buf.append(tag)
                i = j + 1
                continue

        if ch == ";":
            stmt = "".join(buf).strip()
            if stmt and not all(
                line.strip().startswith("--") or not line.strip()
                for line in stmt.splitlines()
            ):
                stmts.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail and not all(
        line.strip().startswith("--") or not line.strip() for line in tail.splitlines()
    ):
        stmts.append(tail)
    return stmts
