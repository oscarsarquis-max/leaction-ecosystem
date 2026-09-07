import os
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv("/var/www/inove4us-school/.env", override=False)
conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "inove4us_school"),
    user=os.getenv("DB_USER", "admin"),
    password=os.getenv("DB_PASS", ""),
    sslmode=os.getenv("DB_SSLMODE", "prefer"),
)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute(
    "SELECT COUNT(*) AS n FROM school_metodologias_catalogo WHERE ativo AND origem = 'padrao'"
)
print("catalogo", dict(cur.fetchone()))
cur.execute(
    "SELECT condicao_categoria, COUNT(*) AS n FROM school_aee_matrizes GROUP BY 1 ORDER BY 1"
)
print("matrizes", [dict(r) for r in cur.fetchall()])
cur.execute("SELECT COUNT(*) AS n FROM school_aee_metodologias_org")
print("org", dict(cur.fetchone()))
cur.execute(
    """
    SELECT m.condicao_categoria, COUNT(*) AS n,
           COUNT(*) FILTER (WHERE length(trim(org.passos_customizados)) > 0) AS nonempty
    FROM school_aee_metodologias_org org
    JOIN school_aee_matrizes m ON m.id = org.aee_matriz_id
    GROUP BY 1 ORDER BY 1
    """
)
print("org_por_condicao", [dict(r) for r in cur.fetchall()])
cur.execute(
    """
    SELECT m.instituicao_id::text AS instituicao_id, m.condicao_categoria,
           org.metodologia_nome, length(trim(org.passos_customizados)) AS nchars
    FROM school_aee_metodologias_org org
    JOIN school_aee_matrizes m ON m.id = org.aee_matriz_id
    WHERE length(trim(org.passos_customizados)) > 0
    ORDER BY 1, 2, 3
    LIMIT 80
    """
)
print("org_nao_vazios", [dict(r) for r in cur.fetchall()])
