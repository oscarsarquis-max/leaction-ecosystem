import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

print(f"🔌 Conectando em {os.getenv('DB_NAME')} no {os.getenv('DB_HOST')}...")

try:
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        sslmode="require"
    )

    cur = conn.cursor()

    # Lista TODOS os esquemas e tabelas
    print("\n📋 LISTA DE TABELAS ENCONTRADAS:")
    print("-" * 50)
    cur.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                ORDER BY table_schema, table_name;
                """)

    rows = cur.fetchall()
    if not rows:
        print("❌ Nenhuma tabela encontrada! O banco parece vazio para este usuário.")
    else:
        for schema, table in rows:
            print(f"  • {schema}.{table}")

    conn.close()

except Exception as e:
    print(f"❌ Erro: {e}")