import os
import time
import sys
import traceback
from pathlib import Path
from dotenv import load_dotenv

# --- CONFIGURAÇÃO DE AMBIENTE AWS ECS vs LOCAL (PADRÃO MASTER) ---
if not os.getenv("DB_HOST"):
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database import LeactionCRUD
# Nota: Criaremos a classe ModuladorAgent no Passo 4 para encapsular o Bedrock
from ai_engine.agents.modulador_agent import LeActionModuladorAgent


def main():
    print("\n[START] Iniciando script modulador_worker.py...", flush=True)
    host_atual = os.getenv("DB_HOST")
    print(f"DEBUG MODULADOR: Host detectado pelo sistema: {host_atual}", flush=True)

    try:
        # Instancia o banco reutilizando sua classe global LeactionCRUD
        db_manager = LeactionCRUD(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            sslmode="prefer"
        )
        print("✅ [Modulador] Gerenciador de Banco instanciado com sucesso.")

        # Instancia o Agente Cognitivo acoplado ao gerenciador de banco
        agent = LeActionModuladorAgent(db_manager)
        print("✅ [Modulador] Agente Cognitivo Claude instanciado.")

    except Exception as e:
        print(f"🚨 ERRO NA INICIALIZAÇÃO DO MODULADOR: {str(e)}")
        traceback.print_exc()
        return

    print("\n🚀 [Worker Modulador] Motor de Auditoria pronto para o monitoramento assíncrono!")

    while True:
        conn = None
        try:
            conn = db_manager._connect_db()
            conn.autocommit = True  # Visibilidade imediata de updates concorrentes

            with conn.cursor() as cur:
                # 1. BUSCA UMA EVIDÊNCIA PENDENTE (Respeitando a capitalização da DDL)
                cur.execute("""
                            SELECT id_evid
                            FROM public.ctdi_evidencias
                            WHERE status_modulador = 'Pendente'
                            LIMIT 1
                            """)
                row = cur.fetchone()

                if row:
                    id_evid = row[0]
                    print(f"\n📦 [Modulador] Evidência identificada para avaliação. ID: {id_evid}...", flush=True)

                    # 2. ALTERA STATUS PARA EVITAR CONCORRÊNCIA NA NUVEM
                    cur.execute("""
                                UPDATE public.ctdi_evidencias
                                SET status_modulador = 'Processando'
                                WHERE id_evid = %s
                                """, (id_evid,))

                    # 3. DISPARA A ESTEIRA DO AGENTE (Fase de Coleta de Contexto + LLM)
                    # O método processar_evidenca vai rodar a query complexa e chamar o Bedrock
                    if agent.processar_evidencia(conn, id_evid):

                        # Se a análise cognitiva rodar e gravar com sucesso, altera o status final
                        cur.execute("""
                                    UPDATE public.ctdi_evidencias
                                    SET status_modulador = 'Avaliado'
                                    WHERE id_evid = %s
                                    """, (id_evid,))
                        print(f"✅ [SUCESSO MODULADOR] Evidência ID {id_evid} auditada com sucesso!", flush=True)
                    else:
                        # Se falhar (timeout AWS, erro de JSON parser etc), marca o erro na fila
                        cur.execute("""
                                    UPDATE public.ctdi_evidencias
                                    SET status_modulador = 'Erro_Modulador'
                                    WHERE id_evid = %s
                                    """, (id_evid,))
                        print(f"❌ [FALHA MODULADOR] Erro ao processar cognição da Evidência ID {id_evid}", flush=True)
                else:
                    # IDLE (Aguardando em silêncio no CloudWatch)
                    print(".", end="", flush=True)

            conn.close()  # Limpeza preventiva de sessão no PostgreSQL
            time.sleep(5)  # Polling de segurança controlado

        except Exception as e:
            if conn: conn.close()
            print(f"\n🚨 ERRO NO LOOP DO MODULADOR: {str(e)}", file=sys.stderr)
            traceback.print_exc()
            time.sleep(10)


if __name__ == "__main__":
    main()