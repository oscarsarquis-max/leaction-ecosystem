import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Vamos conectar no banco padrão 'postgres' para olhar ao redor
# (Mesmo que seu .env diga outro, vou forçar 'postgres' aqui)
DB_TO_CHECK = 'postgres'

print(f"🕵️ Conectando ao 'lobby' do servidor ({DB_TO_CHECK})...")

try:
    conn = psycopg2.connect(
        dbname=DB_TO_CHECK,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        sslmode="require"
    )

    cur = conn.cursor()

    # 1. LISTAR TODOS OS BANCOS DE DADOS
    print("\n🏢 BANCOS DE DADOS EXISTENTES NESTE SERVIDOR:")
    cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
    bancos = cur.fetchall()

    for (nome_banco,) in bancos:
        print(f"   -> 🗄️  {nome_banco}")

    # 2. VERIFICAR SE AS TABELAS ESTÃO NO 'postgres' (Onde estamos agora)
    print(f"\n🔎 Verificando tabelas dentro de '{DB_TO_CHECK}':")
    cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name LIKE 'ctdi_%'; -- Procura só as tabelas do seu sistema
                """)
    tabelas = cur.fetchall()

    if tabelas:
        print(f"   ✅ ACHEI! As tabelas estão AQUI no '{DB_TO_CHECK}':")
        for (t,) in tabelas:
            print(f"      • {t}")
        print("\n💡 SOLUÇÃO: Mude DB_NAME=postgres no seu .env!")
    else:
        print(f"   ❌ O banco '{DB_TO_CHECK}' também está vazio de tabelas 'ctdi'.")
        print("      -> Os dados devem estar em outro banco da lista acima.")

    conn.close()

except Exception as e:
    print(f"❌ Erro: {e}")