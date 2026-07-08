
from flask_mail import Message
from flask import Flask, request, jsonify, g, render_template, current_app, session
from flask_cors import CORS
import requests
import os
import psycopg2.errors
import sys
import traceback
import textwrap
import json
import uuid
from database import LeactionCRUD, generate_random_code
import boto3
import subprocess
import time
from datetime import datetime
from botocore.exceptions import ClientError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# --- ADICIONE ESTA LINHA OBRIGATÓRIA ---
app.secret_key = 'leaction_2026_desenvolvimento_seguro'
# ---------------------------------------
# CORS(app, resources={r"/api/*": {"origins": "http://localhost:3001"}})
CORS(app, supports_credentials=True)

# --- Configuração CORS Atualizada ---
CORS(app, resources={
    r"/api/*": {
        # Adicione os ports comuns de desenvolvimento e o domínio de produção
        "origins": [
            "http://localhost:3000",
            "http://localhost:3001",
            "https://paneldx.com.br"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# DB_CONFIG = {
#     # Lê as variáveis de ambiente injetadas pelo Fargate/Secrets Manager.
#     # Se a variável não for encontrada, ele usa o valor de fallback (aqui 'postgres' e '5432')
#     "dbname": os.environ.get("DB_NAME", "LeAction_SysF"), # Garante que o DB_NAME correto é usado
#     "user": os.environ.get("DB_USER", "postgres"),
#     "password": os.environ.get("DB_PASSWORD", "Cmgv6190!@"), # Não use fallback para senha, a injeção deve ser obrigatória
#     "host": os.environ.get("DB_HOST"), # <--- CORRIGIDO: Agora lê o DNS do RDS
#     "port": os.environ.get("DB_PORT", 5432),
#
#     # SOLUÇÃO CONDICIONAL: LÊ O VALOR DO ARQUIVO .ENV OU AWS
#     "sslmode": os.environ.get("DB_SSLMODE", "disable")
# }

# Busca os valores de ambiente
env_pass = os.environ.get("DB_PASSWORD") or os.environ.get("DB_PASS")

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "LeAction_SysF"),

    # Tenta USER (padrão local) ou USERNAME (padrão AWS/Fargate)
    "user": os.environ.get("DB_USER") or os.environ.get("DB_USERNAME") or "postgres",

    # Tenta PASSWORD ou PASS (o que você viu no JSON da Task Definition)
    # Sem o fallback "xxxx", ele é forçado a pegar a variável real
    # "password": os.environ.get("DB_PASSWORD") or os.environ.get("DB_PASS"),
    "password": env_pass if env_pass else "Cmgv6190!@",

    # Se estiver na AWS e não houver HOST, precisamos do IP da instância, não 127.0.0.1
    "host": os.environ.get("DB_HOST", "127.0.0.1"),

    "port": int(os.environ.get("DB_PORT", 5432)),
    "sslmode": os.environ.get("DB_SSLMODE", "disable")
}

db_manager = LeactionCRUD(**DB_CONFIG)

# =========================================================================
# REGISTRO DO SUBSISTEMA /INOVADOR (BLINDADO E ISOLADO)
# =========================================================================
# O bloco try/except garante blindagem total. Se houver erro de caminhos
# ou arquivos ausentes, o core do PanelDX ignora e não quebra o deploy.
try:
    from routes.inovador_routes import inovador_bp
    app.register_blueprint(inovador_bp, url_prefix='/inovador')
except Exception as e:
    print(f"⚠️ ALERTA: Subsistema /inovador não foi carregado: {e}", file=sys.stderr)

# Definição do valor máximo de timeout (3300 segundos = 55 minutos)
MAX_TIMEOUT_S = 3300

# --- Configuração do Microsserviço de Cálculo ---
CALC_MICROSERVICE_URL = os.environ.get("CALC_MICROSERVICE_URL", "http://localhost:5001")

# =========================================================================
# ROTAS FLASK
# =========================================================================

@app.route('/status', methods=['GET'])
def status_check():
    # Retorna o status 200 OK sem acessar o banco de dados
    return jsonify({"status": "running"}), 200

@app.route('/health', methods=['GET'])
def elb_health_check():
    """Rota simples para o Load Balancer verificar a integridade da aplicação."""
    return jsonify({"status": "healthy"}), 200

@app.teardown_request
def teardown_request_func(exception=None):
    pass


# --- HELPER PARA FILTRO EDUCACIONAL 21/01/2026---
def filter_education_answers(all_answers):
    """
    Filtra as respostas para o cálculo setorial de Educação.
    Critério: Questões da Dimensão LA (id_dime=4) OU Questões marcadas como 'EDUCACAO'.
    """
    education_subset = []
    for ans in all_answers:
        try:
            dime = int(ans.get('id_dime', 0))
        except:
            dime = 0

        # Garante que lê a string corretamente, removendo espaços e normalizando
        setor = str(ans.get('setor_ques', '')).strip().upper()

        if dime == 4 or setor == 'EDUCACAO':
            education_subset.append(ans)

    return education_subset

# NOVA ESTRATÉGIA DE CÁLCULO: 10/12/2025###########################################################
def calculate_scores(answers_list):
    """
    Agrega as respostas (do Presente OU do Futuro) e calcula a média por Domínio,
    Dimensão e o Score Geral.
    """
    respostas_por_dominio = {}
    respostas_por_dimensao = {}

    for answer in answers_list:
        grad_ques = answer.get('grad_ques')
        if grad_ques is not None and isinstance(grad_ques, (int, float)):
            respostas_por_dominio.setdefault(answer['id_doma'], []).append(grad_ques)
            respostas_por_dimensao.setdefault(answer['id_dime'], []).append(grad_ques)

    # Cálculo das médias por Domínio e Dimensão (dicionários)
    pdom_scores_dict = {str(d): round(sum(scores) / len(scores), 2) for d, scores in respostas_por_dominio.items() if
                        scores}
    pdim_scores_dict = {str(d): round(sum(scores) / len(scores), 2) for d, scores in respostas_por_dimensao.items() if
                        scores}

    # Cálculo da Média Final do Domínio e da Dimensão (para o Score Geral)
    pdom_matu_score_final_avg = sum(pdom_scores_dict.values()) / len(pdom_scores_dict) if pdom_scores_dict else 0.0
    pdim_matu_score_final_avg = sum(pdim_scores_dict.values()) / len(pdim_scores_dict) if pdim_scores_dict else 0.0

    # Cálculo do Score Geral (média das médias finais)
    pgen_matu_score = round((pdom_matu_score_final_avg + pdim_matu_score_final_avg) / 2, 2) if (
    pdom_matu_score_final_avg + pdim_matu_score_final_avg) > 0 else 0.0

    # Retorna (Scores_Dominio, Scores_Dimensao, Score_Geral)
    return pdom_scores_dict, pdim_scores_dict, pgen_matu_score
# FIM DA NOVA ESTRATÉGIA DE CÁLCULO: 10/12/2025####################################################

# --- Funções de Rota (Endpoints da API) ---
@app.route('/api/questions_by_dimension', methods=['GET'])
def get_questions_by_dimension():
    # 1. REMOÇÃO: A verificação db_manager.conn é obsoleta.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        # 2. MUDANÇA CRÍTICA: Passar 'conn' para o db_manager
        questions = db_manager.read_questions_structured_for_evaluation(conn)

        return jsonify(questions), 200
    except Exception as e:
        # O método chamado é de leitura, então não há necessidade de rollback.
        print(f"Erro ao obter questões estruturadas: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

@app.route('/api/bloc_derv', methods=['GET', 'POST'])
def handle_blocdervs():
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            search_query = request.args.get('search_query', '')

            # MUDANÇA CRÍTICA: Passar 'conn' para os métodos de LEITURA
            if search_query:
                records = db_manager.search_records(conn, 'bloc_derv', search_query)
            else:
                records = db_manager.read_all_records(conn, 'bloc_derv')

            return jsonify(records), 200

        elif request.method == 'POST':
            data = request.json

            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            new_id = db_manager.create_record(conn, 'bloc_derv', data)

            if new_id:
                return jsonify({"message": "Registro criado com sucesso!", "id": new_id}), 201
            return jsonify({"error": "Não foi possível criar o registro."}), 500

    except Exception as e:
        # Tratamento de erro unificado
        print(f"Erro ao processar blocdervs: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao processar dados: {str(e)}"}), 500

@app.route('/api/bloc_derv/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_blocderv(record_id):
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    if request.method == 'GET':
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de LEITURA
            record = db_manager.read_record_by_id(conn, 'bloc_derv', record_id)
            return jsonify(record), 200 if record else (jsonify({"error": "Registro não encontrado."}), 404)
        except Exception as e:
            print(f"Erro GET em handle_single_blocderv: {e}", file=sys.stderr)
            return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

    elif request.method == 'PUT':
        data = request.json
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            if db_manager.update_record(conn, 'bloc_derv', record_id, data):
                return jsonify({"message": "Registro atualizado com sucesso!"}), 200
            # update_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível atualizar o registro."}), 500
        except Exception as e:
            # Rollback no caso de erro não tratado pelo db_manager.update_record
            conn.rollback()
            print(f"Erro PUT em handle_single_blocderv: {e}", file=sys.stderr)
            return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500


    elif request.method == 'DELETE':
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            deleted = db_manager.delete_record(conn, 'bloc_derv', record_id)

            if deleted:
                return jsonify({"message": f"Registro {record_id} da tabela bloc_derv deletado com sucesso."}), 200
            else:
                return jsonify({
                    "error": f"Registro {record_id} da tabela blocderv não encontrado ou não pôde ser deletado."}), 404

        except psycopg2.errors.ForeignKeyViolation as e:
            # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
            conn.rollback()
            return jsonify({"error": "Não foi possível deletar o registro.",
                            "details": f"Violação de chave estrangeira: existem outros registros que dependem desta. Erro do DB: {e.pgerror}"}), 409

        except Exception as e:
            # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
            conn.rollback()
            return jsonify({"error": f"Erro interno do servidor ao deletar registro: {str(e)}"}), 500


@app.route('/api/ctdi_clie', methods=['GET', 'POST'])
def handle_clientes():
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            search_query = request.args.get('search_query', '')

            # 🎯 BURACO DE MINHOCA: Usamos um cursor nativo para garantir o SELECT * completo
            cursor = conn.cursor()

            if search_query:
                # Se houver busca, varre por nome ou email de forma relacional
                query = """
                        SELECT * \
                        FROM public.ctdi_clie
                        WHERE nome_clie ILIKE %s \
                           OR mail_clie ILIKE %s
                        ORDER BY id_clie DESC;
                        """
                cursor.execute(query, (f"%{search_query}%", f"%{search_query}%"))
            else:
                # Se não houver busca, traz todos os registros com mapeamento integral de colunas
                query = "SELECT * FROM public.ctdi_clie ORDER BY id_clie DESC;"
                cursor.execute(query)

            # Mapeia dinamicamente os nomes das colunas vindas do banco (Independente do db_manager)
            columns = [desc[0] for desc in cursor.description]
            records = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()

            # Print de auditoria para você ver no terminal se a role SOLO está subindo no GET
            print(f"📡 [GET LOG] Registros recuperados com colunas dinâmicas: {records[:1]}", file=sys.stderr)

            return jsonify(records), 200

        elif request.method == 'POST':
            import urllib.parse
            data = {}

            # 🧠 1. MOTOR DE CAPTURA INDESTRUTÍVEL MULTI-FORMATO
            if request.form:
                data = dict(request.form)
            elif request.get_data():
                raw_data = request.get_data(as_text=True)
                try:
                    data = request.get_json(force=True) or {}
                except Exception:
                    try:
                        data = dict(urllib.parse.parse_qsl(raw_data))
                    except Exception:
                        data = {}

            print(f"📥 [FLASK LOG DEFENSIVO] Payload processado com sucesso: {data}", file=sys.stderr)

            if not data:
                return jsonify({"error": "Aviso operacional: O payload de dados chegou vazio ao servidor."}), 400

            # 🚀 2. FILTRAGEM DE COLUNAS REAIS DA TABELA ctdi_clie
            # 🎯 CORREÇÃO: Incluídas as colunas de controle do perfil Inovador/Solo
            valid_columns = [
                'docu_clie', 'nome_clie', 'mail_clie', 'fone_clie', 'adre_clie',
                'zipn_clie', 'empresa_clie', 'tipo_ensino', 'qtd_alunos',
                'qtd_colaboradores', 'qtd_unidades', 'localizacao_sede',
                'rede_ensino', 'clima_organizacional', 'has_active_project',
                'init_role', 'justificativa_solo'  # 🌟 Adicionados aqui!
            ]

            clie_payload = {}
            for col in valid_columns:
                val = data.get(col) if data.get(col) is not None else data.get(col.upper())
                if val is not None:
                    clie_payload[col] = val

            # 🧠 3. TRAVAS INTELIGENTES DE INTEGRIDADE CONTRA CAMPOS NOT NULL
            # Captura a role para saber se aplica os fallbacks corporativos ou limpa para o Inovador
            current_role = clie_payload.get('init_role', 'GENERAL').strip().upper()

            if current_role == 'SOLO':
                # Se for Inovador Solo, garantimos que os campos corporativos fiquem limpos/nulos como na UI
                clie_payload['empresa_clie'] = "Autônomo / Inovador Solo"
                if not clie_payload.get('docu_clie'):
                    clie_payload['docu_clie'] = "00.000.000/0001-00" # Evita quebra de NOT NULL se houver constraint
            else:
                # Caso contrário (GENERAL), aplica os fallbacks corporativos originais
                if not clie_payload.get('docu_clie'):
                    clie_payload['docu_clie'] = "00.000.000/0001-00"
                if not clie_payload.get('empresa_clie'):
                    clie_payload['empresa_clie'] = "Da Vinci Sandbox (Solo)"

            # 💾 4. PERSISTÊNCIA NA PRIMEIRA TABELA (ctdi_clie)
            new_id = db_manager.create_record(conn, 'ctdi_clie', clie_payload)

            if new_id:
                # 🌟 [A CORREÇÃO CRÍTICA] 4.1. GERAÇÃO AUTOMÁTICA DO SLOT DE MATURIDADE (ctdi_matu)
                # Alinha a integridade relacional criando o registro que evita o 'id_matu' nulo no login
                matu_payload = {
                    "id_clie": new_id,
                    "status_ia": "AGUARDANDO CONTEXTO" if current_role == "GENERAL" else "SANDBOX",
                 }
                new_id_matu = db_manager.create_record(conn, 'ctdi_matu', matu_payload)
                print(f"🎲 [DB SETUP LOG] Slot inicial de maturidade gerado com sucesso! ID_MATU: {new_id_matu}", file=sys.stderr)

                # 🎲 5. GERAÇÃO DO CÓDIGO DE ACESSO COGNITIVO
                import random
                import string
                sufixo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                access_code = f"LA-{sufixo}"

                # 🔒 6. PERSISTÊNCIA NA SEGUNDA TABELA (ctdi_lead_access)
                access_payload = {
                    "id_clie": new_id,
                    "access_code": access_code
                }
                db_manager.create_record(conn, 'ctdi_lead_access', access_payload)

                # 📨 [INJEÇÃO DE CORREÇÃO] DISPARO REAL DO EMAIL VIA AWS SES
                destinatario = clie_payload.get('mail_clie')
                if destinatario:
                    try:
                        print(f"📧 [SES] Iniciando disparo de e-mail para {destinatario} com código {access_code}...",
                              file=sys.stderr)
                        email_enviado = send_report_email_ses(recipient=destinatario, access_code=access_code)
                        if not email_enviado:
                            print(
                                f"⚠️ [SES] A função retornou False. O e-mail não foi enviado, revise as credenciais AWS.",
                                file=sys.stderr)
                    except Exception as email_err:
                        # Tratamento defensivo: O erro do e-mail não deve travar a resposta HTTP do cadastro de sucesso
                        print(f"❌ [SES ERRO] Falha na execução da rotina de e-mail: {email_err}", file=sys.stderr)
                else:
                    print("⚠️ [SES] Disparo cancelado: 'mail_clie' não foi encontrado no payload.", file=sys.stderr)

                # ⚡ 7. RETORNO DE SUCESSO ESTRUTURADO PARA A UX DO FRONT
                mail_clie = clie_payload.get('mail_clie', 'informado')
                return jsonify({
                    "message": f"Sucesso! O código de acesso foi gerado para o perfil {current_role}. Verifique seu e-mail: {mail_clie}",
                    "id": new_id,
                    "id_matu": new_id_matu  # Vincula o ID de maturidade no retorno para auditorias de rede
                }), 201

            return jsonify({"error": "Não foi possível criar o registro na tabela ctdi_clie."}), 500

    except Exception as e:
        print(f"❌ Erro crítico ao processar clientes: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao processar dados: {str(e)}"}), 500
    

@app.route('/api/ctdi_clie/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_cliente(record_id):
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    if request.method == 'GET':
        try:
            record = db_manager.read_record_by_id(conn, 'ctdi_clie', record_id)
            return jsonify(record), 200 if record else (jsonify({"error": "Registro não encontrado."}), 404)
        except Exception as e:
            return jsonify({"error": f"Erro interno: {str(e)}"}), 500

    elif request.method == 'PUT':
        data = request.json
        try:
            # --- TRAVA DE SEGURANÇA (Opcional, mas recomendada) ---
            # Se você quiser garantir que nem via API o Lead sobrescreva dados já validados,
            # poderia buscar o record atual aqui e comparar.

            if db_manager.update_record(conn, 'ctdi_clie', record_id, data):
                return jsonify({"message": "Registro atualizado com sucesso!"}), 200
            return jsonify({"error": "Não foi possível atualizar."}), 500
        except Exception as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500

    elif request.method == 'DELETE':
        try:
            deleted = db_manager.delete_record(conn, 'ctdi_clie', record_id)
            if deleted:
                return jsonify({"message": "Deletado com sucesso."}), 200
            return jsonify({"error": "Não encontrado."}), 404
        except Exception as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500


# --- NOVO ENDPOINT EXCLUSIVO PARA O LEAD ATUALIZAR CONTEXTO ---
@app.route('/api/client/update-context', methods=['POST'])
def update_client_context():
    conn = None
    try:
        data = request.json
        id_clie = data.get('id_clie')

        conn = get_db_conn()
        cursor = conn.cursor()

        # 1. Atualiza os dados técnicos na ctdi_clie
        cursor.execute("""
                       UPDATE ctdi_clie
                       SET tipo_ensino          = %s,
                           qtd_alunos           = %s,
                           localizacao_sede     = %s,
                           rede_ensino          = %s,
                           qtd_colaboradores    = %s,
                           qtd_unidades         = %s,
                           clima_organizacional = %s
                       WHERE id_clie = %s
                       """, (data.get('tipo_ensino'), data.get('qtd_alunos'), data.get('localizacao_sede'),
                             data.get('rede_ensino'), data.get('qtd_colaboradores'), data.get('qtd_unidades'),
                             data.get('clima_organizacional'), id_clie))

        # 2. PROMOÇÃO DE ESTADO: ctdi_matu vai para CONTEXTO OK
        cursor.execute("""
                       UPDATE ctdi_matu
                       SET status_ia = 'CONTEXTO OK'
                       WHERE id_clie = %s
                       """, (id_clie,))

        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()


@app.route('/api/admin/clientes-search', methods=['GET'])
def admin_search_clientes():
    conn = None
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        term = request.args.get('term', '')
        search_term = f"%{term}%"

        # Query limpa sem as barras invertidas desnecessárias
        query = """
                SELECT DISTINCT ON (c.id_clie) 
                    c.id_clie, 
                    c.nome_clie, 
                    c.empresa_clie, 
                    c.docu_clie, 
                    c.mail_clie, 
                    c.fone_clie, 
                    c.adre_clie, 
                    c.zipn_clie, 
                    c.tipo_ensino, 
                    c.qtd_alunos, 
                    c.qtd_colaboradores, 
                    c.qtd_unidades, 
                    c.localizacao_sede, 
                    c.rede_ensino, 
                    c.clima_organizacional,
                    CASE WHEN p.status = 'ATIVO' THEN true ELSE false END as has_active
                FROM ctdi_clie c
                LEFT JOIN ctdi_projetos p ON c.id_clie = p.id_clie AND p.status = 'ATIVO'
                WHERE c.nome_clie ILIKE %s 
                   OR c.empresa_clie ILIKE %s 
                   OR c.docu_clie ILIKE %s
                ORDER BY c.id_clie DESC
                """

        cursor.execute(query, (search_term, search_term, search_term))
        results = cursor.fetchall()

        clientes = []
        for row in results:
            clientes.append({
                "id_clie": row[0],
                "nome_clie": row[1],
                "empresa_clie": row[2] or "",
                "docu_clie": row[3],
                "mail_clie": row[4],
                "fone_clie": row[5],
                "adre_clie": row[6],
                "zipn_clie": row[7],
                "tipo_ensino": row[8],
                "qtd_alunos": row[9],
                "qtd_colaboradores": row[10],
                "qtd_unidades": row[11],
                "localizacao_sede": row[12],
                "rede_ensino": row[13],
                "clima_organizacional": row[14],
                "hasActiveProject": row[15]
            })

        cursor.close()
        return jsonify(clientes), 200
    except Exception as e:
        print(f"ERRO NO SEARCH: {str(e)}") # Isso ajuda você a ver o erro real no terminal do Python
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/leaf_dime', methods=['GET', 'POST'])
@app.route('/api/leaf_dime/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_dimensoes(record_id=None):
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        # --- LEITURA (GET) ---
        if request.method == 'GET':
            if record_id:
                record = db_manager.read_record_by_id(conn, 'leaf_dime', record_id)
                return jsonify(record), 200 if record else (jsonify({"error": "Não encontrado"}), 404)

            search_query = request.args.get('search_query', '')
            # O db_manager agora deve retornar as novas colunas automaticamente se fizer SELECT *
            if search_query:
                records = db_manager.search_records(conn, 'leaf_dime', search_query)
            else:
                records = db_manager.read_all_records(conn, 'leaf_dime')
            return jsonify(records), 200

        # --- ATUALIZAÇÃO (PUT) ---
        elif request.method == 'PUT' and record_id:
            data = request.json

            # PROTEÇÃO: Impedimos a alteração do nome core no banco
            if 'name_dime' in data:
                del data['name_dime']

            # O db_manager.update_record monta o SQL dinamicamente com os campos enviados
            if db_manager.update_record(conn, 'leaf_dime', record_id, data):
                return jsonify({"message": "Estratégia atualizada com sucesso!"}), 200
            return jsonify({"error": "Não foi possível atualizar."}), 500

        # --- CRIAÇÃO (POST) ---
        elif request.method == 'POST':
            data = request.json
            # Normaliza a sigla para maiúsculas
            if 'code_dime' in data:
                data['code_dime'] = data['code_dime'].upper()

            new_id = db_manager.create_record(conn, 'leaf_dime', data)
            if new_id:
                return jsonify({"message": "Registro criado!", "id": new_id}), 201
            return jsonify({"error": "Erro ao criar registro."}), 500

        # --- EXCLUSÃO (DELETE) ---
        elif request.method == 'DELETE' and record_id:
            if db_manager.delete_record(conn, 'leaf_dime', record_id):
                return jsonify({"message": "Deletado com sucesso."}), 200
            return jsonify({"error": "Registro não encontrado."}), 404

    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro em leaf_dime: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500


@app.route('/api/leaf_dime/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_dimensao(record_id):
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    if request.method == 'GET':
        # ... (seu código GET original está ok) ...
        record = db_manager.read_record_by_id(conn, 'leaf_dime', record_id)
        return jsonify(record), 200 if record else (jsonify({"error": "Não encontrado"}), 404)

    elif request.method == 'PUT':
        data = request.json

        # --- A GRANDE MUDANÇA ESTÁ AQUI ---
        # 1. Blindagem: Removemos o name_dime para garantir que ele nunca mude
        if 'name_dime' in data:
            del data['name_dime']

        # 2. Padronização: Sigla sempre em maiúsculas
        if 'code_dime' in data:
            data['code_dime'] = data['code_dime'].upper()

        try:
            # O db_manager agora receberá o dicionário com 'long_description', etc.
            if db_manager.update_record(conn, 'leaf_dime', record_id, data):
                return jsonify({"message": "Estratégia atualizada com sucesso (Nome preservado)!"}), 200
            return jsonify({"error": "Não foi possível atualizar o registro."}), 500
        except Exception as e:
            if conn: conn.rollback()
            print(f"Erro PUT em handle_single_dimensao: {e}", file=sys.stderr)
            return jsonify({"error": str(e)}), 500

    elif request.method == 'DELETE':
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            deleted = db_manager.delete_record(conn, 'leaf_dime', record_id)

            if deleted:
                return jsonify({"message": f"Registro {record_id} da tabela leaf_dime deletado com sucesso."}), 200
            else:
                return jsonify({
                    "error": f"Registro {record_id} da tabela leaf_dime não encontrado ou não pôde ser deletado."}), 404

        except psycopg2.errors.ForeignKeyViolation as e:
            # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
            conn.rollback()
            return jsonify({"error": "Não foi possível deletar o registro.",
                            "details": f"Violação de chave estrangeira: existem outros registros que dependem desta. Erro do DB: {e.pgerror}"}), 409

        except Exception as e:
            # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
            conn.rollback()
            return jsonify({"error": f"Erro interno do servidor ao deletar registro: {str(e)}"}), 500

#Endpoins de Maturidades---------------------------------------------------------------------------------------------
@app.route('/api/ctdi_matu', methods=['GET', 'POST'])
def handle_maturidades():
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            search_query = request.args.get('search_query', '')

            # MUDANÇA CRÍTICA: Passar 'conn' para os métodos de LEITURA
            if search_query:
                records = db_manager.search_records(conn, 'ctdi_matu', search_query)
            else:
                records = db_manager.read_all_records(conn, 'ctdi_matu')

            return jsonify(records), 200

        elif request.method == 'POST':
            data = request.json
            id_clie = data.get('ID_CLIE')
            if not id_clie:
                return jsonify({"error": "ID_CLIE é obrigatório"}), 400

            try:
                # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
                new_id = db_manager.create_maturity_record(conn, id_clie)

                if new_id:
                    return jsonify({"message": "Maturidade criada com sucesso!", "id": new_id}), 201
                # create_maturity_record já faz o rollback em caso de falha interna
                return jsonify({"error": "Não foi possível criar o registro."}), 500

            except ValueError as e:
                # ValueError não causa transação, não precisa de rollback
                return jsonify({"error": str(e)}), 400

            except psycopg2.errors.ForeignKeyViolation as e:
                # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
                conn.rollback()
                return jsonify({"error": f"Violação de chave estrangeira: ID do cliente {id_clie} não existe."}), 400

            except Exception as e:
                # Rollback em caso de erro inesperado (se não for tratado internamente pelo db_manager)
                conn.rollback()
                return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500

    except Exception as e:
        # Tratamento de erro unificado para a rota
        print(f"Erro ao processar maturidades: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao processar dados: {str(e)}"}), 500


@app.route('/api/ctdi_matu/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_maturidade(record_id):
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    if request.method == 'GET':
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de LEITURA
            record = db_manager.read_record_by_id(conn, 'ctdi_matu', record_id)
            return jsonify(record), 200 if record else (jsonify({"error": "Registro não encontrado."}), 404)
        except Exception as e:
            print(f"Erro GET em handle_single_maturidade: {e}", file=sys.stderr)
            return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

    elif request.method == 'PUT':
        data = request.json
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            if db_manager.update_record(conn, 'ctdi_matu', record_id, data):
                return jsonify({"message": "Registro atualizado com sucesso!"}), 200
            # update_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível atualizar o registro."}), 500
        except Exception as e:
            # Rollback no caso de erro não tratado pelo db_manager.update_record
            conn.rollback()
            print(f"Erro PUT em handle_single_maturidade: {e}", file=sys.stderr)
            return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500


    elif request.method == 'DELETE':
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            deleted = db_manager.delete_record(conn, 'ctdi_matu', record_id)

            if deleted:
                return jsonify({"message": f"Registro {record_id} da tabela ctdi_matu deletado com sucesso."}), 200
            else:
                return jsonify({
                    "error": f"Registro {record_id} da tabela ctdi_matu não encontrado ou não pôde ser deletado."}), 404

        except psycopg2.errors.ForeignKeyViolation as e:
            # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
            conn.rollback()
            return jsonify({"error": "Não foi possível deletar o registro.",
                            "details": f"Violação de chave estrangeira: existem outros registros que dependem desta. Erro do DB: {e.pgerror}"}), 409

        except Exception as e:
            # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
            conn.rollback()
            return jsonify({"error": f"Erro interno do servidor ao deletar registro: {str(e)}"}), 500


# --- NOVA ROTA: CHECAGEM DE E-MAIL (O Porteiro) ---
@app.route('/api/check-email', methods=['POST'])
def check_email_type():
    data = request.json
    email = data.get('email', '').lower().strip()

    conn = get_db_conn()
    cursor = conn.cursor()

    try:
        # 1. Verifica EQUIPE (Prioridade)
        cursor.execute("SELECT id_team FROM ctdi_team WHERE email = %s AND ativo = true", (email,))
        if cursor.fetchone():
            return jsonify({"type": "TEAM", "message": "Digite sua senha de acesso."})

        # 2. Verifica LEADS/CLIENTES (Múltiplos IDs suportados)
        cursor.execute("SELECT id_clie FROM ctdi_clie WHERE mail_clie = %s", (email,))
        leads = cursor.fetchall()

        if leads:
            # Gera um candidato a código novo (só será usado se não existir um antigo)
            novo_codigo = generate_random_code(6)
            codigo_final = None

            try:
                for lead in leads:
                    id_clie = lead[0]

                    # --- A MUDANÇA MÁGICA: ON CONFLICT DO NOTHING ---
                    # Tenta inserir. Se já existir (conflito no ID), NÃO ATUALIZA. Mantém o velho.
                    cursor.execute("""
                                   INSERT INTO ctdi_lead_access (id_clie, access_code, created_at)
                                   VALUES (%s, %s, NOW()) ON CONFLICT (id_clie) DO NOTHING
                                   """, (id_clie, novo_codigo))

                    # Agora recuperamos o código REAL que ficou no banco (seja o velho ou o novo)
                    cursor.execute("SELECT access_code FROM ctdi_lead_access WHERE id_clie = %s", (id_clie,))
                    res = cursor.fetchone()
                    if res:
                        codigo_final = res[0]  # Pega o código para enviar por email

                conn.commit()
            except Exception as e_db:
                conn.rollback()
                print(f"Erro DB: {e_db}", file=sys.stderr)
                return jsonify({"error": "Erro ao processar credenciais."}), 500

            # Envia o código recuperado do banco
            if codigo_final:
                send_report_email_ses(email, codigo_final)
                return jsonify({"type": "LEAD", "message": "Código de acesso enviado/confirmado."})

        return jsonify({"error": "E-mail não encontrado."}), 404

    except Exception as e:
        print(f"Erro check-email: {e}", file=sys.stderr)
        return jsonify({"error": "Erro interno"}), 500
    finally:
        cursor.close()


@app.route('/api/login', methods=['POST'])
def login_unificado():
    print("\n--- INICIANDO LOGIN INTELIGENTE (Tabela ctdi_projetos) ---")

    try:
        conn = db_manager._connect_db()  # Ou get_db_conn(), use o que estiver configurado
    except Exception as e:
        return jsonify({"error": "Erro de conexão DB"}), 500

    data = request.json
    email = data.get('email', '').lower().strip()
    credential = data.get('credential')

    print(f"Tentativa de login para: {email}")

    cursor = conn.cursor()

    try:
        # ==================================================================
        # 1. TENTATIVA A: É UM ADMIN/TIME? (Mantido)
        # ==================================================================
        cursor.execute("SELECT id_team, nome, role, password_hash FROM ctdi_team WHERE email = %s AND ativo = true",
                       (email,))
        admin_user = cursor.fetchone()

        if admin_user:
            print(f"-> Email encontrado na tabela ADMIN.")
            db_hash = admin_user[3]

            # Valida senha (suporta hash ou texto puro para facilitar dev)
            senha_valida = False
            if db_hash and (db_hash.startswith('scrypt:') or db_hash.startswith('pbkdf2:')):
                from werkzeug.security import check_password_hash
                senha_valida = check_password_hash(db_hash, credential)
            else:
                senha_valida = (db_hash == credential)

            if senha_valida:
                return jsonify({
                    "success": True,
                    "redirect": "/admin",
                    "id_clie": admin_user[0],
                    "nome_clie": admin_user[1],
                    "role": admin_user[2],
                    "hasActiveProject": False
                })
            else:
                return jsonify({"error": "Senha incorreta."}), 401

        # ==================================================================
        # 2. TENTATIVA B: É UM CLIENTE/LEAD? (CORRIGIDO AQUI)
        # ==================================================================
        print("-> Procurando na tabela de CLIENTES...")

        # --- QUERY CORRIGIDA COM ctdi_projetos ---
        query_lead = """
                     SELECT c.id_clie,
                            c.nome_clie,
                            -- Subquery para verificar se tem projeto ativo
                            (SELECT fase_atual
                             FROM ctdi_projetos p
                             WHERE p.id_clie = c.id_clie
                               AND p.status = 'ATIVO'
                                LIMIT 1) as projeto_fase
                     FROM ctdi_clie c
                         JOIN ctdi_lead_access a
                     ON c.id_clie = a.id_clie
                     WHERE LOWER (c.mail_clie) = LOWER (%s)
                       AND UPPER (TRIM (a.access_code)) = UPPER (TRIM (%s))
                         LIMIT 1 \
                     """

        cursor.execute(query_lead, (email, credential))
        lead_user = cursor.fetchone()

        if lead_user:
            print(f"-> LEAD ENCONTRADO: {lead_user[1]}")

            id_clie = lead_user[0]
            nome_clie = lead_user[1]
            fase_proj = lead_user[2]  # Se vier texto aqui, tem projeto. Se vier None, não tem.

            # Define a flag para o Node.js
            has_active = True if fase_proj else False

            # Busca ID da Maturidade (para os links funcionarem)
            id_matu = None
            try:
                cursor.execute("SELECT id_matu FROM ctdi_matu WHERE id_clie = %s ORDER BY id_matu DESC LIMIT 1",
                               (id_clie,))
                res_matu = cursor.fetchone()
                if res_matu: id_matu = res_matu[0]
            except:
                pass

            return jsonify({
                "success": True,
                "redirect": "/projeto",
                "id_clie": id_clie,
                "nome_clie": nome_clie,
                "role": "LEAD",
                "hasActiveProject": has_active,  # Agora vai TRUE!
                "faseAtual": fase_proj or 'Diagnóstico Inicial',
                "id_matu": id_matu
            })

        print("-> FALHA: Credenciais inválidas.")
        return jsonify({"error": "E-mail ou código inválidos."}), 401

    except Exception as e:
        print(f"ERRO CRITICO LOGIN: {e}")
        return jsonify({"error": "Erro interno no servidor."}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ========================================================================================
# ROTA: ATIVAR/DESATIVAR PROJETO (A "CHAVE" DO ADMIN)
# ========================================================================================
@app.route('/api/admin/toggle-project', methods=['POST'])
def admin_toggle_project():
    conn = None
    try:
        data = request.json
        id_clie = data.get('id_clie')
        is_active = data.get('status')

        # A nossa Máquina de Estado
        novo_status = "PROJETO OK" if is_active else "AVALIACAO OK"

        conn = get_db_conn()
        cursor = conn.cursor()

        # 1. ATUALIZA A CTDI_CLIE (Apenas o booleano de ativação)
        cursor.execute("""
            UPDATE ctdi_clie 
            SET has_active_project = %s 
            WHERE id_clie = %s
        """, (is_active, id_clie))

        # 2. ATUALIZA A CTDI_MATU (Onde reside o status_ia)
        # Fazemos o JOIN ou subquery para encontrar a avaliação certa do cliente
        cursor.execute("""
            UPDATE ctdi_matu 
            SET status_ia = %s 
            WHERE id_clie = %s
        """, (novo_status, id_clie))

        # 3. SINCRONIZA COM A CTDI_PROJETOS
        status_str = 'ATIVO' if is_active else 'OFF'
        cursor.execute("""
            INSERT INTO ctdi_projetos (id_clie, status) 
            VALUES (%s, %s)
            ON CONFLICT (id_clie) 
            DO UPDATE SET status = EXCLUDED.status
        """, (id_clie, status_str))

        conn.commit()
        cursor.close()
        print(f">>> SUCESSO: Cliente {id_clie} sensibilizado em ctdi_matu como {novo_status}")
        return jsonify({"success": True}), 200

    except Exception as e:
        if conn: conn.rollback()
        print(f"ERRO REAL NO TOGGLE: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# ENDPOINT PARA ADMIN: Retorna todas as maturidades com nome do cliente
@app.route('/api/all_maturities', methods=['GET'])
def get_all_maturities():
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição. Se falhar, a exceção é levantada.
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        # Chama o método que busca todos os registros de maturidade, incluindo o nome do cliente
        # MUDANÇA CRÍTICA: Passar 'conn' para o método de LEITURA
        all_maturities = db_manager.read_all_maturities_with_client_name(conn)
        return jsonify(all_maturities), 200

    except Exception as e:
        # O método chamado é de leitura, não requer rollback.
        print(f"ERRO: Falha ao buscar todas as maturidades para admin: {e}", file=sys.stderr)
        return jsonify({"error": "Falha ao carregar a lista de avaliações."}), 500

#Endpoints de Movimentos -------------------------------------------------------------------------------------
@app.route('/api/ctdi_movi', methods=['GET', 'POST'])
def handle_movimentos():
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            search_query = request.args.get('search_query', '')

            # MUDANÇA CRÍTICA: Passar 'conn' para os métodos de LEITURA
            if search_query:
                records = db_manager.search_records(conn, 'ctdi_movi', search_query)
            else:
                records = db_manager.read_all_records(conn, 'ctdi_movi')

            return jsonify(records), 200

        elif request.method == 'POST':
            data = request.json

            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            new_id = db_manager.create_record(conn, 'ctdi_movi', data)

            if new_id:
                return jsonify({"message": "Registro criado com sucesso!", "id": new_id}), 201
            # create_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível criar o registro."}), 500

    except Exception as e:
        # Tratamento de erro unificado para GET e POST
        print(f"Erro ao processar movimentos: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao processar dados: {str(e)}"}), 500

@app.route('/api/ctdi_movi/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_movimento(record_id):
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500


    if request.method == 'GET':
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de LEITURA
            record = db_manager.read_record_by_id(conn, 'ctdi_movi', record_id)
            return jsonify(record), 200 if record else (jsonify({"error": "Registro não encontrado."}), 404)
        except Exception as e:
            print(f"Erro GET em handle_single_movimento: {e}", file=sys.stderr)
            return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

    elif request.method == 'PUT':
        data = request.json
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            if db_manager.update_record(conn, 'ctdi_movi', record_id, data):
                return jsonify({"message": "Registro atualizado com sucesso!"}), 200
            # update_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível atualizar o registro."}), 500
        except Exception as e:
            conn.rollback()
            print(f"Erro PUT em handle_single_movimento: {e}", file=sys.stderr)
            return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500


    elif request.method == 'DELETE':
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            deleted = db_manager.delete_record(conn, 'ctdi_movi', record_id)

            if deleted:
                return jsonify({"message": f"Registro {record_id} da tabela ctdi_movi deletado com sucesso."}), 200
            else:
                return jsonify({
                                   "error": f"Registro {record_id} da tabela ctdi_movi não encontrado ou não pôde ser deletado."}), 404

        except psycopg2.errors.ForeignKeyViolation as e:
            # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
            conn.rollback()
            return jsonify({"error": "Não foi possível deletar o registro.",
                            "details": f"Violação de chave estrangeira: existem outros registros que dependem desta. Erro do DB: {e.pgerror}"}), 409

        except Exception as e:
            # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
            conn.rollback()
            return jsonify({"error": f"Erro interno do servidor ao deletar registro: {str(e)}"}), 500

#Endpoints de Fases----------------------------------------------------------------------------

@app.route('/api/ctdi_phase', methods=['GET', 'POST'])
def handle_fases():
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            search_query = request.args.get('search_query', '')

            # MUDANÇA CRÍTICA: Passar 'conn' para os métodos de LEITURA
            if search_query:
                records = db_manager.search_records(conn, 'ctdi_phase', search_query)
            else:
                records = db_manager.read_all_records(conn, 'ctdi_phase')

            return jsonify(records), 200

        elif request.method == 'POST':
            data = request.json

            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            new_id = db_manager.create_record(conn, 'ctdi_phase', data)

            if new_id:
                return jsonify({"message": "Registro criado com sucesso!", "id": new_id}), 201
            # create_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível criar o registro."}), 500

    except Exception as e:
        # Tratamento de erro unificado para GET e POST
        print(f"Erro ao processar fases: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao processar dados: {str(e)}"}), 500


@app.route('/api/ctdi_phase/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_fase(record_id):
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500


    if request.method == 'GET':
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de LEITURA
            record = db_manager.read_record_by_id(conn, 'ctdi_phase', record_id)
            return jsonify(record), 200 if record else (jsonify({"error": "Registro não encontrado."}), 404)
        except Exception as e:
            print(f"Erro GET em handle_single_fase: {e}", file=sys.stderr)
            return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

    elif request.method == 'PUT':
        data = request.json
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            if db_manager.update_record(conn, 'ctdi_phase', record_id, data):
                return jsonify({"message": "Registro atualizado com sucesso!"}), 200
            # update_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível atualizar o registro."}), 500
        except Exception as e:
            conn.rollback()
            print(f"Erro PUT em handle_single_fase: {e}", file=sys.stderr)
            return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500


    elif request.method == 'DELETE':
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            deleted = db_manager.delete_record(conn, 'ctdi_phase', record_id)

            if deleted:
                return jsonify({"message": f"Registro {record_id} da tabela ctdi_phase deletado com sucesso."}), 200
            else:
                return jsonify({
                                   "error": f"Registro {record_id} da tabela ctdi_phase não encontrado ou não pôde ser deletado."}), 404
        except psycopg2.errors.ForeignKeyViolation as e:
            # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
            conn.rollback()
            return jsonify({"error": "Não foi possível deletar o registro.",
                            "details": f"Violação de chave estrangeira: existem outros registros que dependem desta. Erro do DB: {e.pgerror}"}), 409
        except Exception as e:
            # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
            conn.rollback()
            return jsonify({"error": f"Erro interno do servidor ao deletar registro: {str(e)}"}), 500

#Endpoins de Questões---------------------------------------------------------------------------------------------
@app.route('/api/ctdi_quest', methods=['GET', 'POST'])
def handle_questoes():
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            # Adaptamos para um JOIN para trazer os dados da Bússola e nomes das Dimensões/Domínios
            # Incluímos q.quali_ques, q.prefu_ques e q.setor_ques para o front-end
            sql = """
                  SELECT q.*, \
                         b.insight_chave, \
                         b.target_context, \
                         d.name_dime AS name_dime_text, \
                         m.name_doma AS name_doma_text
                  FROM public.ctdi_quest q
                           LEFT JOIN public.ctdi_bussola b ON q.id_ques = b.id_ques
                           LEFT JOIN public.leaf_dime d ON q.id_dime = d.id_dime
                           LEFT JOIN public.leaf_doma m ON q.id_doma = m.id_doma
                  ORDER BY q.id_ques ASC \
                  """
            # Usando o execute_query do db_manager para rodar o SQL customizado
            records = db_manager.execute_query(conn, sql)

            # EAGER LOADING: Se houver registros, buscamos as rubricas vinculadas em massa
            if records:
                ids_ques = tuple(r['id_ques'] for r in records)
                sql_rubr = "SELECT * FROM public.ctdi_rubricas WHERE id_ques IN %s ORDER BY grad_rubr ASC"
                all_rubrics = db_manager.execute_query(conn, sql_rubr, (ids_ques,))

                # Injetamos o array de rubricas dentro de cada questão correspondente
                for r in records:
                    r['rubricas'] = [rub for rub in all_rubrics if rub['id_ques'] == r['id_ques']]

            return jsonify(records), 200

        elif request.method == 'POST':
            data = request.json

            # Separamos os dados da Questão seguindo o DDL atualizado
            payload_quest = {
                "desc_ques": data.get("desc_ques"),
                "id_dime": data.get("id_dime"),
                "id_doma": data.get("id_doma"),
                "prefu_ques": data.get("prefu_ques", "P"),  # P ou F
                "setor_ques": data.get("setor_ques", "GERAL"),
                "presurvey_ques": data.get("presurvey_ques"),
                "quali_ques": data.get("quali_ques")  # Novo campo qualitativo
            }

            # 1. Cria a Questão
            new_id = db_manager.create_record(conn, 'ctdi_quest', payload_quest)

            if new_id:
                # 2. Cria a Bússola vinculada
                payload_bussola = {
                    "id_ques": new_id,
                    "insight_chave": data.get("insight_chave"),
                    "target_context": data.get("target_context")
                }
                db_manager.create_record(conn, 'ctdi_bussola', payload_bussola)

                # 3. Cria as Rubricas (Mecanismo de Resposta Fechada)
                rubricas = data.get("rubricas", [])
                for rb in rubricas:
                    # Só grava rubricas que tenham rótulo ou descrição
                    if rb.get('label_rubr') or rb.get('desc_rubr'):
                        payload_rb = {
                            "id_ques": new_id,
                            "grad_rubr": rb.get('grad_rubr'),
                            "label_rubr": rb.get('label_rubr'),
                            "desc_rubr": rb.get('desc_rubr')
                        }
                        db_manager.create_record(conn, 'ctdi_rubricas', payload_rb)

                conn.commit()
                return jsonify({"message": "Questão, Bússola e Rubricas criadas!", "id": new_id}), 201

            return jsonify({"error": "Não foi possível criar o registro."}), 500

    except Exception as e:
        conn.rollback()
        print(f"Erro ao processar questoes: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao processar dados: {str(e)}"}), 500


@app.route('/api/ctdi_quest/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_questao(record_id):
    # Primeiro Try: Garante a conexão
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    # Segundo Try: Processa a lógica de negócio
    try:
        # --- MÉTODO GET ---
        if request.method == 'GET':
            record = db_manager.read_record_by_id(conn, 'ctdi_quest', record_id)
            if record:
                sql_rubr = "SELECT * FROM public.ctdi_rubricas WHERE id_ques = %s ORDER BY grad_rubr ASC"
                record['rubricas'] = db_manager.execute_query(conn, sql_rubr, (record_id,))
                return jsonify(record), 200
            return jsonify({"error": "Registro não encontrado."}), 404

        # --- MÉTODO PUT ---
        elif request.method == 'PUT':
            data = request.json
            print(f">>> TENTANDO ATUALIZAR ID: {record_id}")

            payload_quest = {
                "desc_ques": data.get("desc_ques"),
                "id_dime": int(data.get("id_dime")),
                "id_doma": int(data.get("id_doma")),
                "prefu_ques": data.get("prefu_ques", "P"),
                "setor_ques": data.get("setor_ques", "GERAL"),
                "presurvey_ques": bool(data.get("presurvey_ques")),
                "quali_ques": data.get("quali_ques")
            }

            success = db_manager.update_record(conn, 'ctdi_quest', record_id, payload_quest)

            if success:
                # Sincronização de Rubricas (Delete-Insert)
                rubricas = data.get("rubricas", [])
                db_manager.execute_update(conn, "DELETE FROM public.ctdi_rubricas WHERE id_ques = %s", (record_id,))

                for rb in rubricas:
                    if rb.get('label_rubr') or rb.get('desc_rubr'):
                        payload_rb = {
                            "id_ques": record_id,
                            "grad_rubr": int(rb.get('grad_rubr')),
                            "label_rubr": rb.get('label_rubr'),
                            "desc_rubr": rb.get('desc_rubr')
                        }
                        db_manager.create_record(conn, 'ctdi_rubricas', payload_rb)

                # Sincronização da Bússola
                payload_bussola = {
                    "insight_chave": data.get("insight_chave", ""),
                    "target_context": data.get("target_context", "GERAL")
                }

                sql_check = "SELECT id_bussola FROM public.ctdi_bussola WHERE id_ques = %s"
                bussola_existente = db_manager.execute_query(conn, sql_check, (record_id,))

                if bussola_existente:
                    id_b = bussola_existente[0]['id_bussola']
                    db_manager.update_record(conn, 'ctdi_bussola', id_b, payload_bussola)
                else:
                    payload_bussola['id_ques'] = record_id
                    db_manager.create_record(conn, 'ctdi_bussola', payload_bussola)

                conn.commit()
                return jsonify({"message": "Questão, Rubricas e Bússola atualizadas com sucesso!"}), 200

            return jsonify({"error": "Falha ao atualizar ctdi_quest"}), 500

        # --- MÉTODO DELETE ---
        elif request.method == 'DELETE':
            print(f">>> [DELETE] Limpando dependências da Questão {record_id}...")
            # Limpeza manual para evitar erro de Foreign Key
            db_manager.execute_update(conn, "DELETE FROM public.ctdi_rubricas WHERE id_ques = %s", (record_id,))
            db_manager.execute_update(conn, "DELETE FROM public.ctdi_bussola WHERE id_ques = %s", (record_id,))

            deleted = db_manager.delete_record(conn, 'ctdi_quest', record_id)

            if deleted:
                conn.commit()
                return jsonify({"message": "Questão e todas as suas referências removidas!"}), 200
            return jsonify({"error": "Questão não encontrada no banco."}), 404

    except Exception as e:
        if conn: conn.rollback()
        print(f"Erro na rota /api/ctdi_quest/{record_id}: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

    # Finalização obrigatória: se chegar aqui, algo deu errado com o método HTTP
    finally:
        if conn: conn.close()

#Endpoins de Rodadas---------------------------------------------------------------------------------------------
@app.route('/api/ctdi_roun', methods=['GET', 'POST'])
def handle_rodadas():
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            search_query = request.args.get('search_query', '')

            # MUDANÇA CRÍTICA: Passar 'conn' para os métodos de LEITURA
            if search_query:
                records = db_manager.search_records(conn, 'ctdi_roun', search_query)
            else:
                records = db_manager.read_all_records(conn, 'ctdi_roun')

            return jsonify(records), 200

        elif request.method == 'POST':
            data = request.json

            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            new_id = db_manager.create_record(conn, 'ctdi_roun', data)

            if new_id:
                return jsonify({"message": "Registro criado com sucesso!", "id": new_id}), 201
            # create_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível criar o registro."}), 500

    except Exception as e:
        # Tratamento de erro unificado para GET e POST
        print(f"Erro ao processar rodadas: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao processar dados: {str(e)}"}), 500


@app.route('/api/ctdi_roun/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_rodada(record_id):
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de LEITURA
            record = db_manager.read_record_by_id(conn, 'ctdi_roun', record_id)
            return jsonify(record), 200 if record else (jsonify({"error": "Registro não encontrado."}), 404)

        elif request.method == 'PUT':
            data = request.json
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            if db_manager.update_record(conn, 'ctdi_roun', record_id, data):
                return jsonify({"message": "Registro atualizado com sucesso!"}), 200
            return jsonify({"error": "Não foi possível atualizar o registro."}), 500

        elif request.method == 'DELETE':
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            deleted = db_manager.delete_record(conn, 'ctdi_roun', record_id)
            if deleted:
                return jsonify({"message": f"Registro {record_id} da tabela ctdi_roun deletado com sucesso."}), 200
            else:
                return jsonify({
                    "error": f"Registro {record_id} da tabela ctdi_roun não encontrado ou não pôde ser deletado."}), 404

    except psycopg2.errors.ForeignKeyViolation as e:
        # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
        conn.rollback()
        return jsonify({"error": "Não foi possível deletar o registro.",
                        "details": f"Violação de chave estrangeira: existem outros registros que dependem desta. Erro do DB: {e.pgerror}"}), 409
    except Exception as e:
        # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
        conn.rollback()
        return jsonify({"error": f"Erro interno do servidor ao deletar registro: {str(e)}"}), 500

#Endpoins de Sprints---------------------------------------------------------------------------------------------
@app.route('/api/ctdi_sprn', methods=['GET', 'POST'])
def handle_sprints():
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            id_matu = request.args.get('id_matu')  # Captura o parâmetro que enviamos do JS
            search_query = request.args.get('search_query', '')

            if id_matu:
                # DEBUG para confirmar se o 71 está chegando aqui
                print(f" DEBUG SQL: Filtrando sprints para id_matu = {id_matu}")
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                query = """
                        SELECT s.*, \
                               b.name_bloc as name_bloc_text, \
                               i.id_itera
                        FROM ctdi_sprn s
                                 LEFT JOIN leaf_bloc b ON s.id_bloc = b.id_bloc
                                 INNER JOIN ctdi_itera i ON s.id_itera = i.id_itera
                                 INNER JOIN ctdi_main m ON i.id_ctdi = m.id_ctdi
                        WHERE m.id_matu = %s
                        ORDER BY i.id_itera ASC, \
                                 s.ordr_sprn ASC, \
                                 CASE \
                                     WHEN s.stat_sprn = 'em_andamento' THEN 1 \
                                     WHEN s.stat_sprn = 'planejada' THEN 2 \
                                     WHEN s.stat_sprn = 'concluida' THEN 3 \
                                     ELSE 4 \
                                     END
                        """

                cur.execute(query, (id_matu,))
                records = cur.fetchall()
                cur.close()
            elif search_query:
                records = db_manager.search_records(conn, 'ctdi_sprn', search_query)
            else:
                records = db_manager.read_all_records(conn, 'ctdi_sprn')

            return jsonify(records), 200

        elif request.method == 'POST':
            data = request.json

            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            new_id = db_manager.create_record(conn, 'ctdi_sprn', data)

            if new_id:
                return jsonify({"message": "Registro criado com sucesso!", "id": new_id}), 201
            # create_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível criar o registro."}), 500

    except Exception as e:
        # Tratamento de erro unificado para GET e POST
        print(f"Erro ao processar sprints: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao processar dados: {str(e)}"}), 500


@app.route('/api/ctdi_sprn/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_sprint(record_id):
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de LEITURA
            record = db_manager.read_record_by_id(conn, 'ctdi_sprn', record_id)
            return jsonify(record), 200 if record else (jsonify({"error": "Registro não encontrado."}), 404)

        elif request.method == 'PUT':
            data = request.json
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            if db_manager.update_record(conn, 'ctdi_sprn', record_id, data):
                return jsonify({"message": "Registro atualizado com sucesso!"}), 200
            return jsonify({"error": "Não foi possível atualizar o registro."}), 500

        elif request.method == 'DELETE':
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            deleted = db_manager.delete_record(conn, 'ctdi_sprn', record_id)
            if deleted:
                return jsonify({"message": f"Registro {record_id} da tabela ctdi_sprn deletado com sucesso."}), 200
            else:
                return jsonify({
                    "error": f"Registro {record_id} da tabela ctdi_sprn não encontrado ou não pôde ser deletado."}), 404

    except psycopg2.errors.ForeignKeyViolation as e:
        # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
        conn.rollback()
        return jsonify({"error": "Não foi possível deletar o registro.",
                        "details": f"Violação de chave estrangeira: existem outros registros que dependem desta. Erro do DB: {e.pgerror}"}), 409
    except Exception as e:
        # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
        conn.rollback()
        return jsonify({"error": f"Erro interno do servidor ao deletar registro: {str(e)}"}), 500


# Detalhamento das sprints com metadados do Framework (leaf_derv)
@app.route('/api/sprint_details/<int:id_sprn>', methods=['GET'])
def get_sprint_details(id_sprn):
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Join completo para trazer a inteligência do entregável baseada no bloco
        query = """
                SELECT s.*,
                       d.name_derv,
                       d.derv_defi,
                       d.derv_comp,
                       d.derv_metr,
                       d.criteria_dod,
                       d.desc_derv
                FROM ctdi_sprn s
                         LEFT JOIN leaf_derv d ON s.id_bloc = d.id_bloc
                WHERE s.id_sprn = %s \
                """
        cur.execute(query, (id_sprn,))
        sprint_data = cur.fetchone()
        cur.close()

        if sprint_data:
            return jsonify(sprint_data), 200
        return jsonify({"error": "Sprint não encontrada no repositório."}), 404
    except Exception as e:
        print(f"❌ Erro no Python (sprint_details): {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/ctdi_sprn/update-strategic', methods=['PUT'])
def update_sprint_strategic():
    # 1. Obter conexão
    conn = get_db_conn()

    try:
        data = request.json
        id_sprn = data.get('id_sprn')

        if not id_sprn:
            return jsonify({"error": "ID da sprint não fornecido"}), 400

        # 2. Montar o dicionário com os nomes exatos das colunas do seu banco
        # Usei psycopg2.extras.Json para o campo metrics_scores que é JSONB
        update_data = {
            "swot_type": data.get('swot_type'),
            "swot_justification": data.get('swot_justification'),
            "evidence_url": data.get('evidence_url'),
            "exec_notes": data.get('exec_notes'),
            "metrics_scores": psycopg2.extras.Json(data.get('metrics_scores', {})),
            "realv_sprn": data.get('realv_sprn'),
            "stat_sprn": data.get('status')
        }

        print(f"--- [DEBUG PYTHON] Atualizando Sprint {id_sprn} com dados estratégicos ---")

        # 3. Executar o update usando seu db_manager
        success = db_manager.update_record(conn, 'ctdi_sprn', id_sprn, update_data)

        if success:
            return jsonify({"success": True, "message": "Evolução gravada com sucesso!"}), 200
        else:
            return jsonify({"error": "Falha ao atualizar registro no banco."}), 500

    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO PYTHON (update-strategic): {str(e)}")
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()


# --- NOVOS ENDPOINTS PARA CERIMÔNIAS (RITOS) ---

@app.route('/api/cerimonias/<int:id_sprn>', methods=['GET'])
def get_cerimonias(id_sprn):
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Busca todas as cerimônias vinculadas à sprint, da mais nova para a mais antiga
        query = "SELECT * FROM ctdi_cermls WHERE id_sprn = %s ORDER BY dt_cermls DESC, id_cermls DESC"
        cur.execute(query, (id_sprn,))
        records = cur.fetchall()
        cur.close()

        return jsonify(records), 200
    except Exception as e:
        print(f"❌ Erro ao buscar cerimônias: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500

## Endpoints de cerimonias dentro as sprints 28/04/2026
@app.route('/api/cerimonias/registrar', methods=['POST'])
def registrar_cerimonia():
    try:
        conn = get_db_conn()
        data = request.json
        id_cermls = data.get('id_cermls') # Verifica se veio ID de edição

        insert_data = {
            "id_sprn": data.get('id_sprn'),
            "tp_cermls": data.get('tp_cermls'),
            "note_cermls": data.get('note_cermls'),
            "dt_cermls": data.get('dt_cermls')
        }

        if id_cermls:
            # LÓGICA DE UPDATE
            print(f"--- [UPDATE] Corrigindo Rito {id_cermls} ---")
            success = db_manager.update_record(conn, 'ctdi_cermls', id_cermls, insert_data)
        else:
            # LÓGICA DE INSERT (Original)
            print(f"--- [INSERT] Novo Rito para Sprint {insert_data['id_sprn']} ---")
            success = db_manager.create_record(conn, 'ctdi_cermls', insert_data)

        if success:
            return jsonify({"success": True}), 201
        return jsonify({"error": "Erro no banco"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Novo endpoint para buscar notas por maturidade--------------------------------------------------------------
@app.route('/api/ctdi_surv/by_maturity/<int:id_matu>', methods=['GET'])
def get_surveys_by_maturity(id_matu):
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        # MUDANÇA CRÍTICA: Passar 'conn' para o método de LEITURA
        surveys = db_manager.read_surveys_by_maturity(conn, id_matu)
        return jsonify(surveys), 200
    except Exception as e:
        # O método chamado é de leitura, não requer rollback.
        print(f"Erro ao obter notas para a maturidade {id_matu}: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500


#Endpoints de Questionários (Surveys)-------------------------------------------------------------------------
@app.route('/api/ctdi_surv', methods=['GET', 'POST'])
def handle_surveys():
    # ****************************************************************
    # FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    if request.method == 'GET':
        try:
            search_query = request.args.get('search_query', '')

            # Passar 'conn' para os métodos de LEITURA
            if search_query:
                records = db_manager.search_records(conn, 'ctdi_surv', search_query)
            else:
                records = db_manager.read_all_records(conn, 'ctdi_surv')

            return jsonify(records), 200

        except Exception as e:
            # Tratamento de erro para GET
            print(f"Erro ao processar surveys (GET): {e}", file=sys.stderr)
            return jsonify({"error": f"Erro interno ao buscar dados: {str(e)}"}), 500


    elif request.method == 'POST':
        # --- NOVO BLOCO TRY PARA CAPTURAR FALHAS DE JSON/PARSING/CONEXÃO ---
        try:
            # Garante que o JSON é lido corretamente
            data = request.json
            if data is None:
                print("ERRO: Requisição sem corpo JSON válido.", file=sys.stderr)
                return jsonify({"error": "Requisição inválida: O corpo deve ser JSON."}), 400

            # Extração dos dados do JSON
            id_matu_relacionado = data.get('id_matu')
            answers = data.get('answers')
            finalize_calculation = data.get('finalize', False)

            # --- Tenta obter a conexão (aqui o erro pode ser fatal se for um hook) ---
            conn = get_db_conn()

        except Exception as e:
            # Captura falhas se o JSON não puder ser lido (malformado)
            print(f"ERRO DE PARSING JSON/PAYLOAD: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return jsonify({"error": "Corpo da requisição malformado (JSON inválido)."}), 400
        # --------------------------------------------------------------------

        if not id_matu_relacionado or not answers:
            return jsonify({"error": "Dados incompletos para a pesquisa. 'id_matu' e 'answers' são obrigatórios."}), 400

        try:
            # 1. Prepara a lista de payloads para inserção em massa
            payloads = []
            for resposta in answers:

                payload_item = {
                    'ID_MATU': id_matu_relacionado,
                    'ID_QUES': resposta['id_ques'],
                    'ID_DIME': resposta['id_dime'],
                    'ID_DOMA': resposta['id_doma'],
                    'GRAD_QUES': resposta['grad_ques'],
                    'PREFU_QUES': resposta.get('prefu_ques')
                }

                payloads.append(payload_item)

            # MUDANÇA CRÍTICA: Passar 'conn' para o Bulk Insert (WRITE)
            # Isso insere as respostas (P ou F ou ambas) no DB.
            db_manager.create_multiple_survey_records(conn, payloads)

            # --- INÍCIO DA LÓGICA DE CÁLCULO SEPARADO (CONDICIONAL) ---

            if finalize_calculation:
                # 2. BUSCA DAS RESPOSTAS PARA CÁLCULO (Se 'finalize' for TRUE)
                # IMPORTANTE: db_manager.read_surveys_by_maturity deve retornar o campo 'setor_ques'
                answers_for_calc = db_manager.read_surveys_by_maturity(conn, id_matu_relacionado)

                if not answers_for_calc:
                    conn.rollback()
                    return jsonify({"error": "Finalização solicitada, mas sem respostas salvas para cálculo."}), 400

                # ==============================================================================
                # PARTE A: CÁLCULO GERAL (MANTIDO IGUAL AO ORIGINAL)
                # ==============================================================================

                # 3. SEGREGAÇÃO DAS RESPOSTAS (P e F)
                respostas_pres = [a for a in answers_for_calc if a.get('prefu_ques') == 'P']
                respostas_fut = [a for a in answers_for_calc if a.get('prefu_ques') == 'F']

                # NOVO CHECK: Garantir que ambas as seções tenham dados para um cálculo significativo
                if not respostas_pres or not respostas_fut:
                    conn.rollback()
                    return jsonify({
                                       "error": "Finalização solicitada, mas respostas do Presente e/ou Futuro estão incompletas."}), 400

                # 4. CALCULAR SCORES DE PRESENTE E FUTURO (GERAL)
                pdom_pres_scores, pdim_pres_scores, pgen_pres_score = calculate_scores(respostas_pres)
                pdom_fut_scores, pdim_fut_scores, pgen_fut_score = calculate_scores(respostas_fut)

                # 5. CALCULAR SCORES DE GAP (GERAL)

                # Cálculo do GAP de Domínio
                pdom_gap_scores = {}
                for id_doma, score_fut in pdom_fut_scores.items():
                    score_pres = pdom_pres_scores.get(id_doma, 0.0)
                    pdom_gap_scores[id_doma] = round(score_fut - score_pres, 2)

                # Cálculo do GAP de Dimensão
                pdim_gap_scores = {}
                for id_dime, score_fut in pdim_fut_scores.items():
                    score_pres = pdim_pres_scores.get(id_dime, 0.0)
                    pdim_gap_scores[id_dime] = round(score_fut - score_pres, 2)

                # Cálculo do GAP Geral
                pgen_gap_score = round(pgen_fut_score - pgen_pres_score, 2)

                # ==============================================================================
                # PARTE B: CÁLCULO SETORIAL - EDUCAÇÃO (NOVO)
                # ==============================================================================

                # 1. Filtra apenas o universo educacional (Dimensão LA + Questões 'EDUCACAO')
                # Nota: A função filter_education_answers deve estar definida no início do arquivo
                answers_sect = filter_education_answers(answers_for_calc)

                # 2. Segrega P e F do Setor
                answers_sect_pres = [a for a in answers_sect if a.get('prefu_ques') == 'P']
                answers_sect_fut = [a for a in answers_sect if a.get('prefu_ques') == 'F']

                # 3. Calcula Scores Setoriais (Reutiliza a função calculate_scores)
                # Mesmo que a lista esteja vazia, a função retorna 0.0/Vazio, o que é seguro.
                pdom_sect_pres, pdim_sect_pres, pgen_sect_pres = calculate_scores(answers_sect_pres)
                pdom_sect_fut, pdim_sect_fut, pgen_sect_fut = calculate_scores(answers_sect_fut)

                # 4. Calcula Gaps Setoriais

                # Gap Domínio (Setorial)
                pdom_sect_gap = {}
                for d_id, score_fut in pdom_sect_fut.items():
                    score_pres = pdom_sect_pres.get(d_id, 0.0)
                    pdom_sect_gap[d_id] = round(score_fut - score_pres, 2)

                # Gap Dimensão (Setorial)
                pdim_sect_gap = {}
                for d_id, score_fut in pdim_sect_fut.items():
                    score_pres = pdim_sect_pres.get(d_id, 0.0)
                    pdim_sect_gap[d_id] = round(score_fut - score_pres, 2)

                # Gap Geral (Setorial)
                pgen_sect_gap = round(pgen_sect_fut - pgen_sect_pres, 2)

                # ==============================================================================
                # PARTE C: PREPARAÇÃO E PERSISTÊNCIA (ATUALIZADO)
                # ==============================================================================

                # Serialização dos dicionários GERAIS
                pdom_pres_scores_str = json.dumps(pdom_pres_scores)
                pdim_pres_scores_str = json.dumps(pdim_pres_scores)
                pdom_fut_scores_str = json.dumps(pdom_fut_scores)
                pdim_fut_scores_str = json.dumps(pdim_fut_scores)
                pdom_gap_scores_str = json.dumps(pdom_gap_scores)
                pdim_gap_scores_str = json.dumps(pdim_gap_scores)

                # Serialização dos dicionários SETORIAIS (Novos)
                pdom_sect_pres_str = json.dumps(pdom_sect_pres)
                pdim_sect_pres_str = json.dumps(pdim_sect_pres)
                pdom_sect_fut_str = json.dumps(pdom_sect_fut)
                pdim_sect_fut_str = json.dumps(pdim_sect_fut)
                pdom_sect_gap_str = json.dumps(pdom_sect_gap)
                pdim_sect_gap_str = json.dumps(pdim_sect_gap)

                # MUDANÇA CRÍTICA: Atualizar ctdi_matu com todos os 18 scores
                success = db_manager.update_maturity_scores(
                    conn,
                    id_matu_relacionado,
                    # GERAL
                    pdom_pres_scores_str, pdim_pres_scores_str, pgen_pres_score,
                    pdom_fut_scores_str, pdim_fut_scores_str, pgen_fut_score,
                    pdom_gap_scores_str, pdim_gap_scores_str, pgen_gap_score,
                    # SETORIAL
                    pdom_sect_pres_str, pdim_sect_pres_str, pgen_sect_pres,
                    pdom_sect_fut_str, pdim_sect_fut_str, pgen_sect_fut,
                    pdom_sect_gap_str, pdim_sect_gap_str, pgen_sect_gap
                )

                if success:
                    # SUCESSO na FINALIZAÇÃO
                    return jsonify(
                        {
                            "message": "Respostas salvas e matriz de transformação (Geral + Educação) calculada com sucesso!"}), 201
                else:
                    conn.rollback()
                    return jsonify({"error": "Falha ao atualizar o banco de dados com os novos scores."}), 500

            else:
                # Se finalize = false: Apenas salva as respostas e retorna sucesso (Salvamento Intermediário)
                return jsonify({"message": "Respostas salvas com sucesso (salvamento intermediário)."}), 201


        except Exception as e:
            conn.rollback()
            # --- ATIVAÇÃO DO DEBUG DETALHADO ---
            print(f"ERRO CRÍTICO (POST /api/ctdi_surv): {str(e)}", file=sys.stderr)
            print("--- INÍCIO DO TRACEBACK DETALHADO ---", file=sys.stderr)
            # ESTA LINHA IRÁ IMPRIMIR O ERRO REAL DO PYTHON/PSICOPG2
            traceback.print_exc(file=sys.stderr)
            print("--- FIM DO TRACEBACK DETALHADO ---", file=sys.stderr)
            # ------------------------------------

            # Retorna um 500 para o cliente
            return jsonify({"error": f"Erro interno do servidor durante a transação. Detalhes no log."}), 500

@app.route('/api/ctdi_surv/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_survey(record_id):
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    if request.method == 'GET':
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de LEITURA
            record = db_manager.read_record_by_id(conn, 'ctdi_surv', record_id)
            return jsonify(record), 200 if record else (jsonify({"error": "Registro não encontrado."}), 404)
        except Exception as e:
            print(f"Erro GET em handle_single_survey: {e}", file=sys.stderr)
            return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

    elif request.method == 'PUT':
        data = request.json
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            if db_manager.update_record(conn, 'ctdi_surv', record_id, data):
                try:
                    # MUDANÇA CRÍTICA: Passar 'conn' para a leitura de acompanhamento
                    record = db_manager.read_record_by_id(conn, 'ctdi_surv', record_id)

                    if record and record.get('id_matu'):
                        id_matu_relacionado = record.get('id_matu')
                        # NOTA: CALC_MICROSERVICE_URL e 'requests' devem ser importados/definidos
                        calc_url = f"{CALC_MICROSERVICE_URL}/calculate/{id_matu_relacionado}"
                        requests.post(calc_url, json={})

                    return jsonify(
                        {"message": "Registro atualizado e cálculo de maturidade disparado com sucesso!"}), 200

                except Exception as e:
                    # Falha aqui NÃO afeta a transação do DB (já commitada pelo update_record)
                    print(f"Alerta: Falha ao disparar microsserviço de cálculo: {e}", file=sys.stderr)
                    return jsonify({"message": "Registro atualizado, mas falha ao disparar o cálculo."}), 500

            # update_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível atualizar o registro."}), 500

        except Exception as e:
            # Rollback para qualquer falha não tratada dentro do update_record
            conn.rollback()
            print(f"Erro PUT em handle_single_survey: {e}", file=sys.stderr)
            return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            deleted = db_manager.delete_record(conn, 'ctdi_surv', record_id)

            if deleted:
                return jsonify({"message": f"Registro {record_id} da tabela ctdi_surv deletado com sucesso."}), 200
            else:
                return jsonify({
                    "error": f"Registro {record_id} da tabela ctdi_surv não encontrado ou não pôde ser deletado."}), 404

        except psycopg2.errors.ForeignKeyViolation as e:
            # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
            conn.rollback()
            return jsonify({"error": "Não foi possível deletar o registro.",
                            "details": f"Violação de chave estrangeira: existem outros registros que dependem desta. Erro do DB: {e.pgerror}"}), 409

        except Exception as e:
            # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
            conn.rollback()
            return jsonify({"error": f"Erro interno do servidor ao deletar registro: {str(e)}"}), 500

#Endpoins de Blocos---------------------------------------------------------------------------------------------

@app.route('/api/leaf_bloc', methods=['GET', 'POST'])
def handle_blocos():
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            search_query = request.args.get('search_query', '')

            # MUDANÇA CRÍTICA: Passar 'conn' para os métodos de LEITURA
            if search_query:
                records = db_manager.search_records(conn, 'leaf_bloc', search_query)
            else:
                records = db_manager.read_all_records(conn, 'leaf_bloc')

            return jsonify(records), 200

        elif request.method == 'POST':
            data = request.json
            if not data:
                return jsonify({"error": "Dados inválidos."}), 400

            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            new_id = db_manager.create_record(conn, 'leaf_bloc', data)

            if new_id:
                return jsonify({"message": "Registro criado com sucesso!", "id": new_id}), 201
            # create_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível criar o registro."}), 500

    except Exception as e:
        # Tratamento de erro unificado para GET e POST
        print(f"Erro ao processar blocos: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao processar dados: {str(e)}"}), 500


@app.route('/api/ctdi_surv/partial', methods=['POST'])
def handle_partial_survey():
    try:
        conn = get_db_conn()
        data = request.json
        cursor = conn.cursor()

        id_matu = data.get('id_matu')
        id_ques = data.get('id_ques')
        grad_ques = data.get('grad_ques')

        # 1. VERIFICAÇÃO MANUAL: Já existe resposta para essa questão nesta maturidade?
        cursor.execute(
            "SELECT id_surv FROM public.ctdi_surv WHERE id_matu = %s AND id_ques = %s",
            (id_matu, id_ques)
        )
        record = cursor.fetchone()

        if record:
            # 2. SE EXISTE: Faz o UPDATE (O ID_SURV permanece o mesmo)
            cursor.execute(
                "UPDATE public.ctdi_surv SET grad_ques = %s WHERE id_matu = %s AND id_ques = %s",
                (grad_ques, id_matu, id_ques)
            )
        else:
            # 3. SE NÃO EXISTE: Faz o INSERT (O banco gera o próximo ID disponível)
            cursor.execute(
                """INSERT INTO public.ctdi_surv (id_matu, id_ques, id_dime, id_doma, grad_ques) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (id_matu, id_ques, data.get('id_dime'), data.get('id_doma'), grad_ques)
            )

        conn.commit()
        return jsonify({"message": "Resposta processada com ID preservado"}), 200

    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()


@app.route('/api/leaf_bloc/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_bloco(record_id):
    current_table_name = 'leaf_bloc'
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de LEITURA
            record = db_manager.read_record_by_id(conn, current_table_name, record_id)
            return jsonify(record), 200 if record else (jsonify({"error": "Registro não encontrado."}), 404)

        elif request.method == 'PUT':
            data = request.json
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            if db_manager.update_record(conn, current_table_name, record_id, data):
                return jsonify({"message": "Registro atualizado com sucesso!"}), 200
            # update_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível atualizar o registro."}), 500

        elif request.method == 'DELETE':
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            deleted = db_manager.delete_record(conn, current_table_name, record_id)
            if deleted:
                return jsonify(
                    {"message": f"Registro {record_id} da tabela {current_table_name} deletado com sucesso."}), 200
            else:
                return jsonify({
                                   "error": f"Registro {record_id} da tabela {current_table_name} não encontrado ou não pôde ser deletado."}), 404
        # Não precisa de um except aqui, o outer except é suficiente para ForeignKeyViolation

    except psycopg2.errors.ForeignKeyViolation as e:
        # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
        conn.rollback()
        return jsonify({"error": "Não foi possível deletar o registro.",
                        "details": f"Violação de chave estrangeira: existem outros registros que dependem desta. Erro do DB: {e.pgerror}"}), 409
    except Exception as e:
        # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
        conn.rollback()
        print(f"Erro interno do servidor ao deletar registro: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Erro interno do servidor ao deletar registro: {str(e)}"}), 500

    return jsonify({"error": "Método não permitido."}), 405

#Endpoins de Entregáveis---------------------------------------------------------------------------------------------
@app.route('/api/leaf_derv', methods=['GET', 'POST'])
def handle_entregaveis():
    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            # Captura os possíveis parâmetros da URL
            id_bloc = request.args.get('id_bloc')
            search_query = request.args.get('search_query', '')

            # 1. Lógica para o Modal de Sprints: Filtro por Bloco
            if id_bloc:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                query = "SELECT * FROM leaf_derv WHERE id_bloc = %s"
                cur.execute(query, (id_bloc,))
                records = cur.fetchall()
                cur.close()

            # 2. Lógica para o CRUD: Busca textual
            elif search_query:
                records = db_manager.search_records(conn, 'leaf_derv', search_query)

            # 3. Lógica para o CRUD: Listagem Geral
            else:
                records = db_manager.read_all_records(conn, 'leaf_derv')

            return jsonify(records), 200

        elif request.method == 'POST':
            data = request.json
            new_id = db_manager.create_record(conn, 'leaf_derv', data)

            if new_id:
                return jsonify({"message": "Registro criado com sucesso!", "id": new_id}), 201

            return jsonify({"error": "Não foi possível criar o registro."}), 500

    except Exception as e:
        # Rollback em caso de erro de transação
        if conn: conn.rollback()
        print(f"Erro ao processar entregáveis: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao processar dados: {str(e)}"}), 500


@app.route('/api/leaf_derv/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_entregavel(record_id):
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de LEITURA
            record = db_manager.read_record_by_id(conn, 'leaf_derv', record_id)
            return jsonify(record), 200 if record else (jsonify({"error": "Registro não encontrado."}), 404)

        elif request.method == 'PUT':
            data = request.json
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            if db_manager.update_record(conn, 'leaf_derv', record_id, data):
                return jsonify({"message": "Registro atualizado com sucesso!"}), 200
            # update_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível atualizar o registro."}), 500

        elif request.method == 'DELETE':
            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            deleted = db_manager.delete_record(conn, 'leaf_derv', record_id)
            if deleted:
                return jsonify({"message": f"Registro {record_id} da tabela leaf_derv deletado com sucesso."}), 200
            else:
                return jsonify({
                                   "error": f"Registro {record_id} da tabela leaf_derv não encontrado ou não pôde ser deletado."}), 404

    except psycopg2.errors.ForeignKeyViolation as e:
        # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
        conn.rollback()
        return jsonify({"error": "Não foi possível deletar o registro.",
                        "details": f"Violação de chave estrangeira: existem outros registros que dependem desta. Erro do DB: {e.pgerror}"}), 409
    except Exception as e:
        # MUDANÇA CRÍTICA: Rollback usando o objeto 'conn'
        conn.rollback()
        return jsonify({"error": f"Erro interno do servidor ao deletar registro: {str(e)}"}), 500

#Endpoins de Domínios---------------------------------------------------------------------------------------------
@app.route('/api/leaf_doma', methods=['GET', 'POST'])
def handle_dominios():
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            search_query = request.args.get('search_query', '')

            # MUDANÇA CRÍTICA: Passar 'conn' para os métodos de LEITURA
            if search_query:
                records = db_manager.search_records(conn, 'leaf_doma', search_query)
            else:
                records = db_manager.read_all_records(conn, 'leaf_doma')

            return jsonify(records), 200

        elif request.method == 'POST':
            data = request.json

            # MUDANÇA CRÍTICA: Passar 'conn' para o método de ESCRITA
            new_id = db_manager.create_record(conn, 'leaf_doma', data)

            if new_id:
                return jsonify({"message": "Registro criado com sucesso!", "id": new_id}), 201
            # create_record já faz o rollback em caso de falha interna
            return jsonify({"error": "Não foi possível criar o registro."}), 500

    except Exception as e:
        # Tratamento de erro unificado para GET e POST
        print(f"Erro ao processar domínios: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao processar dados: {str(e)}"}), 500

@app.route('/api/leaf_doma/<int:id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def handle_dominio_individual(id):
    # Resposta explícita para o Preflight do Navegador
    if request.method == 'OPTIONS':
        return '', 200

    try:
        conn = get_db_conn()
    except Exception as e:
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            record = db_manager.read_record_by_id(conn, 'leaf_doma', id)
            return jsonify(record) if record else (jsonify({"error": "Não encontrado"}), 404)

        elif request.method == 'PUT':
            data = request.json
            # Mapeia o ID para garantir que o CRUD saiba quem atualizar
            success = db_manager.update_record(conn, 'leaf_doma', id, data)
            if success:
                return jsonify({"message": "Registro atualizado com sucesso!"}), 200
            return jsonify({"error": "Falha na atualização"}), 500

        elif request.method == 'DELETE':
            success = db_manager.delete_record(conn, 'leaf_doma', id)
            if success:
                return jsonify({"message": "Registro deletado com sucesso!"}), 200
            return jsonify({"error": "Falha na exclusão"}), 500

    except Exception as e:
        print(f"Erro no endpoint individual: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500

@app.route('/api/diagnostico/<int:id_matu>', methods=['GET'])
def handle_diagnostico_request(id_matu):
    """
    Rota Flask para buscar o relatório de diagnóstico de maturidade.
    URL: /api/diagnostico/ID_MATURIDADE
    """
    # Esta função chama a função de processamento principal (get_diagnostico_report)
    return get_diagnostico_report(id_matu)

def get_diagnostico_report(id_matu):
    # ****************************************************************
    # FLUXO: OBTER CONEXÃO
    # ****************************************************************
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    # ------------------------------------------------------------------------------------------------------
    # FUNÇÃO AUXILIAR (MANTIDA)
    # ------------------------------------------------------------------------------------------------------
    def calculate_representative_benchmark(conn, id_doma):
        # (Sua lógica original de benchmark aqui - omitida para brevidade, mantenha a que já existe)
        pass

    # ------------------------------------------------------------------------------------------------------
    # INÍCIO DA ROTA PRINCIPAL
    # ------------------------------------------------------------------------------------------------------

    try:
        # 1. BUSCA REGISTRO DE MATURIDADE
        maturity = db_manager.read_record_by_id(conn, 'ctdi_matu', id_matu)

        if not maturity:
            return jsonify({"error": "Registro de maturidade não encontrado."}), 404

        # 2. TRATAMENTO DE SCORES (LEITURA)

        # --- A. LEITURA GERAL (Mantida) ---
        pgen_pres = float(maturity.get('pgen_pres') or 0.0)
        pgen_fut = float(maturity.get('pgen_fut') or 0.0)
        pgen_gap = float(maturity.get('pgen_gap') or 0.0)

        pdom_scores_pres = maturity.get('pdom_pres') or {}
        pdim_scores_pres = maturity.get('pdim_pres') or {}
        pdom_scores_fut = maturity.get('pdom_fut') or {}
        pdim_scores_fut = maturity.get('pdim_fut') or {}
        pdom_scores_gap = maturity.get('pdom_gap') or {}
        pdim_scores_gap = maturity.get('pdim_gap') or {}

        # --- B. LEITURA SETORIAL / EDUCAÇÃO (NOVA) ---
        # Usamos 'or 0.0' / 'or {}' para proteger contra NULLs do banco
        pgen_sect_pres = float(maturity.get('pgen_sect_pres') or 0.0)
        pgen_sect_fut = float(maturity.get('pgen_sect_fut') or 0.0)
        pgen_sect_gap = float(maturity.get('pgen_sect_gap') or 0.0)

        pdom_sect_pres = maturity.get('pdom_sect_pres') or {}
        pdim_sect_pres = maturity.get('pdim_sect_pres') or {}
        pdom_sect_fut = maturity.get('pdom_sect_fut') or {}
        pdim_sect_fut = maturity.get('pdim_sect_fut') or {}
        pdom_sect_gap = maturity.get('pdom_sect_gap') or {}
        pdim_sect_gap = maturity.get('pdim_sect_gap') or {}

        # 3. BUSCA DADOS DE REFERÊNCIA E BLOCOS (Mantido)
        benchmark_data_raw = db_manager.get_benchmark_by_sector(conn, 'Educação')
        blocks_data = db_manager.get_all_blocks_mapping(conn)

        # Serialização para evitar erros de objeto não serializável
        benchmark_data_serialized = [db_manager._convert_record_to_serializable(item) for item in benchmark_data_raw]

        # Mapeamento auxiliar para sugestões
        benchmark_map = {f"DIME_{item['id_dime']}": item for item in benchmark_data_serialized if item.get('id_dime')}
        benchmark_map.update({f"DOMA_{item['id_doma']}": item for item in benchmark_data_serialized if item.get('id_doma')})

        # 4. LÓGICA DE SUGESTÕES (Mantida a original baseada no GAP GERAL por enquanto)
        suggestions = []
        dimensoes_com_dor = [int(d_id) for d_id, g_val in pdim_scores_gap.items() if float(g_val) > 0]

        for id_doma_str, gap_score_dom_val in pdom_scores_gap.items():
            id_doma = int(id_doma_str)
            gap_score_dom = float(gap_score_dom_val)

            if gap_score_dom <= 0: continue

            blocos_assertivos = [
                {
                    "nome": b.get('name_bloc'),
                    "desc": b.get('desc_bloc'),
                    "id_dime": int(b.get('id_dime'))
                }
                for b in blocks_data
                if int(b.get('id_doma')) == id_doma and int(b.get('id_dime')) in dimensoes_com_dor
            ]

            if not blocos_assertivos: continue

            dominio_data = benchmark_map.get(f"DOMA_{id_doma}")
            suggestions.append({
                "dominio_nome": dominio_data.get('name_doma') if dominio_data else f"Domínio {id_doma}",
                "gap_dom": round(gap_score_dom, 2),
                "score_dom_pres": round(float(pdom_scores_pres.get(id_doma_str, 0.0)), 2),
                "score_dom_fut": round(float(pdom_scores_fut.get(id_doma_str, 0.0)), 2),
                "score_prioridade": gap_score_dom,
                "blocos_sugeridos": blocos_assertivos
            })

        suggestions.sort(key=lambda x: x['score_prioridade'], reverse=True)

        # 5. MOVIMENTO PRINCIPAL
        # Nota: Estamos usando o gap GERAL para definir o movimento macro.
        # Se quiser mudar para o setorial, troque pgen_gap por pgen_sect_gap
        movement_data = db_manager.get_movement_by_score(conn, pgen_gap)

        if not movement_data:
            movement_data_final = {
                "nome": "Transformação Ilimitada",
                "estagio_descricao": "Transformação profunda necessária.",
                "caracteristicas": "N/A",
                "implicacoes_diagnostico": "Foco na estratégia e nos pilares de maior Gap.",
            }
        else:
            movement_data_final = {
                "nome": movement_data.get('name_movi'),
                "estagio_descricao": movement_data.get('desc_movi'),
                "caracteristicas": movement_data.get('crtr_movi'),
                "implicacoes_diagnostico": movement_data.get('diag_movi')
            }

        # 6. MONTAGEM DO REPORT FINAL
        report = {
            "id_matu": id_matu,
            "cliente": maturity.get('nome_clie_text', 'N/A'),
            "email_cliente": maturity.get('mail_clie_text', 'N/A'),

            # --- DADOS GERAIS ---
            "score_geral_presente": pgen_pres,
            "score_geral_futuro": pgen_fut,
            "score_geral_gap": pgen_gap,

            # --- DADOS SETORIAIS (NOVA SEÇÃO) ---
            "score_educacao": {
                "geral": {
                    "presente": pgen_sect_pres,
                    "futuro": pgen_sect_fut,
                    "gap": pgen_sect_gap
                },
                "detalhe_gap": {
                    "pdom": pdom_sect_gap,
                    "pdim": pdim_sect_gap
                },
                 "detalhe_pres": {
                    "pdom": pdom_sect_pres,
                    "pdim": pdim_sect_pres
                },
                 "detalhe_fut": {
                    "pdom": pdom_sect_fut,
                    "pdim": pdim_sect_fut
                }
            },

            "movimento_principal": movement_data_final,

            "scores_detalhe_presente": {
                "pdom_scores": pdom_scores_pres,
                "pdim_scores": pdim_scores_pres
            },
            "scores_detalhe_futuro": {
                "pdom_scores": pdom_scores_fut,
                "pdim_scores": pdim_scores_fut
            },
            "scores_detalhe_gap": {
                "pdom_scores": pdom_scores_gap,
                "pdim_scores": pdim_scores_gap
            },

            "benchmark_setorial": benchmark_data_serialized,
            "suggestions": suggestions
        }

        return jsonify(report), 200

    except Exception as e:
        print(f"Erro ao gerar o relatório de diagnóstico para ID {id_matu}: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao gerar diagnóstico: {str(e)}"}), 500


# Função adaptada para Login Híbrido (Flask-Mail)
def send_access_code_email(mail_obj, recipient, access_code):
    """
    Envia o código de acesso via SMTP (Flask-Mail).
    """
    try:
        # Tenta pegar o sender da config, ou usa um padrão
        sender_email = app.config.get('MAIL_USERNAME', 'admin@leaction.com.br')

        msg = Message(
            subject='Seu Código de Acesso - LeAction',
            sender=sender_email,
            recipients=[recipient]
        )

        # Tenta construir a URL de acesso dinamicamente
        try:
            base_url = request.url_root.replace('/api/', '')  # Remove /api/ se estiver na raiz
            access_url = f"{base_url}acesso"
        except:
            # Fallback caso esteja rodando fora de contexto de request
            access_url = "https://leaction.com.br/acesso"

        msg.body = f"""
Olá!

Você solicitou acesso ao sistema LeAction.

Seu Código de Acesso é: {access_code}

1. Acesse: {access_url}
2. Digite seu e-mail: {recipient}
3. Insira o código acima quando solicitado.

Se você não solicitou este código, ignore este e-mail.
"""

        # Envia usando o objeto mail passado
        mail_obj.send(msg)
        print(f"E-mail de código enviado para {recipient} (Flask-Mail)")
        return True

    except Exception as e:
        print(f"ERRO CRÍTICO ao enviar e-mail (Flask-Mail): {e}", file=sys.stderr)
        return False
# A função AGORA espera receber o objeto 'mail' como argumento

def send_report_email(mail_obj, recipient, access_code):
    """
    Gera o PDF do relatório (simulado) e envia o e-mail com o código de acesso,
    rodando DENTRO do contexto da aplicação.
    """
    # É CRUCIAL rodar esta lógica DENTRO do contexto da aplicação Flask
    with app.app_context():
        try:
            # Garante que o sender use a configuração global
            sender_email = app.config['MAIL_USERNAME']

            # Montagem da Mensagem
            msg = Message(
                'Seu Código de Acesso e Diagnóstico LeAction',
                sender=sender_email,
                recipients=[recipient]
            )
            # request.url_root só funciona no contexto da aplicação
            access_url = request.url_root.replace('/api/', '') + 'acesso'

            msg.body = f"""
Olá!

Sua inscrição foi concluída com sucesso.

Seu Código de Acesso único é: {access_code}

Seu Login é o seu e-mail corporativo ({recipient}).

Acesse {access_url} para iniciar sua avaliação.

Obrigado por usar o LeAction System.
"""
            # 2. Envio da Mensagem
            mail_obj.send(msg)
            return True

        except Exception as e:
            # Este print agora deve aparecer no seu console em caso de erro
            print(f"ERRO CRÍTICO ao enviar e-mail para {recipient}: {e}", file=sys.stderr)
            return False


# app.py (Função Principal para Envio de E-mail via SES)
def send_report_email_ses(recipient, access_code, aws_region='us-east-2'):
    """
    Envia o e-mail de código de acesso usando o AWS SES (Boto3), incluindo o corpo HTML.
    """

    # 1. Configurar o cliente SES
    try:
        ses_client = boto3.client('ses', region_name=aws_region)
    except Exception as e:
        print(f"ERRO CRÍTICO ao inicializar cliente Boto3/SES: {e}", file=sys.stderr)
        return False

    # 2. Definir o URL de Acesso (Usando a lógica de request.url_root)
    try:
        # Pega a raiz, remove '/api/', e adiciona '/acesso'
        access_url = request.url_root.replace('/api/', '') + 'acesso'
    except RuntimeError:
        # Fallback seguro
        access_url = "https://paneldx.com.br/acesso"

    # Adiciona o access_code à URL
    access_url_with_code = f"{access_url}/{access_code}"

    # 3. Montar a Mensagem
    sender_email = os.environ.get('EMAIL_SENDER', 'consultant@paneldx.com.br')
    subject = 'Seu Código de Acesso para o Diagnóstico LeAction'

    # --- NOVO BLOCO: GERAÇÃO DO CORPO HTML (render_template) ---
    body_html = None
    try:
        # Renderiza o template HTML (templates/email_access_code.html)
        body_html = render_template('email_access_code.html',
                                    recipient=recipient,
                                    access_code=access_code,
                                    access_url=access_url_with_code)
    except Exception as e:
        print(f"ALERTA: Falha ao renderizar template HTML: {e}", file=sys.stderr)
        body_html = None
    # -------------------------------------------------------------

    # 4. Processamento do Corpo do E-mail TEXTO (Fallback)
    template_body = f"""\
Olá!

Sua inscrição foi concluída com sucesso.

Seu Código de Acesso único é: 
{access_code}

Seu Login é o seu e-mail corporativo: 
({recipient}).

Acesse {access_url_with_code} 
para iniciar sua avaliação.

Obrigado por usar o PanelDX (LeAction System).

Entre em contato por: 
conhecer@leaction.com.br.
"""
    clean_text = textwrap.dedent(template_body).strip()
    body_text = clean_text.replace('\n', '\r\n')

    # 5. Configurar o Corpo da Mensagem SES
    message_body = {
        'Text': {
            'Data': body_text,
            'Charset': 'UTF-8'
        }
    }

    # ADICIONAR HTML SE TIVER SUCESSO
    if body_html:
        message_body['Html'] = {
            'Data': body_html,
            'Charset': 'UTF-8'
        }

    # 6. ENVIAR O E-MAIL
    try:
        response = ses_client.send_email(
            Source=sender_email,
            Destination={
                'ToAddresses': [recipient],
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': message_body  # Usa a mensagem TEXTO e HTML
            }
        )
        print(f"E-mail enviado via SES. MessageId: {response['MessageId']}", file=sys.stderr)
        return True

    except Exception as e:
        print(f"ERRO CRÍTICO ao enviar e-mail via SES para {recipient}: {e}", file=sys.stderr)
        return False


# ENDPOINT DE ENVIO DE EMAIL DE NOTIFICAÇÃO DO RELATÓRIO----------------------------------------------------------------
@app.route('/api/request-pdf-email', methods=['POST'])
def request_pdf_email():
    # 1. REMOÇÃO: O bloco de verificação db_manager.conn é obsoleto.

    # ****************************************************************
    # NOVO FLUXO: OBTER CONEXÃO (Única vez)
    # ****************************************************************
    try:
        # Tenta obter a conexão ativa da requisição
        conn = get_db_conn()
    except Exception as e:
        # Se falhar ao conectar, retorna erro 500
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    data = request.json
    email = data.get('email')
    id_matu = data.get('id_matu')

    if not email or not id_matu:
        return jsonify({"error": "E-mail e ID de Maturidade são obrigatórios para a notificação."}), 400

    try:
        # Busca o nome do cliente para a saudação no e-mail
        # MUDANÇA CRÍTICA: Passar 'conn' para o método de LEITURA
        maturity_record = db_manager.read_maturity_with_client_name(conn, id_matu)
        client_name = maturity_record.get('nome_clie_text', 'Lead') if maturity_record else 'Lead'

        # REUTILIZANDO O CÓDIGO DA FUNÇÃO DE NOTIFICAÇÃO (send_report_email)
        mail_obj = app.extensions['mail']

        with app.app_context():
            sender_email = app.config['MAIL_USERNAME']

            msg = Message(
                'Link de Acesso ao Seu Diagnóstico de Maturidade',
                sender=sender_email,
                recipients=[email]
            )

            # URL de acesso direto ao diagnóstico (porta 3001)
            diagnostic_url = request.url_root.replace('/api/', '') + f'diagnostico/{id_matu}'

            msg.body = f"""
        Olá {client_name},

        Seu relatório de diagnóstico foi concluído!

        Você pode visualizar seu relatório a qualquer momento através do link abaixo:
        Link de Acesso ao Diagnóstico: {diagnostic_url}

        Este e-mail serve como confirmação de que seu relatório foi processado.

        Atenciosamente,
        Equipe LeAction
        """
            # Se fosse anexar o PDF, a lógica de anexo viria aqui
            # msg.attach("relatorio.pdf", "application/pdf", pdf_data)

            mail_obj.send(msg)

            # Retorna sucesso se o envio SMTP não falhar
            return jsonify(
                {"message": "Solicitação de envio por e-mail registrada com sucesso. Verifique sua caixa!"}), 200

    except Exception as e:
        print(f"Erro ao registrar solicitação de e-mail: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao processar notificação: {str(e)}"}), 500

# ENDPOINT DE TRATAMENTO DOS LEADS------------------------------------------------------------------------
@app.route('/api/register-lead', methods=['POST'])
def register_lead():
    # 1. REMOÇÃO: A verificação "if not db_manager.conn:" é obsoleta
    #    e o fluxo de get_db_conn() será usado para tratar a falha.

    lead_data = request.json

    # ****************************************************************
    # ATUALIZAÇÃO B2B: Validação de campos
    # ****************************************************************
    # Removemos 'DOCU_CLIE' da exigência do front e adicionamos 'EMPRESA_CLIE'
    required_fields = ["NOME_CLIE", "MAIL_CLIE", "EMPRESA_CLIE", "FUNC_LEAD"]

    for field in required_fields:
        if not lead_data.get(field):
            return jsonify({"error": f"O campo '{field}' é obrigatório."}), 400

    # ****************************************************************
    # GROWTH HACK: Gerar Documento Provisório
    # ****************************************************************
    # Como o banco exige docu_clie (NOT NULL), geramos um código interno.
    # O CNPJ real será preenchido depois pelo Admin na tela de Clientes.
    lead_data['DOCU_CLIE'] = f"LEAD-{uuid.uuid4().hex[:8].upper()}"

    # ****************************************************************
    # OBTER CONEXÃO
    # ****************************************************************
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        # 1. Cria cliente, maturidade inicial e código de acesso
        # O db_manager agora receberá o 'DOCU_CLIE' gerado e o 'EMPRESA_CLIE' do form
        id_clie, access_code = db_manager.create_lead_client_maturity(conn, lead_data)

        if not id_clie:
            raise Exception("Falha ao obter ID do novo cliente.")

        # 2. ENVIAR NOTIFICAÇÃO (FASE 4)
        # Nota: Certifique-se de que sua função de email está importada corretamente
        try:
            email_sent = send_report_email_ses(lead_data['MAIL_CLIE'], access_code)
            if not email_sent:
                print("Alerta: E-mail não enviado, mas cadastro realizado.", file=sys.stderr)
        except Exception as e_mail:
            print(f"Erro ao tentar enviar email: {e_mail}", file=sys.stderr)

        # 3. Retorno ao Frontend
        return jsonify({
            "message": "Inscrição realizada com sucesso! Código de acesso enviado.",
            "email": lead_data['MAIL_CLIE']
        }), 201

    except Exception as e:
        print(f"Erro ao registrar lead: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao registrar lead: {str(e)}"}), 500

# 1. FUNÇÃO PARA OBTER/CRIAR A CONEXÃO
def get_db_conn():
    """Cria uma nova conexão com o DB e a armazena em g se ainda não existir."""
    if 'db_conn' not in g:
        # Usa o método de conexão do seu DBManager (que deve retornar uma nova conexão)
        g.db_conn = db_manager._connect_db()
    return g.db_conn


# 2. FUNÇÃO PARA FECHAR A CONEXÃO (ao final da requisição)
@app.teardown_request
def close_db_conn(exception):
    """Fecha a conexão com o banco de dados no final da requisição."""
    db_conn = g.pop('db_conn', None)

    if db_conn is not None:
        try:
            # Garante que a conexão está fechada.
            db_conn.close()
        except Exception as e:
            # Evita que erros de fechamento quebrem a aplicação
            print(f"Erro ao fechar a conexão DB: {e}", file=sys.stderr)


# ========================================================================================
# ROTA: GERAÇÃO DO PLANO INTELIGENTE (IA GENESIS) - VERSÃO BÍBLIA LEACTION
# ========================================================================================

@app.route('/api/client/generate-ai-plan', methods=['POST'])
def generate_ai_plan():
    print("\n⚡ [DEBUG START] Iniciando Gênese IA...")
    try:
        data = request.json or {}
        id_matu = data.get('id_matu')
        print(f"🔍 [DEBUG] ID Maturidade recebido: {id_matu}")

        conn = get_db_conn()
        cursor = conn.cursor()

        # 1. BUSCA O ID_CLIE
        cursor.execute("SELECT id_clie FROM ctdi_matu WHERE id_matu = %s", (id_matu,))
        res_matu = cursor.fetchone()
        if not res_matu:
            print(f"❌ [DEBUG ERROR] id_matu {id_matu} não encontrado na ctdi_matu!")
            return jsonify({"error": "Maturidade não encontrada"}), 404

        id_clie = res_matu[0]
        print(f"✅ [DEBUG] Cliente localizado: ID {id_clie}")

        # 2. VERIFICA/CRIA CTDI_MAIN (O Ciclo)
        cursor.execute("SELECT id_ctdi FROM ctdi_main WHERE id_matu = %s", (id_matu,))
        res_main = cursor.fetchone()

        if not res_main:
            print(f"🚧 [DEBUG] ctdi_main não existe. Criando...")
            cursor.execute("""
                           INSERT INTO ctdi_main (id_matu, id_dime, name_ctdi, stat_ctdi)
                           VALUES (%s, 1, 'Plano de Aceleração Digital', 'inativo') RETURNING id_ctdi
                           """, (id_matu,))
            id_ctdi = cursor.fetchone()[0]
            print(f"✅ [DEBUG] ctdi_main criada com ID: {id_ctdi}")
        else:
            id_ctdi = res_main[0]
            print(f"✅ [DEBUG] ctdi_main já existente: ID {id_ctdi}")

        # 3. UPSERT NA CTDI_PROJETOS (Lógica Manual de Segurança)
        print(f"📡 [DEBUG] Sincronizando ctdi_projetos...")
        cursor.execute("SELECT id_proj FROM ctdi_projetos WHERE id_clie = %s", (id_clie,))
        proj_res = cursor.fetchone()

        if proj_res:
            print(f"🔄 [DEBUG] Atualizando projeto ID: {proj_res[0]}")
            cursor.execute("""
                           UPDATE ctdi_projetos
                           SET id_ctdi            = %s,
                               data_geracao_plano = CURRENT_TIMESTAMP,
                               status             = 'ATIVO',
                               fase_atual         = 'IA: Processando Roadmap...'
                           WHERE id_clie = %s
                           """, (id_ctdi, id_clie))
        else:
            print(f"🆕 [DEBUG] Criando novo registro em ctdi_projetos")
            cursor.execute("""
                           INSERT INTO ctdi_projetos (id_clie, id_ctdi, data_geracao_plano, status, fase_atual)
                           VALUES (%s, %s, CURRENT_TIMESTAMP, 'ATIVO', 'IA: Iniciando Gênese...')
                           """, (id_clie, id_ctdi))

        # 4. O GATILHO PARA O WORKER
        print(f"🚀 [DEBUG] Setando status_ia = 'PENDENTE' na ctdi_matu")
        cursor.execute("UPDATE ctdi_matu SET status_ia = 'PENDENTE' WHERE id_matu = %s", (id_matu,))


        conn.commit()
        print(f"🏁 [DEBUG SUCCESS] Transação commitada com sucesso!")
        print(f"✅ [DATABASE] Status PENDENTE confirmado no banco para o ID {id_matu}")

        cursor.close()
        conn.close()

        return jsonify({"success": True, "id_ctdi": id_ctdi}), 200

    except Exception as e:
        if 'conn' in locals() and conn: conn.rollback()
        print(f"🚨 [DEBUG CRITICAL ERROR]: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ========================================================================================
# ROTA: BUSCAR JORNADA COMPLETA (Ondas + Sprints)
# ========================================================================================
@app.route('/api/client/journey', methods=['GET'])
def get_client_journey():
    # O Node envia id_matu ou id_clie. Vamos focar no id_matu (O HUB)
    id_matu = request.args.get('id_matu') or request.args.get('id_clie')

    if not id_matu:
        return jsonify({"error": "Identificador (id_matu) obrigatório"}), 400

    conn = get_db_conn()
    # Usar DictCursor facilita muito a vida para o JSON não vir bagunçado
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # QUERY MESTRA: Une Main -> Itera -> Sprn a partir do HUB (id_matu)
        sql = """
              SELECT i.id_itera, \
                     i.name_itera, \
                     i.stat_itera, \
                     s.id_sprn, \
                     s.name_sprn, \
                     s.desc_sprn, \
                     s.stat_sprn, \
                     s.dtini_sprn, \
                     s.dtend_sprn
              FROM ctdi_main m
                       JOIN ctdi_itera i ON m.id_ctdi = i.id_ctdi
                       LEFT JOIN ctdi_sprn s ON i.id_itera = s.id_itera
              WHERE m.id_matu = %s
              ORDER BY i.id_phase ASC, s.id_sprn ASC \
              """
        cursor.execute(sql, (id_matu,))
        rows = cursor.fetchall()

        # Agrupamento lógico para o formato do EJS
        jornada_map = {}
        for row in rows:
            it_id = row['id_itera']
            if it_id not in jornada_map:
                jornada_map[it_id] = {
                    "id": it_id,
                    "nome": row['name_itera'],
                    "status": row['stat_itera'],
                    "sprints": []
                }

            if row['id_sprn']:
                jornada_map[it_id]['sprints'].append({
                    "id": row['id_sprn'],
                    "nome": row['name_sprn'],
                    "objetivo": row['desc_sprn'] or 'Foco em implementação estratégica.',
                    "status": row['stat_sprn'] or 'planejada',
                    "data_inicio": row['dtini_sprn'],
                    "data_fim": row['dtend_sprn']
                })

        return jsonify(list(jornada_map.values())), 200

    except Exception as e:
        print(f"❌ ERRO JOURNEY: {e}")
        return jsonify([]), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/client/update-sprint-date', methods=['POST'])
def update_sprint_date_python():
    data = request.json
    id_sprn = data.get('id_sprn')
    data_inicio = data.get('data_inicio')
    id_clie = data.get('id_clie')

    # Log para auditoria no terminal do Python
    print(f"--- [DEBUG PYTHON] Ativando Sprint {id_sprn} para {data_inicio} ---")

    # 1. Obter conexão
    conn = db_manager._connect_db()

    try:
        # 1. SQL: Mudamos 'AGENDADA' para 'ativa' (padrão que o Kanban busca)
        sql_sprint = """
                     UPDATE ctdi_sprn
                     SET dtini_sprn = %s::date,
                         dtend_sprn = (%s::date + INTERVAL '7 days'),
                         stat_sprn  = 'ativa'
                     WHERE id_sprn = %s
                     RETURNING name_sprn
                     """

        # 2. Executa a query de atualização da Sprint
        res = db_manager.execute_query(conn, sql_sprint, (data_inicio, data_inicio, id_sprn))

        if res and len(res) > 0:
            primeira_linha = res[0]
            if isinstance(primeira_linha, dict):
                nome_sprint = primeira_linha.get('name_sprn')
            elif isinstance(primeira_linha, (list, tuple)):
                nome_sprint = primeira_linha[0]
            else:
                nome_sprint = primeira_linha

            print(f"--- [DEBUG PYTHON] Sprint '{nome_sprint}' ATIVADA. Sincronizando status global...")

            # 3. SQL Status Global: Mudamos para 'CONCLUIDO'
            # Isso satisfaz a lógica 'isGenesisOk' do seu index.ejs e libera o Kanban
            sql_status = """
                UPDATE ctdi_matu SET status_ia = 'CONCLUIDO', dt_fim_ia = NOW()
                WHERE id_matu = (
                    SELECT id_matu FROM ctdi_main m 
                    JOIN ctdi_itera i ON m.id_ctdi = i.id_ctdi 
                    JOIN ctdi_sprn s ON i.id_itera = s.id_itera 
                    WHERE s.id_sprn = %s LIMIT 1
                )
            """
            db_manager.execute_update(conn, sql_status, (id_sprn,))

        return jsonify({"success": True, "message": "Sprint ativada com sucesso!"}), 200

    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO BACKEND: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        # 4. Fechar a conexão
        if conn:
            conn.close()


@app.route('/api/admin/monitor-genese-data', methods=['GET'])
def get_monitor_data():
    try:
        conn = get_db_conn()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Usamos COALESCE para garantir que o EJS não receba 'null' e quebre
        cursor.execute("""
                       SELECT COALESCE(cliente, 'Cliente Novo')          as cliente,
                              COALESCE(fase_atual, 'Aguardando Início')  as fase_atual,
                              COALESCE(status_worker, 'INATIVO')         as status_worker,
                              COALESCE(id_diagnostico, 0)                as id_diagnostico,
                              TO_CHAR(nascimento_plano, 'DD/MM HH24:MI') as nascimento_plano
                       FROM vw_dashboard_genese
                       ORDER BY nascimento_plano DESC LIMIT 10
                       """)

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(results), 200
    except Exception as e:
        print(f"❌ Erro no Pulse: {e}")
        return jsonify([]), 200  # Retorna array vazio para o EJS não dar erro

@app.route('/api/meus-projetos', methods=['GET'])
def get_meus_projetos():
    role = (request.args.get('role') or '').upper()
    conn = db_manager._connect_db()
    cur = conn.cursor()

    try:
        # A MUDANÇA: Adicionamos JOIN com ctdi_sprn para filtrar por 'ativa'
        base_query = """
                     SELECT DISTINCT q.id_squad,
                                     q.nome_squad,
                                     p.id_ctdi,
                                     COALESCE(m.name_ctdi, 'Projeto sem Nome') as name_ctdi,
                                     c.nome_clie,
                                     m.id_matu,
                                     p.id_proj
                     FROM ctdi_squads q
                              JOIN ctdi_projetos p ON q.id_proj = p.id_proj
                              JOIN ctdi_sprn s ON q.id_squad = s.id_squad
                              LEFT JOIN ctdi_main m ON p.id_ctdi = m.id_ctdi
                              LEFT JOIN ctdi_matu mt ON m.id_matu = mt.id_matu
                              LEFT JOIN ctdi_clie c ON mt.id_clie = c.id_clie
                     WHERE p.status = 'ATIVO'
                       AND s.stat_sprn = 'ativa'
                     """

        if role == 'ADMIN':
            query = base_query + " ORDER BY p.id_ctdi DESC, q.id_squad ASC"
            cur.execute(query)
        else:
            id_clie = request.args.get('id_clie')
            query = base_query + " AND p.id_clie = %s ORDER BY p.id_ctdi DESC, q.id_squad ASC"
            cur.execute(query, (id_clie,))

        rows = cur.fetchall()

        projetos = []
        for row in rows:
            projetos.append({
                "id_squad": row[0],
                "nome_squad": row[1],
                "id_ctdi": row[2],
                "name_ctdi": row[3],
                "nome_clie": row[4],
                "id_matu": row[5],
                "id_proj": row[6]
            })

        return jsonify(projetos)
    except Exception as e:
        print(f"🚨 Erro no Python: {e}")
        return jsonify([]), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/seletor-projetos-ativos', methods=['GET'])
def get_seletor_projetos():
    role = (request.args.get('role') or '').upper()
    id_clie = request.args.get('id_clie')
    conn = db_manager._connect_db()
    cur = conn.cursor()

    try:
        # Query ultra simplificada: foca no Projeto e garante unicidade
        query = """
            SELECT DISTINCT
                p.id_ctdi, 
                COALESCE(m.name_ctdi, 'Projeto sem Nome') as nome_projeto,
                c.nome_clie,
                m.id_matu
            FROM ctdi_projetos p
            JOIN ctdi_squads q ON p.id_proj = q.id_proj
            JOIN ctdi_sprn s ON q.id_squad = s.id_squad
            LEFT JOIN ctdi_main m ON p.id_ctdi = m.id_ctdi
            LEFT JOIN ctdi_matu mt ON m.id_matu = mt.id_matu
            LEFT JOIN ctdi_clie c ON mt.id_clie = c.id_clie
            WHERE p.status = 'ATIVO'
              AND s.stat_sprn = 'ativa'
        """

        if role != 'ADMIN':
            query += " AND p.id_clie = %s"
            cur.execute(query + " ORDER BY p.id_ctdi DESC", (id_clie,))
        else:
            cur.execute(query + " ORDER BY p.id_ctdi DESC")

        rows = cur.fetchall()
        return jsonify([{
            "id_ctdi": r[0],
            "nome": r[1],
            "cliente": r[2],
            "id_matu": r[3]
        } for r in rows])

    finally:
        cur.close()
        conn.close()

# --- 1. ROTA PARA LISTAGEM E CRIAÇÃO ---
@app.route('/api/ctdi_team', methods=['GET', 'POST'])
def handle_ctdi_team():
    conn = db_manager._connect_db()
    cur = conn.cursor()

    # --- LISTAGEM (GET) ---
    if request.method == 'GET':
        # Aceita 'id_squad' (novo) ou 'id_team' (antigo) para não quebrar o front atual
        id_squad = request.args.get('id_squad') or request.args.get('id_team')

        print(f">>> [DEBUG GET] Solicitando membros para a Squad: {id_squad}")

        if not id_squad:
            return jsonify([]), 200

        try:
            # Alteramos o WHERE para a nova coluna id_squad
            # Mas mantemos id_team no SELECT para o seu JS não estranhar o objeto
            query = """
                    SELECT id_member,
                           nome,
                           email,
                           role,
                           position,
                           ativo,
                           id_squad,
                           data_cadastro
                    FROM ctdi_team
                    WHERE id_squad = %s
                      AND role NOT IN ('ADMIN', 'SYSADMIN')
                    ORDER BY nome ASC
                    """
            cur.execute(query, (id_squad,))
            rows = cur.fetchall()

            membros = []
            for r in rows:
                membros.append({
                    "id_member": r[0],
                    "nome": r[1],
                    "email": r[2],
                    "role": r[3],
                    "position": r[4],
                    "ativo": r[5],
                    # Retornamos como 'id_team' e 'id_squad' para compatibilidade total
                    "id_team": r[6],
                    "id_squad": r[6],
                    "data_cadastro": r[7].strftime('%d/%m/%Y %H:%M') if r[7] else None
                })
            return jsonify(membros)
        except Exception as e:
            print(f"🚨 [ERRO GET]: {str(e)}")
            return jsonify([]), 500
        finally:
            if cur: cur.close()
            if conn: conn.close()

    # --- INCLUSÃO (POST) ---
    if request.method == 'POST':
        data = request.json
        print(f">>> [DEBUG POST] Dados recebidos: {data}")

        try:
            # 1. Limpeza de Segurança e Ajuste de IDs
            data.pop('id_member', None)  # Garante que o banco gere o ID (PK)

            # Se o front ainda estiver enviando 'id_team', movemos para 'id_squad'
            # Isso evita o erro de "null value" se o front-end ainda não foi atualizado
            if 'id_team' in data and 'id_squad' not in data:
                data['id_squad'] = data.pop('id_team')

            # 2. Preparação das colunas
            columns = list(data.keys())

            # Verificação de segurança: id_squad PRECISA estar aqui para não quebrar a constraint NOT NULL
            if 'id_squad' not in columns:
                # Aqui você pode decidir se retorna erro ou se associa a uma squad padrão
                return jsonify({"error": "O campo id_squad é obrigatório para cadastrar membros."}), 400

            if 'data_cadastro' not in columns:
                columns.append('data_cadastro')

            # 3. SQL Dinâmico ajustado
            # Usamos %s para todos os valores, exceto para data_cadastro que usa NOW()
            placeholders = []
            for col in columns:
                if col == 'data_cadastro':
                    placeholders.append('NOW()')
                else:
                    placeholders.append('%s')

            query = f"""
                INSERT INTO ctdi_team ({', '.join(columns)}) 
                VALUES ({', '.join(placeholders)}) 
                RETURNING id_member;
            """

            # Filtramos os parâmetros para não enviar valor onde é NOW()
            params = [data[k] for k in columns if k != 'data_cadastro']

            cur.execute(query, tuple(params))
            new_id = cur.fetchone()[0]
            conn.commit()

            print(f"✅ [DEBUG POST] Sucesso! Novo ID: {new_id} na Squad: {data.get('id_squad')}")
            return jsonify({"success": True, "id": new_id}), 201

        except Exception as e:
            if conn: conn.rollback()
            print(f"🚨 [ERRO POST]: {str(e)}")
            return jsonify({"error": str(e)}), 500
        finally:
            if cur: cur.close()
            if conn: conn.close()


# --- 2. ROTA PARA EDIÇÃO E EXCLUSÃO ---
@app.route('/api/ctdi_team/<int:id_member>', methods=['PUT', 'DELETE'])
def update_delete_team(id_member):
    conn = db_manager._connect_db()
    cur = conn.cursor()

    try:
        if request.method == 'PUT':
            data = request.json
            print(f">>> [DEBUG PUT] Editando membro {id_member}")

            # Ajuste de compatibilidade para o id_squad (caso venha como id_team)
            target_squad = data.get('id_squad') or data.get('id_team')

            # SQL atualizado para incluir id_squad
            query = """
                    UPDATE ctdi_team
                    SET nome     = %s,
                        email    = %s,
                        role     = %s,
                        position = %s,
                        ativo    = %s,
                        id_squad = %s
                    WHERE id_member = %s
                    """
            # Adicionamos target_squad na tupla de execução
            cur.execute(query, (
                data['nome'],
                data['email'],
                data['role'],
                data['position'],
                data['ativo'],
                target_squad, # <--- Nova coluna
                id_member
            ))

            # Se vier senha, atualiza separado (mantém sua lógica original)
            if data.get('password_hash'):
                cur.execute("UPDATE ctdi_team SET password_hash = %s WHERE id_member=%s",
                            (data['password_hash'], id_member))

            conn.commit()
            return jsonify({"success": True})

        if request.method == 'DELETE':
            # O DELETE não muda nada, pois ele mata a linha pelo ID da PK (id_member)
            print(f">>> [DEBUG DELETE] Removendo membro {id_member}")
            cur.execute("DELETE FROM ctdi_team WHERE id_member=%s", (id_member,))
            conn.commit()
            return jsonify({"success": True})

    except Exception as e:
        if conn: conn.rollback()
        print(f"🚨 [ERRO PUT/DELETE]: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()

# Rotas de tratamento da IA nova fase 14/04/2026

# Garante que o Python enxergue a subpasta ai_engine para futuras integrações
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai_engine'))


@app.route('/api/admin/ia-status', methods=['GET'])
def get_ia_status():
    conn = None
    try:
        # 2. Uso do seu db_manager padrão
        conn = db_manager._connect_db()

        # 3. Cursor que retorna dicionários (chave: valor)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Query otimizada para a Torre de Controle
        query = """
                WITH progresso_calculado AS (SELECT mn.id_matu, \
                                                    COUNT(s.id_sprn)                                           as total_sprints, \
                                                    SUM(CASE WHEN s.stat_sprn = 'concluida' THEN 1 ELSE 0 END) as sprints_concluidas \
                                             FROM ctdi_sprn s \
                                                      JOIN ctdi_itera i ON s.id_itera = i.id_itera \
                                                      JOIN ctdi_main mn ON i.id_ctdi = mn.id_ctdi \
                                             GROUP BY mn.id_matu)
                SELECT m.id_matu, \
                       c.nome_clie, \
                       m.dt_fim_ia, \
                       m.status_ia, \
                       m.url_pdf_ia, \
                       m.pgen_gap, \
                       COALESCE( \
                               (p.sprints_concluidas::float / NULLIF(p.total_sprints, 0)) * 100, \
                               0 \
                       ) as progresso_modulador
                FROM ctdi_matu m
                         JOIN ctdi_clie c ON m.id_clie = c.id_clie
                         LEFT JOIN progresso_calculado p ON m.id_matu = p.id_matu
                ORDER BY m.dt_fim_ia DESC NULLS LAST
                """

        cur.execute(query)
        records = cur.fetchall()
        cur.close()

        return jsonify(records), 200

    except Exception as e:
        print(f"❌ Erro na rota IA-Status: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


import re


@app.route('/api/admin/ia-status-detalhado/<int:id_matu>', methods=['GET'])
def get_ia_status_detalhado(id_matu):
    conn = None
    try:
        conn = db_manager._connect_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = """
                SELECT m.id_matu, c.nome_clie, m.dt_fim_ia, m.url_pdf_ia, m.pgen_gap, m.txt_diagnostico_ia
                FROM ctdi_matu m
                         JOIN ctdi_clie c ON m.id_clie = c.id_clie
                WHERE m.id_matu = %s \
                """
        cur.execute(query, (id_matu,))
        registro = cur.fetchone()
        cur.close()

        if not registro or not registro['txt_diagnostico_ia']:
            return jsonify({"error": "Plano vazio"}), 404

        txt = registro['txt_diagnostico_ia']

        # --- FUNÇÃO DE EXTRAÇÃO FLEXÍVEL (Substitua a antiga por esta) ---
        def extrair(texto, palavras_chave_inicio, marcadores_fim):
            try:
                import re
                # Padrão para achar o título: aceita #, emojis e asteriscos ao redor das palavras-chave
                regex_inicio = r'#+.*(?:' + '|'.join(palavras_chave_inicio) + r').*'
                match_inicio = re.search(regex_inicio, texto, re.IGNORECASE)

                if not match_inicio:
                    return ""

                content_start = match_inicio.end()

                # O fim da seção é onde começa o próximo título (#) que contenha uma das palavras de fronteira
                end_idx = len(texto)
                for marcador in marcadores_fim:
                    regex_fim = r'\n#+.*(?:' + marcador + r').*'
                    match_fim = re.search(regex_fim, texto[content_start:], re.IGNORECASE)
                    if match_fim:
                        pos_absoluta = content_start + match_fim.start()
                        if pos_absoluta < end_idx:
                            end_idx = pos_absoluta

                resultado = texto[content_start:end_idx].strip()
                # Limpa linhas de separação e excesso de espaços
                return re.sub(r'^-+\s*', '', resultado).replace('---', '').strip()
            except Exception as e:
                print(f"Erro na extração: {e}")
                return ""

        # --- MAPEAMENTO INTELIGENTE (Baseado no seu log de debug) ---
        txt = registro['txt_diagnostico_ia']

        registro['detalhes'] = {
            # Busca por "SÍNTESE EXECUTIVA"
            "sintese": extrair(txt, ["SÍNTESE EXECUTIVA"], ["ALERTA", "ANÁLISE", "DIAGNÓSTICO"]),

            # Busca por "ALERTA" ou "CRÍTICO"
            "alerta_critico": extrair(txt, ["ALERTA", "CRÍTICO"], ["ANÁLISE", "DIAGNÓSTICO", "DOMÍNIOS"]),

            # Busca por "ANÁLISE DOS DOMÍNIOS" ou "DIAGNÓSTICO"
            "dominios_texto": extrair(txt, ["ANÁLISE DOS DOMÍNIOS", "DIAGNÓSTICO"], ["ESTRATÉGIA DE ONDAS", "ROADMAP"]),

            # Busca por "ESTRATÉGIA DE ONDAS" ou "ROADMAP"
            "roadmap_texto": extrair(txt, ["ESTRATÉGIA DE ONDAS", "ROADMAP"],
                                     ["RECOMENDAÇÕES ESPECÍFICAS", "GEOGRÁFICAS"]),

            # Busca por "GEOGRÁFICAS" ou "ESPECÍFICAS" (Ajustado para o seu novo log)
            "geografia": extrair(txt, ["RECOMENDAÇÕES ESTRATÉGICAS ESPECÍFICAS", "GEOGRÁFICAS"],
                                 ["MÉTRICAS", "CONCLUSÃO"]),

            # Busca por "MÉTRICAS" ou "RECOMENDAÇÕES"
            "recomendacoes": extrair(txt, ["MÉTRICAS DE SUCESSO", "RECOMENDAÇÕES"], ["CONCLUSÃO", "PRÓXIMOS PASSOS"]),

            # Busca por "CONCLUSÃO" ou "PRÓXIMOS PASSOS"
            "conclusao": extrair(txt, ["CONCLUSÃO ESTRATÉGICA", "PRÓXIMOS PASSOS"], ["###FIM_TEXTO###", "---"])
        }

        return jsonify(registro), 200

    except Exception as e:
        print(f"❌ Erro no processamento do detalhado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/client/update-clima', methods=['POST'])
def update_client_clima():
    conn = None
    try:
        data = request.json
        id_clie = data.get('id_clie')

        # Extraindo todos os campos do payload do modal
        tipo_ensino = data.get('tipo_ensino')
        qtd_alunos = data.get('qtd_alunos')
        localizacao = data.get('localizacao_sede')
        rede_ensino = data.get('rede_ensino')
        qtd_colab = data.get('qtd_colaboradores')
        qtd_unid = data.get('qtd_unidades')
        clima = data.get('clima_organizacional')

        conn = get_db_conn()
        cursor = conn.cursor()

        # UPDATE unificado na ctdi_clie
        cursor.execute("""
                       UPDATE ctdi_clie
                       SET tipo_ensino          = %s,
                           qtd_alunos           = %s,
                           localizacao_sede     = %s,
                           rede_ensino          = %s,
                           qtd_colaboradores    = %s,
                           qtd_unidades         = %s,
                           clima_organizacional = %s
                       WHERE id_clie = %s
                       """, (tipo_ensino, qtd_alunos, localizacao, rede_ensino, qtd_colab, qtd_unid, clima, id_clie))

        conn.commit()
        cursor.close()

        print(f">>> SUCESSO: Contexto do Cliente {id_clie} atualizado.")
        return jsonify({"success": True}), 200

    except Exception as e:
        if conn: conn.rollback()
        print(f"ERRO NO UPDATE CLIMA: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()


@app.route('/api/evidencias/vincular', methods=['POST'])
def vincular_evidencia():
    try:
        data = request.json
        conn = get_db_conn()
        cur = conn.cursor()

        # 1. BUSCA O ID_SPEC baseado no nome do componente que veio do Modal
        # Ex: Se veio 'Plano de Aula', ele busca o ID correspondente na ctdi_doc_specs
        componente = data.get('componente')
        cur.execute("SELECT id_spec FROM public.ctdi_doc_specs WHERE nome_componente = %s", (componente,))
        row = cur.fetchone()
        id_spec = row[0] if row else None

        if id_spec is None:
            print(f"⚠️ Aviso: Componente '{componente}' não encontrado na ctdi_doc_specs!")

        # 2. MONTA O DICIONÁRIO incluindo o id_spec
        insert_data = {
            "id_sprn": int(data.get('id_sprn')),
            "id_spec": id_spec,  # Agora o campo não será mais NULL
            "url_evid": data.get('url_evidencia'),
            "componente_vinculado": componente,
            "status_modulador": "Pendente",
            "data_vinculo": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        print(f">>> [MODULADOR] Gravando com Spec ID {id_spec}: {insert_data}")

        # 3. GRAVAÇÃO
        new_id = db_manager.create_record(conn, 'ctdi_evidencias', insert_data)

        cur.close()  # Sempre feche o cursor manual

        return jsonify({"success": True, "id_evid": new_id}), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/evidencias/<int:id_sprn>', methods=['GET'])
def listar_evidencias(id_sprn):
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        # 🔍 CORREÇÃO: Inclusão da coluna analise_ia no final do SELECT
        query = """
                SELECT id_evid, componente_vinculado, url_evid, status_modulador, data_vinculo, analise_ia
                FROM public.ctdi_evidencias
                WHERE id_sprn = %s
                ORDER BY data_vinculo DESC
                """
        cur.execute(query, (id_sprn,))
        rows = cur.fetchall()

        # Formata para JSON
        evidencias = []
        for r in rows:
            evidencias.append({
                "id_evid": r[0],
                "componente_vinculado": r[1],
                "url_evid": r[2],
                "status_modulador": r[3],
                "data_vinculo": r[4].strftime('%Y-%m-%d %H:%M:%S') if r[4] else None,
                "analise_ia": r[5]  # 🔍 CORREÇÃO: Mapeado o retorno da IA para o front-end
            })
        cur.close()
        return jsonify(evidencias), 200
    except Exception as e:
        print(f"❌ Erro ao listar: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/evidencias/<int:id_evid>', methods=['DELETE'])
def deletar_evidencia(id_evid):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM public.ctdi_evidencias WHERE id_evid = %s", (id_evid,))
        conn.commit()
        cur.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rota para o calculo do presurvey 14/05/2026
@app.route('/api/calculate-presurvey', methods=['POST'])
def calculate_presurvey():
    data = request.get_json()
    id_matu = data.get('id_matu')

    print(f"\n>>> [FLASK] Iniciando cálculo Pre-Survey para ID: {id_matu}")

    try:
        conn = get_db_conn()
        cur = conn.cursor()

        # 1. Busca respostas com granularidade de Dimensão e Domínio
        query_respostas = """
                          SELECT q.id_dime, q.id_doma, q.prefu_ques, s.grad_ques
                          FROM public.ctdi_surv s
                                   JOIN public.ctdi_quest q ON s.id_ques = q.id_ques
                          WHERE s.id_matu = %s
                            AND q.presurvey_ques = true
                          """
        cur.execute(query_respostas, (id_matu,))
        respostas = cur.fetchall()

        # 2. Busca Benchmark de Mercado - CORRIGIDO: Incluindo id_doma
        query_bench = """
                      SELECT id_dime,
                             id_doma,
                             AVG((lower(grad_refb) + upper(grad_refb)) / 2) as media_setor
                      FROM public.ctdi_refb
                      WHERE UPPER(setr_refb) IN ('EDUCACAO', 'EDUCAÇÃO', 'EDUCACIONAL', 'SETOR EDUCACAO')
                      GROUP BY id_dime, id_doma
                      ORDER BY id_dime, id_doma
                      """
        cur.execute(query_bench)
        resultados_bench = cur.fetchall()

        # Garante a tipagem limpa convertendo as chaves para tuplas de inteiros puros (int, int)
        bench_map = {(int(r[0]), int(r[1])): float(r[2]) for r in resultados_bench if r[0] is not None and r[1] is not None}

        # LOG DE DEBUG CORRIGIDO
        print(f"\n>>> [DEBUG BENCHMARK]")
        print(f">>> Linhas de benchmark encontradas: {len(resultados_bench)}")
        print(f">>> Dicionário bench_map (primeiros 2 itens): {dict(list(bench_map.items())[:2])}\n")

        # Estruturas para acumular notas
        stats_dime = {i: {'P': [], 'F': []} for i in range(1, 6)}
        stats_doma = {}

        for d_id, doma_id, prefu, nota in respostas:
            if nota is not None and str(nota).lower() != 'na' and d_id is not None and doma_id is not None:
                n = float(nota)
                stats_dime[int(d_id)][prefu.upper()].append(n)

                # Força a chave a ser tupla de inteiros (int, int) para bater com o bench_map
                key = (int(d_id), int(doma_id))
                if key not in stats_doma:
                    stats_doma[key] = {'P': [], 'F': []}
                stats_doma[key][prefu.upper()].append(n)

        def media(lista):
            return sum(lista) / len(lista) if lista else 0.0

        # ==================================================================
        # DICIONÁRIOS DE MAPEAMENTO COMPLETO E CORRIGIDO
        # ==================================================================
        nomes_dimensoes = {
            1: "Estratégica",
            2: "Humana",
            3: "Organizacional",
            4: "Pedagógica",
            5: "Tecnológica"
        }

        nomes_dominios = {
            1: "Estratégia Digital",
            2: "Modelo de Negócio Digital",
            3: "Cultura de Inovação",
            4: "Cultura de Dados",
            5: "Cultura de Colaboração",
            6: "Governança Digital",
            7: "Plataformas Digitais",
            8: "Capacidades Digitais",
            9: "Métricas Digitais",
        }

        # PROCESSAMENTO ESTATÍSTICO E TRADUÇÃO DOS DOMÍNIOS COM TRAVA ANTI-ERRO
        scores_dominios_json = {}
        for key, vals in stats_doma.items():
            id_dime, id_doma = key[0], key[1]

            nome_dime = nomes_dimensoes.get(id_dime, f"Dim {id_dime}")
            nome_doma = nomes_dominios.get(id_doma, f"Dom {id_doma}")

            chav_texto = f"{nome_dime} - {nome_doma}"

            scores_dominios_json[chav_texto] = {
                "P": round(media(vals['P']), 2),
                "F": round(media(vals['F']), 2),
                "M": round(bench_map.get(key, 0.0), 2)
            }

        # 3. Lógica de Identificação de Gaps Críticos (Ambição e Mercado)
        gap_ambicao_max = -1.0
        par_ambicao = (1, 1)

        gap_mercado_max = -1.0
        par_mercado = (1, 1)

        for key, vals in stats_doma.items():
            medP = media(vals['P'])
            medF = media(vals['F'])
            medM = bench_map.get(key, 0)

            g_amb = medF - medP
            if g_amb > gap_ambicao_max:
                gap_ambicao_max = g_amb
                par_ambicao = key

            g_mkt = medM - medP
            if g_mkt > gap_mercado_max:
                gap_mercado_max = g_mkt
                par_mercado = key

        # 4. Busca Nomes e Descrições para as Recomendações
        def get_tech_info(dime, doma):
            cur.execute("""
                        SELECT b.name_bloc, b.desc_bloc, d.name_derv, d.desc_derv
                        FROM public.leaf_bloc b
                                 JOIN public.leaf_derv d ON b.id_bloc = d.id_bloc
                        WHERE b.id_dime = %s
                          AND b.id_doma = %s
                        ORDER BY b.level_bloc ASC
                        LIMIT 1
                        """, (dime, doma))
            res = cur.fetchone()
            return res if res else ("Iniciativa Digital", "Sem descrição", "Plano de Ação", "Sem descrição")

        inf_amb = get_tech_info(*par_ambicao)
        inf_mkt = get_tech_info(*par_mercado)

        # Prepara o JSON unificado
        import json
        insights_data = {
            "recomendas": {
                "ambicao": {
                    "id": par_ambicao,
                    "bloco": inf_amb[0], "desc_b": inf_amb[1],
                    "derv": inf_amb[2], "desc_d": inf_amb[3]
                },
                "mercado": {
                    "id": par_mercado,
                    "bloco": inf_mkt[0], "desc_b": inf_mkt[1],
                    "derv": inf_mkt[2], "desc_d": inf_mkt[3]
                }
            },
            "scores_dominios": scores_dominios_json
        }

        # 5. Insert/Update na ctdi_matu_presurvey
        insert_query = """
                       INSERT INTO public.ctdi_matu_presurvey (id_matu, score_estrat_p, score_estrat_f, score_organiz_p, \
                                                               score_organiz_f, \
                                                               score_humana_p, score_humana_f, score_pedag_p, \
                                                               score_pedag_f, score_tecno_p, score_tecno_f, \
                                                               json_insights) \
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id_matu) DO UPDATE SET score_estrat_p  = EXCLUDED.score_estrat_p, \
                                                           score_estrat_f  = EXCLUDED.score_estrat_f,
                                                           score_organiz_p = EXCLUDED.score_organiz_p, \
                                                           score_organiz_f = EXCLUDED.score_organiz_f,
                                                           score_humana_p  = EXCLUDED.score_humana_p, \
                                                           score_humana_f  = EXCLUDED.score_humana_f,
                                                           score_pedag_p   = EXCLUDED.score_pedag_p, \
                                                           score_pedag_f   = EXCLUDED.score_pedag_f,
                                                           score_tecno_p   = EXCLUDED.score_tecno_p, \
                                                           score_tecno_f   = EXCLUDED.score_tecno_f,
                                                           json_insights   = EXCLUDED.json_insights,
                                                           data_criacao    = CURRENT_TIMESTAMP; \
                       """

        # Prevenção contra falhas de chave vazia nas dimensões principais do radar superior
        valores = (
            id_matu,
            media(stats_dime.get(1, {}).get('P', [])), media(stats_dime.get(1, {}).get('F', [])),
            media(stats_dime.get(2, {}).get('P', [])), media(stats_dime.get(2, {}).get('F', [])),
            media(stats_dime.get(3, {}).get('P', [])), media(stats_dime.get(3, {}).get('F', [])),
            media(stats_dime.get(4, {}).get('P', [])), media(stats_dime.get(4, {}).get('F', [])),
            media(stats_dime.get(5, {}).get('P', [])), media(stats_dime.get(5, {}).get('F', [])),
            json.dumps(insights_data)
        )

        cur.execute(insert_query, valores)
        cur.execute("UPDATE public.ctdi_matu SET status_ia = 'PRESURVEY OK' WHERE id_matu = %s", (id_matu,))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"success": True, "status_ia": "PRESURVEY OK"}), 200

    except Exception as e:
        print(f"❌ [FLASK ERROR] {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/get-presurvey-results/<int:id_matu>', methods=['GET'])
def get_presurvey_results(id_matu):
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        # 1. Checa o status_ia atual na ctdi_matu para decidir a origem dos dados
        cur.execute("SELECT status_ia FROM public.ctdi_matu WHERE id_matu = %s", (id_matu,))
        status_row = cur.fetchone()

        if not status_row:
            cur.close()
            conn.close()
            return jsonify({"error": "Diagnóstico não encontrado"}), 404

        status_atual = (status_row[0] or "").strip().upper()

        # 2. CASO SEJA AVALIACAO OK: Busca as colunas reais da ctdi_matu
        if status_atual == 'AVALIACAO OK' or 'CONCLU' in status_atual:
            query_principal = """
                              SELECT c.empresa_clie,
                                     m.status_ia,
                                     m.pdim_pres,
                                     m.pdim_fut,
                                     m.json_plano_estrategico,
                                     m.pdom_pres,
                                     m.pdom_fut
                              FROM public.ctdi_matu m
                                       JOIN public.ctdi_clie c ON m.id_clie = c.id_clie
                              WHERE m.id_matu = %s
                              """
            cur.execute(query_principal, (id_matu,))
            row = cur.fetchone()

            if not row:
                cur.close()
                conn.close()
                return jsonify({"error": "Dados da avaliação completa não encontrados"}), 404

            import json
            # No fluxo completo, o Python salva pdim_pres/fut e pdom_pres/fut como JSONB nativo ou string serializada
            scores_p = row[2] if isinstance(row[2], dict) else json.loads(row[2] or '{}')
            scores_f = row[3] if isinstance(row[3], dict) else json.loads(row[3] or '{}')

            raw_plano = row[4]
            plano_json = raw_plano if isinstance(raw_plano, dict) else json.loads(raw_plano or '{}')

            # Recuperamos os domínios para manter o Radar de Domínios vivo no relatório completo
            domas_p = row[5] if isinstance(row[5], dict) else json.loads(row[5] or '{}')
            domas_f = row[6] if isinstance(row[6], dict) else json.loads(row[6] or '{}')

            # Remapeia o scores_dominios usando a estrutura calculada que o front espera
            scores_dominios_json = {}
            for dom_id in domas_p.keys():
                chav_texto = f"Dom {dom_id}"
                scores_dominios_json[chav_texto] = {
                    "P": float(domas_p.get(dom_id, 0.0)),
                    "F": float(domas_f.get(dom_id, 0.0)),
                    "M": 0.0  # Pode buscar do bench_map se necessário
                }

            # Injeta os dados das Dimensões mapeados para o contrato do EJS
            pre_data = {
                "score_estrat_p": float(scores_p.get('1', 0.0)), "score_estrat_f": float(scores_f.get('1', 0.0)),
                "score_humana_p": float(scores_p.get('2', 0.0)), "score_humana_f": float(scores_f.get('2', 0.0)),
                "score_organiz_p": float(scores_p.get('3', 0.0)), "score_organiz_f": float(scores_f.get('3', 0.0)),
                "score_pedag_p": float(scores_p.get('4', 0.0)), "score_pedag_f": float(scores_f.get('4', 0.0)),
                "score_tecno_p": float(scores_p.get('5', 0.0)), "score_tecno_f": float(scores_f.get('5', 0.0)),
                "json_insights": {
                    "recomendas": plano_json.get('recomendas', {}),
                    "scores_dominios": scores_dominios_json
                }
            }

        # CASO SEJA UM STATUS DE PRE-SURVEY: Busca na ctdi_matu_presurvey
        else:
            query_principal = """
                              SELECT c.empresa_clie,
                                     m.status_ia,
                                     p.score_estrat_p, \
                                     p.score_estrat_f,
                                     p.score_organiz_p, \
                                     p.score_organiz_f,
                                     p.score_humana_p, \
                                     p.score_humana_f,
                                     p.score_pedag_p, \
                                     p.score_pedag_f,
                                     p.score_tecno_p, \
                                     p.score_tecno_f,
                                     p.json_insights
                              FROM public.ctdi_matu m
                                       JOIN public.ctdi_clie c ON m.id_clie = c.id_clie
                                       JOIN public.ctdi_matu_presurvey p ON m.id_matu = p.id_matu
                              WHERE m.id_matu = %s
                              """
            cur.execute(query_principal, (id_matu,))
            row = cur.fetchone()

            if not row:
                cur.close()
                conn.close()
                return jsonify({"error": "Diagnóstico prévio não encontrado"}), 404

            import json
            raw_insights = row[12]
            insights = raw_insights if isinstance(raw_insights, dict) else json.loads(raw_insights or '{}')

            pre_data = {
                "score_estrat_p": float(row[2]), "score_estrat_f": float(row[3]),
                "score_organiz_p": float(row[4]), "score_organiz_f": float(row[5]),
                "score_humana_p": float(row[6]), "score_humana_f": float(row[7]),
                "score_pedag_p": float(row[8]), "score_pedag_f": float(row[9]),
                "score_tecno_p": float(row[10]), "score_tecno_f": float(row[11]),
                "json_insights": insights
            }

        # 3. Processamento de Recomendações e Benchmarks comuns
        insights_obj = pre_data["json_insights"]
        recomendas = insights_obj.get('recomendas', {})

        query_benchmark = """
                          SELECT id_dime,
                                 AVG((lower(grad_refb) + upper(grad_refb)) / 2) as media_setor
                          FROM public.ctdi_refb
                          WHERE UPPER(setr_refb) IN ('EDUCACAO', 'EDUCAÇÃO', 'EDUCACIONAL', 'SETOR EDUCACAO')
                          GROUP BY id_dime
                          ORDER BY id_dime
                          """
        cur.execute(query_benchmark)
        ref_rows = cur.fetchall()
        ref_setor = {int(r[0]): float(r[1]) for r in ref_rows}

        # 4. Resposta padronizada em conformidade com o contrato original do front-end
        response = {
            "lead": {
                "id_matu": id_matu,
                "empresa_clie": row[0],
                "status_ia": row[1]
            },
            "preData": pre_data,
            "refSetor": ref_setor,
            "insights_ia": {
                "ambicao": recomendas.get('ambicao', {
                    "bloco": "Iniciativa de Evolução", "desc_b": "Análise pendente",
                    "derv": "Plano de Ação", "desc_d": "Detalhes em breve"
                }),
                "mercado": recomendas.get('mercado', {
                    "bloco": "Ajuste Competitivo", "desc_b": "Análise de mercado pendente",
                    "derv": "Sprint de Reação", "desc_d": "Detalhes em breve"
                })
            }
        }

        cur.close()
        conn.close()
        return jsonify(response), 200

    except Exception as e:
        print(f"❌ Erro em get_presurvey_results corrigido: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



#Endpoints estratégicos....
# ==============================================================================
# ENDPOINTS DO MÓDULO DE GOVERNANÇA ESTRATÉGICA (OKR ORGANIZACIONAL)
# ==============================================================================

@app.route('/api/okr/consolidado', methods=['GET'])
def get_okr_consolidado():
    """
    Retorna a árvore hierárquica completa (Direcionadores -> Objetivos -> KRs)
    de um determinado cliente para alimentar a interface okr.ejs.
    """
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        id_clie = request.args.get('id_clie')
        if not id_clie:
            return jsonify({"error": "O parâmetro 'id_clie' é obrigatório."}), 400

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Query mestre que consolida a estrutura macro de metas e KPIs
        query = """
                SELECT d.id_direc, \
                       d.nome_direc, \
                       d.desc_direc, \
                       d.kpi_descricao as direc_kpi, \
                       d.meta_receita_alvo, \
                       d.meta_custo_alvo, \
                       d.status_direc, \
                       o.id_obj_dt, \
                       o.nome_obj, \
                       o.desc_obj, \
                       o.kpi_descricao as obj_kpi, \
                       o.status_obj, \
                       k.id_kr, \
                       k.nome_kr, \
                       k.desc_kr, \
                       k.kpi_nome      as kr_kpi, \
                       k.valor_inicial, \
                       k.valor_alvo, \
                       k.valor_atual, \
                       k.status_kr
                FROM public.ctdi_okr_direcionadores d
                         LEFT JOIN public.ctdi_okr_objetivos_dt o ON d.id_direc = o.id_direc
                         LEFT JOIN public.ctdi_okr_krs k ON o.id_obj_dt = k.id_obj_dt
                WHERE d.id_clie = %s
                ORDER BY d.id_direc ASC, o.id_obj_dt ASC, k.id_kr ASC; \
                """

        cur.execute(query, (id_clie,))
        rows = cur.fetchall()
        cur.close()

        # CORREÇÃO: Varre as linhas convertendo os tipos Decimal para Float amigáveis ao JSON
        for row in rows:
            if row['meta_receita_alvo'] is not None: row['meta_receita_alvo'] = float(row['meta_receita_alvo'])
            if row['meta_custo_alvo'] is not None: row['meta_custo_alvo'] = float(row['meta_custo_alvo'])
            if row['valor_inicial'] is not None: row['valor_inicial'] = float(row['valor_inicial'])
            if row['valor_alvo'] is not None: row['valor_alvo'] = float(row['valor_alvo'])
            if row['valor_atual'] is not None: row['valor_atual'] = float(row['valor_atual'])

        return jsonify(rows), 200

    except Exception as e:
        print(f"❌ Erro ao processar árvore consolidada de OKR: {e}", file=sys.stderr)
        return jsonify({"error": f"Erro interno ao buscar dados estratégicos: {str(e)}"}), 500
    finally:
        if conn: conn.close()


@app.route('/api/okr/direcionadores', methods=['POST'])
def handle_direcionadores():
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        data = request.json
        if not data or 'id_clie' not in data:
            return jsonify({"error": "Dados incompletos. 'id_clie' é obrigatório."}), 400

        # Executa a escrita diretamente
        db_manager.create_record(conn, 'ctdi_okr_direcionadores', data)

        # Se não disparou o except abaixo, a gravação foi concluída com sucesso!
        return jsonify({"success": True, "message": "Direcionador criado com sucesso!"}), 201

    except Exception as e:
        print(f"Erro ao inserir direcionador: {e}", file=sys.stderr)
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/okr/objetivos', methods=['POST'])
def handle_objetivos():
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        data = request.json
        if not data or 'id_direc' not in data:
            return jsonify({"error": "Mapeamento incorreto. 'id_direc' é obrigatório."}), 400

        # Executa a escrita diretamente
        db_manager.create_record(conn, 'ctdi_okr_objetivos_dt', data)

        # Sucesso baseado em execução limpa
        return jsonify({"success": True, "message": "Objetivo de TD vinculado com sucesso!"}), 201

    except Exception as e:
        print(f"Erro ao inserir objetivo: {e}", file=sys.stderr)
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/okr/krs', methods=['POST'])
def handle_krs():
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        data = request.json
        if not data or 'id_obj_dt' not in data:
            return jsonify({"error": "Alinhamento corrompido. 'id_obj_dt' é obrigatório."}), 400

        # Executa a escrita diretamente
        db_manager.create_record(conn, 'ctdi_okr_krs', data)

        # Sucesso baseado em execução limpa
        return jsonify({"success": True, "message": "Key Result estabelecido com sucesso!"}), 201

    except Exception as e:
        print(f"Erro ao inserir KR: {e}", file=sys.stderr)
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/okr/atividades', methods=['GET', 'POST'])
def handle_atividades():
    """
    Gerenciamento do Nível 4: Atividades operacionais vinculadas às Sprints
    """
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRÍTICO ao obter conexão com DB: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            id_sprn = request.args.get('id_sprn')
            if id_sprn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                query = "SELECT * FROM public.ctdi_okr_atividades WHERE id_sprn = %s ORDER BY id_ativ ASC"
                cur.execute(query, (id_sprn,))
                records = cur.fetchall()
                cur.close()
            else:
                records = db_manager.read_all_records(conn, 'ctdi_okr_atividades')
            return jsonify(records), 200

        elif request.method == 'POST':
            data = request.json
            new_id = db_manager.create_record(conn, 'ctdi_okr_atividades', data)
            if new_id:
                return jsonify({"message": "Atividade operacional vinculada à Sprint!", "id": new_id}), 201
            return jsonify({"error": "Não foi possível registrar a atividade."}), 500

    except Exception as e:
        print(f"Erro ao processar atividades operacionais: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500


@app.route('/api/okr/<string:entity_type>/<int:record_id>', methods=['PUT', 'DELETE'])
def handle_single_okr_entity(entity_type, record_id):
    """
    Endpoint dinâmico para Atualização (PUT) e Deleção (DELETE) dos 3 níveis do OKR.
    entity_type aceita: 'direcionadores', 'objetivos' ou 'krs'
    """
    table_map = {
        "direcionadores": "ctdi_okr_direcionadores",
        "objetivos": "ctdi_okr_objetivos_dt",
        "krs": "ctdi_okr_krs"
    }

    table_name = table_map.get(entity_type)
    if not table_name:
        return jsonify({"error": "Entidade estratégica inválida."}), 400

    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro ao conectar ao banco no ciclo CRUD OKR: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500

    try:
        if request.method == 'PUT':
            data = request.json
            if db_manager.update_record(conn, table_name, record_id, data):
                return jsonify({"success": True, "message": "Registro atualizado com sucesso!"}), 200
            return jsonify({"error": "Não foi possível atualizar o registro estratégico."}), 500

        elif request.method == 'DELETE':
            if db_manager.delete_record(conn, table_name, record_id):
                return jsonify({"success": True, "message": "Registro removido com sucesso!"}), 200
            return jsonify({"error": "Registro não encontrado ou já removido."}), 404

    except Exception as e:
        print(f"❌ Erro na operação {request.method} para {table_name}: {e}", file=sys.stderr)
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/okr/admin/dashboard', methods=['GET'])
def get_okr_admin_dashboard():
    """
    Retorna o painel consolidado de OKRs de todos os clientes cadastrados para a visão do Admin.
    Calcula a volumetria de objetivos e o progresso médio ponderado usando a ctdi_clie.
    """
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro de conexão no dashboard do Admin: {e}", file=sys.stderr)
        return jsonify({"error": "Erro de conexão com o banco."}), 500

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Query ajustada para refletir public.ctdi_clie e nome_clie
        query = """
                SELECT c.id_clie, \
                       c.nome_clie                 AS nome_cliente, \
                       COUNT(DISTINCT o.id_obj_dt) AS qde_objetivos, \
                       COALESCE( \
                               AVG( \
                                       CASE \
                                           WHEN (k.valor_alvo - k.valor_inicial) <> 0 \
                                               THEN LEAST(100, GREATEST(0, (ABS(k.valor_atual - k.valor_inicial) / \
                                                                            ABS(k.valor_alvo - k.valor_inicial)) * 100)) \
                                           ELSE 0 \
                                           END \
                               ), 0 \
                       )                           AS progresso_medio
                FROM public.ctdi_clie c
                         LEFT JOIN public.ctdi_okr_direcionadores d ON c.id_clie = d.id_clie
                         LEFT JOIN public.ctdi_okr_objetivos_dt o ON d.id_direc = o.id_direc
                         LEFT JOIN public.ctdi_okr_krs k ON o.id_obj_dt = k.id_obj_dt
                GROUP BY c.id_clie, c.nome_clie
                ORDER BY progresso_medio DESC, c.nome_clie ASC; \
                """
        cur.execute(query)
        dashboard_data = cur.fetchall()
        cur.close()

        # Normalização matemática para o JSON
        for row in dashboard_data:
            row['progresso_medio'] = round(float(row['progresso_medio']), 1)

        return jsonify(dashboard_data), 200

    except Exception as e:
        print(f"❌ Erro ao processar query agregada do Admin: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# --- Bloco de inicialização da aplicação (COM DESPERTAR DO WORKER) ---
# if __name__ == '__main__':
#     test_conn = None
#     try:
#         # 3. MUDANÇA CRÍTICA: Testa a conexão usando o novo método _connect_db()
#         test_conn = db_manager._connect_db()
#
#         # --- NOVO: Acionamento Automático do Worker ---
#         if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
#             try:
#                 # Localiza o caminho do worker relativo ao app.py
#                 base_path = os.path.dirname(os.path.abspath(__file__))
#                 worker_path = os.path.join(base_path, 'ai_engine', 'worker.py')
#
#                 # Inicia o processo independente
#                 subprocess.Popen([sys.executable, worker_path])
#                 print("🛰️  [SISTEMA] Worker IA despertado e operando em background.", file=sys.stderr)
#             except Exception as worker_err:
#                 print(f"⚠️  [AVISO] Falha ao iniciar o Worker: {worker_err}", file=sys.stderr)
#         # ----------------------------------------------
#
#         with app.app_context():
#             print("--- ROTAS DO FLASK CONFIGURADAS ---", file=sys.stderr)
#             for rule in app.url_map.iter_rules():
#                 print(f"Endpoint: {rule.endpoint} | Methods: {rule.methods} | Path: {rule}", file=sys.stderr)
#             print("-----------------------------------", file=sys.stderr)
#
#         print("Backend do LeAction SysF iniciado e conectado ao banco de dados.")
#         app.run(debug=True, port=5000)
#
#     except Exception as e:
#         print(
#             f"Não foi possível iniciar o backend devido a um erro de conexão com o banco de dados: {e}.",
#             file=sys.stderr)
#     finally:
#         if test_conn:
#             test_conn.close()

if __name__ == '__main__':
    # 1. Verifica se o banco está acessível antes de subir o ecossistema
    try:
        with db_manager._connect_db() as conn:
            print("✅ Conexão com banco de dados validada.")
    except Exception as e:
        print(f"❌ Erro fatal: Banco inacessível: {e}")
        sys.exit(1)  # Para a execução imediatamente se o banco não responder

    # 2. DISPARO SINDICALIZADO DOS WORKERS (Master & Modulador)
    # Se estivermos em modo debug, usamos o check do Werkzeug para evitar spawn duplo.
    # Se estivermos em produção (Docker/AWS), a flag garante a execução única.
    is_main_process = os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug

    if is_main_process:
        base_path = os.path.dirname(os.path.abspath(__file__))

        # --- MOTOR 1: DISPARO DO WORKER MASTER (Gênese do Plano IA) ---
        try:
            worker_path = os.path.join(base_path, 'ai_engine', 'worker.py')
            # Roda o worker com o mesmo interpretador atual e repassa as variáveis de ambiente
            subprocess.Popen([sys.executable, worker_path], env=os.environ.copy())
            print("🛰️  [SISTEMA] Worker IA Master despertado.", file=sys.stderr)
        except Exception as worker_err:
            print(f"⚠️  Falha ao iniciar o Worker Master: {worker_err}", file=sys.stderr)

        # --- MOTOR 2: DISPARO DO WORKER MODULADOR (Auditoria & Impacto Financeiro) ---
        try:
            modulador_path = os.path.join(base_path, 'ai_engine', 'modulador_worker.py')
            # Dispara de forma assíncrona e isolada em background
            subprocess.Popen([sys.executable, modulador_path], env=os.environ.copy())
            print("🤖 [SISTEMA] Worker Agente Modulador despertado com sucesso.", file=sys.stderr)
        except Exception as modulador_err:
            print(f"⚠️  Falha ao iniciar o Worker Modulador: {modulador_err}", file=sys.stderr)

    # 3. START DO SERVIDOR FLASK
    # host='0.0.0.0' é vital para o mapeamento de portas de entrada do Docker/AWS
    app.run(debug=True, port=5000, host='0.0.0.0')