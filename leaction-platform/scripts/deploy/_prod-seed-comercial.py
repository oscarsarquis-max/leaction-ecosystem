#!/usr/bin/env python3
"""Apply CMS comercial_publico patch + seed (publicado + rascunho) on leaction_hub."""
from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

import psycopg2

TREE = {
    "avatar_name": "Comercial",
    "avatar_tagline": "Contratação e primeiros passos",
    "avatar_candidates": ["Comercial"],
    "root_id": "inicio",
    "nodes": {
        "inicio": {
            "message": "Olá! Posso ajudar na contratação — inove4us school, Inove4Us (professor) ou serviços do ActionHub. Escolha uma opção:",
            "options": [
                {"label": "Sou escola, quero conhecer o inove4us school", "next": "escola"},
                {"label": "Sou professor(a), quero conhecer o Inove4Us", "next": "professor"},
                {"label": "Quero saber sobre os serviços do Hub", "next": "hub"},
                {"label": "Quero falar direto com alguém", "href": "https://wa.me/5585999031861"},
            ],
        },
        "escola": {
            "message": "O inove4us school é a Torre de Controle da escola: governança, equipe, método e visão do que acontece em sala — sem misturar com o app do professor. Planos e checkout ficam na vitrine /ecossistema.",
            "options": [
                {"label": "Ver planos e contratar", "href": "/ecossistema"},
                {"label": "Falar no WhatsApp", "href": "https://wa.me/5585999031861"},
                {"label": "Voltar", "next": "inicio"},
            ],
        },
        "professor": {
            "message": "O Inove4Us é a ferramenta do professor (Mesa do Inovador): roteiro pronto, execução e diário no fluxo da aula — freemium para começar. Cadastro e acesso ficam em inove4us.com.br.",
            "options": [
                {"label": "Ir para o cadastro / acesso", "href": "https://inove4us.com.br/acesso"},
                {"label": "Falar no WhatsApp", "href": "https://wa.me/5585999031861"},
                {"label": "Voltar", "next": "inicio"},
            ],
        },
        "hub": {
            "message": "O ActionHub concentra marketplace B2B, planos, CMS e a ponte com os satélites do ecossistema. Para entender o que cabe na sua operação, o canal comercial é o WhatsApp.",
            "options": [
                {"label": "Conversar no WhatsApp", "href": "https://wa.me/5585999031861"},
                {"label": "Voltar", "next": "inicio"},
            ],
        },
    },
}


def main() -> None:
    env = {}
    for line in Path("/var/www/leaction-platform/.env").read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k] = v.strip().strip('"').strip("'")
    p = urllib.parse.urlparse(env["DATABASE_URL"])
    conn = psycopg2.connect(
        dbname=p.path.lstrip("/") or "leaction_hub",
        user=p.username,
        password=urllib.parse.unquote(p.password or ""),
        host=p.hostname,
        port=p.port or 5432,
        sslmode="require",
    )
    conn.autocommit = True
    patch = Path("/tmp/patch_cms_assistente_comercial_publico.sql").read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(patch)
        print("OK patch comercial_publico")
        for status in ("rascunho", "publicado"):
            cur.execute(
                """
                INSERT INTO cms_assistente_chat
                  (sistema_destino, status, tree, publicado_em, atualizado_em, atualizado_por)
                VALUES (%s, %s, %s::jsonb,
                        CASE WHEN %s = 'publicado' THEN NOW() ELSE NULL END,
                        NOW(), %s)
                ON CONFLICT (sistema_destino, status) DO UPDATE SET
                  tree = EXCLUDED.tree,
                  atualizado_em = NOW(),
                  atualizado_por = EXCLUDED.atualizado_por,
                  publicado_em = CASE
                    WHEN EXCLUDED.status = 'publicado' THEN NOW()
                    ELSE cms_assistente_chat.publicado_em
                  END
                """,
                ("comercial_publico", status, json.dumps(TREE, ensure_ascii=False), status, "seed-prod"),
            )
            print("OK upsert", status)
        cur.execute(
            "SELECT sistema_destino, status, publicado_em IS NOT NULL AS has_pub FROM cms_assistente_chat WHERE sistema_destino='comercial_publico' ORDER BY status"
        )
        print("verify", cur.fetchall())
    conn.close()


if __name__ == "__main__":
    main()
