import os
import time
import sys
import traceback
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database import LeactionCRUD
from ai_engine.gerar_diagnostico_ia import LeActionAIProcessor


def main():
    # TESTE SUPREMO: Se isso não aparecer, o script nem carregou as bibliotecas
    print("\n[START] Iniciando script worker.py...", flush=True)

    try:
        db_manager = LeactionCRUD(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            sslmode="prefer"
        )
        print("✅ Gerenciador de Banco instanciado.")

        processor = LeActionAIProcessor(db_manager)
        print("✅ Processador de IA instanciado.")

    except Exception as e:
        print(f"🚨 ERRO NA INICIALIZAÇÃO: {str(e)}")
        traceback.print_exc()
        return

    print("\n🚀 [Worker IA] Motor LeAction Iniciado e pronto para o loop!")

    while True:
        conn = None
        try:
            conn = db_manager._connect_db()
            # O PULO DO GATO: Garante que a transação veja dados novos do Flask
            conn.autocommit = True

            with conn.cursor() as cur:
                # 1. BUSCA MATURIDADES PENDENTES
                cur.execute("SELECT id_matu FROM ctdi_matu WHERE status_ia = 'PENDENTE' LIMIT 1")
                row = cur.fetchone()

                if row:
                    id_matu = row[0]
                    print(f"\n🤖 [IA] Processando ID: {id_matu}...", flush=True)

                    # 2. MARCA COMO EM PROCESSAMENTO
                    cur.execute("UPDATE ctdi_matu SET status_ia = 'PROCESSANDO' WHERE id_matu = %s", (id_matu,))

                    # 3. EXECUTA A INTELIGÊNCIA
                    if processor.processar_diagnostico(conn, id_matu):

                        # --- ATIVAÇÃO PÓS-GÊNESE ---
                        cur.execute("SELECT id_ctdi FROM ctdi_main WHERE id_matu = %s", (id_matu,))
                        id_ctdi_res = cur.fetchone()

                        if id_ctdi_res:
                            id_ctdi = id_ctdi_res[0]

                            # A. ATIVA O CICLO PRINCIPAL
                            cur.execute("UPDATE ctdi_main SET stat_ctdi = 'ativo' WHERE id_ctdi = %s", (id_ctdi,))

                            # B. ATIVA ONDA 1
                            cur.execute("""
                                        UPDATE ctdi_itera
                                        SET stat_itera = 'ativa'
                                        WHERE id_ctdi = %s
                                          AND id_itera =
                                              (SELECT id_itera FROM ctdi_itera WHERE id_ctdi = %s ORDER BY id_itera LIMIT 1)
                                        """, (id_ctdi, id_ctdi))

                            # C. ATIVA SPRINT 1
                            cur.execute("""
                                        UPDATE ctdi_sprn
                                        SET stat_sprn = 'ativa'
                                        WHERE id_itera =
                                              (SELECT id_itera FROM ctdi_itera WHERE id_ctdi = %s ORDER BY id_itera LIMIT 1)
                                          AND id_sprn = (
                                        SELECT id_sprn
                                        FROM ctdi_sprn
                                        WHERE id_itera = (SELECT id_itera FROM ctdi_itera WHERE id_ctdi = %s ORDER BY id_itera LIMIT 1)
                                        ORDER BY id_sprn LIMIT 1)
                                        """, (id_ctdi, id_ctdi))

                        # D. ATUALIZA PROJETO
                        cur.execute("""
                                    UPDATE ctdi_projetos
                                    SET fase_atual = 'Plano Estratégico Disponível (Onda 1)',
                                        status     = 'ATIVO'
                                    WHERE id_clie = (SELECT id_clie FROM ctdi_matu WHERE id_matu = %s)
                                    """, (id_matu,))

                        # E. CONCLUI
                        cur.execute("UPDATE ctdi_matu SET status_ia = 'CONCLUIDO' WHERE id_matu = %s", (id_matu,))
                        print(f"✅ [SUCESSO] ID {id_matu} finalizado!", flush=True)
                    else:
                        cur.execute("UPDATE ctdi_matu SET status_ia = 'ERRO_IA' WHERE id_matu = %s", (id_matu,))
                        print(f"❌ [FALHA] Erro no processamento do ID {id_matu}", flush=True)
                else:
                    # IDLE (ESPERA)
                    print(".", end="", flush=True)

            conn.close()  # Fecha a cada ciclo para limpar a sessão no Postgres
            time.sleep(5)

        except Exception as e:
            if conn: conn.close()
            print(f"\n🚨 ERRO NO LOOP: {str(e)}", file=sys.stderr)
            traceback.print_exc()
            time.sleep(10)


if __name__ == "__main__":
    main()