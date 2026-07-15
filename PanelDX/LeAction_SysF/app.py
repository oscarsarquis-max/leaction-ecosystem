
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
import re
import statistics
import base64
import hashlib
import hmac
from html import unescape
from database import LeactionCRUD, generate_random_code
import boto3
import subprocess
import time
import threading
from datetime import datetime
from functools import lru_cache
from botocore.exceptions import ClientError
from botocore.config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Carrega o .env logo no import para que TODAS as configs abaixo
# (secret_key, DB_CONFIG, Bedrock) enxerguem as variáveis em dev.
# Em produção (ECS/Fargate) as variáveis vêm do ambiente e isto é no-op.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

app = Flask(__name__)
# Segredo de sessão do Flask: lê do ambiente; fallback apenas para dev local.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-troque-em-producao')
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
            "http://localhost:4000",
            "http://localhost:4001",
            "https://paneldx.com.br",
            "https://actionhub.com.br",
            "https://www.actionhub.com.br",
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
#     "password": os.environ.get("DB_PASSWORD"), # Não use fallback para senha, a injeção deve ser obrigatória
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

    # Senha exclusivamente via ambiente (DB_PASSWORD ou DB_PASS). Sem fallback
    # hardcoded — falha cedo e de forma explícita se a variável não existir.
    "password": env_pass,

    # Se estiver na AWS e não houver HOST, precisamos do IP da instância, não 127.0.0.1
    "host": os.environ.get("DB_HOST", "127.0.0.1"),

    "port": int(os.environ.get("DB_PORT", 5432)),
    "sslmode": os.environ.get("DB_SSLMODE", "disable")
}

db_manager = LeactionCRUD(**DB_CONFIG)

# =========================================================================
# CONFIG BEDROCK — modelo único e configurável
# O Claude 3.5 Sonnet (20240620) foi descontinuado pela AWS (ResourceNotFound).
# Usa-se o mesmo inference profile que os workers já utilizam com sucesso.
# Sobrescrevível via env BEDROCK_MODEL_ID / BEDROCK_REGION.
# =========================================================================
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
BEDROCK_BOTO_CONFIG = Config(
    connect_timeout=6,
    read_timeout=20,
    retries={'max_attempts': 1},
)
MODERADOR_BEDROCK_TIMEOUT_S = int(os.environ.get('MODERADOR_BEDROCK_TIMEOUT_S', '22'))


def _extrair_json_da_resposta(texto):
    """Extrai um objeto JSON da resposta do modelo de forma tolerante.

    Modelos recentes (Claude 4) às vezes envolvem o JSON em cercas markdown
    (```json ... ```) ou adicionam texto antes/depois. Aqui removemos as cercas
    e, em último caso, recortamos do primeiro '{' ao último '}'.
    Lança json.JSONDecodeError se nada parseável for encontrado.
    """
    import re as _re
    if texto is None:
        raise ValueError("Resposta vazia do modelo.")
    limpo = texto.strip()

    # Remove cercas markdown ```json ... ``` ou ``` ... ```
    cerca = _re.match(r"^```(?:json)?\s*(.*?)\s*```$", limpo, _re.DOTALL | _re.IGNORECASE)
    if cerca:
        limpo = cerca.group(1).strip()

    try:
        return json.loads(limpo)
    except json.JSONDecodeError:
        inicio = limpo.find('{')
        fim = limpo.rfind('}')
        if inicio != -1 and fim != -1 and fim > inicio:
            return json.loads(limpo[inicio:fim + 1])
        raise

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

# Proxy PLG Tracking → Action Hub (não persiste no PanelDX)
try:
    from routes.tracking_proxy import tracking_bp
    app.register_blueprint(tracking_bp)
except Exception as e:
    print(f"⚠️ ALERTA: Proxy CRM tracking não carregado: {e}", file=sys.stderr)

# Rotas /api/* do subsistema inovador no app principal — ALB envia /api/* ao Flask em produção
try:
    from routes.inovador_routes import register_paneldx_public_api_routes
    register_paneldx_public_api_routes(app)
except Exception as e:
    print(f"⚠️ ALERTA: Rotas públicas /api (Mesa/Kanban DX) não registradas: {e}", file=sys.stderr)

# Integração eSIM (telemetria agnóstica a provedores) — módulo desacoplado
try:
    from integrations.esim.webhook import register_esim_routes
    register_esim_routes(app)
except Exception as e:
    print(f"⚠️ ALERTA: Integração eSIM não carregada: {e}", file=sys.stderr)
    traceback.print_exc()

# RBAC — papéis, execução, notificações
try:
    from rbac.routes import register_rbac_routes
    register_rbac_routes(app)
except Exception as e:
    print(f"⚠️ ALERTA: Rotas RBAC não carregadas: {e}", file=sys.stderr)
    traceback.print_exc()

try:
    from rbac.admin_users import register_admin_users_routes
    register_admin_users_routes(app)
except Exception as e:
    print(f"⚠️ ALERTA: Rotas admin usuários não carregadas: {e}", file=sys.stderr)
    traceback.print_exc()

try:
    from routes.estrategia import register_estrategia_routes
    register_estrategia_routes(app)
except Exception as e:
    print(f"⚠️ ALERTA: Rotas estratégia (matriz OKR) não carregadas: {e}", file=sys.stderr)
    traceback.print_exc()

try:
    from routes.crm import register_crm_routes
    register_crm_routes(app)
except Exception as e:
    print(f"⚠️ ALERTA: Rotas CRM/contratos não carregadas: {e}", file=sys.stderr)
    traceback.print_exc()

try:
    from routes.consultor import register_consultor_routes
    register_consultor_routes(app)
except Exception as e:
    print(f"⚠️ ALERTA: Rotas Portal do Consultor não carregadas: {e}", file=sys.stderr)
    traceback.print_exc()

try:
    from rbac.contract_access import register_contract_access_middleware
    register_contract_access_middleware(app)
except Exception as e:
    print(f"⚠️ ALERTA: Middleware de contrato não carregado: {e}", file=sys.stderr)
    traceback.print_exc()

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
        if grad_ques is None:
            continue
        if isinstance(grad_ques, str) and grad_ques.strip().lower() in ('na', 'null', ''):
            continue
        try:
            grad_val = float(grad_ques)
        except (TypeError, ValueError):
            continue
        respostas_por_dominio.setdefault(answer['id_doma'], []).append(grad_val)
        respostas_por_dimensao.setdefault(answer['id_dime'], []).append(grad_val)

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


MATRIX_CV_ALPHA = 0.4
MATRIX_WEAKNESS_BETA = 0.25


def _normalize_prefu(prefu_raw):
    prefu = (prefu_raw or '').strip().upper()
    if prefu in ('P', 'PRESENTE') or prefu.startswith('P'):
        return 'P'
    if prefu in ('F', 'FUTURO') or prefu.startswith('F'):
        return 'F'
    return ''


def compute_matrix_domain_stats(answers_list, alpha=None, beta=None):
    """
    Estatísticas por domínio para a matriz híbrida: CV, elo fraco e realidade ajustada.
    """
    alpha = MATRIX_CV_ALPHA if alpha is None else alpha
    beta = MATRIX_WEAKNESS_BETA if beta is None else beta

    by_dom_pres = {}
    by_dom_fut = {}
    by_dom_ques = {}

    for answer in answers_list:
        grad_ques = answer.get('grad_ques')
        if grad_ques is None:
            continue
        if isinstance(grad_ques, str) and grad_ques.strip().lower() in ('na', 'null', ''):
            continue
        try:
            grad_val = float(grad_ques)
        except (TypeError, ValueError):
            continue

        raw_doma = answer.get('id_doma')
        if raw_doma is None:
            continue
        id_doma = str(raw_doma)
        if not id_doma or id_doma == 'None':
            continue

        prefu = _normalize_prefu(answer.get('prefu_ques'))
        id_ques = str(answer.get('id_ques') or '')
        ques_bucket = by_dom_ques.setdefault(id_doma, {}).setdefault(id_ques, {})

        if prefu == 'P':
            by_dom_pres.setdefault(id_doma, []).append(grad_val)
            ques_bucket['P'] = grad_val
        elif prefu == 'F':
            by_dom_fut.setdefault(id_doma, []).append(grad_val)
            ques_bucket['F'] = grad_val

    all_domains = set(by_dom_pres.keys()) | set(by_dom_fut.keys())
    result = {}

    for id_doma in all_domains:
        pres_vals = by_dom_pres.get(id_doma, [])
        fut_vals = by_dom_fut.get(id_doma, [])
        ques_map = by_dom_ques.get(id_doma, {})

        mean_pres = round(sum(pres_vals) / len(pres_vals), 2) if pres_vals else 0.0
        mean_fut = round(sum(fut_vals) / len(fut_vals), 2) if fut_vals else 0.0
        min_pres = round(min(pres_vals), 2) if pres_vals else 0.0
        max_pres = round(max(pres_vals), 2) if pres_vals else 0.0
        min_fut = round(min(fut_vals), 2) if fut_vals else 0.0
        max_fut = round(max(fut_vals), 2) if fut_vals else 0.0
        range_pres = round(max_pres - min_pres, 2) if pres_vals else 0.0
        std_pres = round(statistics.stdev(pres_vals), 3) if len(pres_vals) > 1 else 0.0
        cv_pres = round(std_pres / mean_pres, 3) if mean_pres > 0 else 0.0

        block_gaps = []
        for ques_vals in ques_map.values():
            if 'P' in ques_vals and 'F' in ques_vals:
                block_gaps.append(ques_vals['F'] - ques_vals['P'])
        block_gap_std = round(statistics.stdev(block_gaps), 3) if len(block_gaps) > 1 else 0.0
        block_gap_range = round(max(block_gaps) - min(block_gaps), 2) if block_gaps else 0.0

        weakness_gap = max(0.0, mean_pres - min_pres)
        cv_penalty = alpha * cv_pres
        weakness_penalty = beta * weakness_gap
        adjusted_reality = round(
            max(0.0, min(5.0, mean_pres - cv_penalty - weakness_penalty)), 2
        )
        gap = round(max(0.0, mean_fut - mean_pres), 2)

        frag_components = [
            min(1.0, range_pres / 2.0),
            min(1.0, std_pres / 1.0),
            min(1.0, cv_pres / 0.30),
            min(1.0, gap / 1.5),
            min(1.0, block_gap_std / 1.0),
            min(1.0, block_gap_range / 2.0),
            min(1.0, weakness_gap / 1.5),
        ]
        fragmentation_index = round(max(frag_components), 3)

        result[id_doma] = {
            "mean_pres": mean_pres,
            "mean_fut": mean_fut,
            "min_pres": min_pres,
            "max_pres": max_pres,
            "min_fut": min_fut,
            "max_fut": max_fut,
            "range_pres": range_pres,
            "std_pres": std_pres,
            "cv_pres": cv_pres,
            "block_count_pres": len(pres_vals),
            "block_gap_std": block_gap_std,
            "block_gap_range": block_gap_range,
            "adjusted_reality": adjusted_reality,
            "gap": gap,
            "cv_penalty": round(cv_penalty, 3),
            "weakness_penalty": round(weakness_penalty, 3),
            "fragmentation_index": fragmentation_index,
        }

    return result


def build_matrix_meta(matrix_domain_stats):
    """Medianas dinâmicas dos domínios para divisão de quadrantes."""
    ambitions = [s["mean_fut"] for s in matrix_domain_stats.values() if s.get("mean_fut", 0) > 0]
    realities = [
        s["adjusted_reality"] for s in matrix_domain_stats.values() if s.get("adjusted_reality", 0) > 0
    ]

    return {
        "median_ambition": round(statistics.median(ambitions), 2) if ambitions else 2.5,
        "median_reality_adjusted": round(statistics.median(realities), 2) if realities else 2.5,
        "alpha_cv": MATRIX_CV_ALPHA,
        "beta_weakness": MATRIX_WEAKNESS_BETA,
        "model": "hybrid",
    }

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
                'zipn_clie', 'bairro_clie', 'cidade_clie', 'estado_clie',
                'empresa_clie', 'tipo_ensino', 'qtd_alunos',
                'qtd_colaboradores', 'qtd_unidades', 'localizacao_sede',
                'rede_ensino', 'clima_organizacional', 'dados_etnograficos', 'dados_mercado',
                'moderacao_dados_mercado', 'moderacao_dados_etnograficos',
                'moderacao_clima_organizacional',
                'has_active_project',
                'init_role', 'justificativa_solo',
                'id_rede', 'is_holding'
            ]

            clie_payload = {}
            for col in valid_columns:
                val = data.get(col) if data.get(col) is not None else data.get(col.upper())
                if val is not None:
                    clie_payload[col] = val

            # 🧠 3. TRAVAS INTELIGENTES DE INTEGRIDADE CONTRA CAMPOS NOT NULL
            # Captura a role para saber se aplica os fallbacks corporativos ou limpa para o Inovador
            current_role = clie_payload.get('init_role', 'GENERAL').strip().upper()
            is_solo = current_role == 'SOLO'

            # Normalização + validação de e-mail, telefone, CNPJ e CEP
            from validators_br import (
                format_br_phone,
                format_cep,
                format_cnpj,
                only_digits,
                validate_lead_signup,
            )
            if clie_payload.get('mail_clie'):
                clie_payload['mail_clie'] = str(clie_payload['mail_clie']).strip().lower()
            if clie_payload.get('fone_clie'):
                clie_payload['fone_clie'] = format_br_phone(clie_payload.get('fone_clie'))
            if not is_solo:
                if clie_payload.get('docu_clie'):
                    clie_payload['docu_clie'] = format_cnpj(clie_payload.get('docu_clie'))
                if clie_payload.get('zipn_clie'):
                    clie_payload['zipn_clie'] = format_cep(clie_payload.get('zipn_clie'))

            signup_errors = validate_lead_signup(clie_payload, is_solo=is_solo)
            if signup_errors:
                return jsonify({"error": signup_errors[0], "errors": signup_errors}), 400

            if is_solo:
                # Se for Inovador Solo, garantimos que os campos corporativos fiquem limpos/nulos como na UI
                clie_payload['empresa_clie'] = "Autônomo / Inovador Solo"
                if not clie_payload.get('docu_clie') or only_digits(clie_payload.get('docu_clie')) in ('', '00000000000100'):
                    clie_payload['docu_clie'] = "00.000.000/0001-00"  # Evita quebra de NOT NULL se houver constraint
            else:
                # Caso contrário (GENERAL), não aceita CNPJ/CEP placeholder genéricos
                if not clie_payload.get('empresa_clie'):
                    return jsonify({"error": "Informe a instituição / razão social."}), 400
                if only_digits(clie_payload.get('docu_clie')) == '00000000000100':
                    return jsonify({"error": "Informe um CNPJ institucional válido."}), 400

            # Evita cadastro duplicado: reenvia o código existente
            mail_informado = (clie_payload.get('mail_clie') or '').strip()
            if mail_informado:
                dup_cur = conn.cursor()
                dup_cur.execute(
                    """
                    SELECT c.id_clie, a.access_code
                    FROM public.ctdi_clie c
                    LEFT JOIN public.ctdi_lead_access a ON a.id_clie = c.id_clie
                    WHERE LOWER(TRIM(c.mail_clie)) = LOWER(TRIM(%s))
                    LIMIT 1
                    """,
                    (mail_informado,),
                )
                existente = dup_cur.fetchone()
                dup_cur.close()
                if existente:
                    id_existente, codigo_existente = existente
                    if not codigo_existente:
                        codigo_existente = _gerar_codigo_acesso_la()
                        db_manager.create_record(conn, 'ctdi_lead_access', {
                            "id_clie": id_existente,
                            "access_code": codigo_existente,
                        })
                        conn.commit()
                        dispatch_access_code_email(mail_informado, codigo_existente)
                        return jsonify({
                            "message": (
                                f"Este e-mail já possui cadastro. Enviamos o código de acesso para {mail_informado}."
                            ),
                            "id": id_existente,
                            "resent": True,
                        }), 200
                    return jsonify({
                        "message": (
                            "Este e-mail já possui cadastro. Utilize o código de acesso "
                            "enviado no momento do cadastro."
                        ),
                        "id": id_existente,
                        "resent": False,
                    }), 200

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

                # Funil de vendas: tracking ?ref= / ?invite= OU lead órfão automático
                try:
                    from services.funil_engine import (
                        associar_cadastro_com_ref,
                        garantir_oportunidade_orfao,
                    )
                    from psycopg2.extras import RealDictCursor as _RDC
                    _funil_cur = conn.cursor(cursor_factory=_RDC)
                    ref_code = (data.get('ref') or data.get('ref_code') or '').strip() or None
                    invite_token = (data.get('invite') or data.get('invite_token') or '').strip() or None
                    associado = None
                    if current_role != 'SOLO' and (ref_code or invite_token):
                        associado = associar_cadastro_com_ref(
                            _funil_cur,
                            id_clie=int(new_id),
                            id_matu=int(new_id_matu),
                            ref_code=ref_code,
                            invite_token=invite_token,
                            nome=clie_payload.get('nome_clie'),
                            email=clie_payload.get('mail_clie'),
                            telefone=clie_payload.get('fone_clie'),
                            empresa=clie_payload.get('empresa_clie'),
                        )
                    if current_role != 'SOLO' and not associado:
                        garantir_oportunidade_orfao(
                            _funil_cur,
                            id_clie=int(new_id),
                            id_matu=int(new_id_matu),
                            nome=clie_payload.get('nome_clie'),
                            email=clie_payload.get('mail_clie'),
                            telefone=clie_payload.get('fone_clie'),
                            empresa=clie_payload.get('empresa_clie'),
                        )
                    _funil_cur.close()
                except Exception as funil_err:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    print(f"⚠️ [FUNIL] Falha ao registrar oportunidade no cadastro: {funil_err}", file=sys.stderr)

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
                        print(
                            f"📧 [SES] Agendando e-mail para {destinatario} com código {access_code}...",
                            file=sys.stderr,
                        )
                        dispatch_access_code_email(destinatario, access_code)
                    except Exception as email_err:
                        print(f"❌ [SES ERRO] Falha ao agendar e-mail: {email_err}", file=sys.stderr)
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
            _ensure_contexto_columns(conn)
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
        data = request.json or {}
        id_clie = data.get('id_clie')
        if not id_clie:
            return jsonify({"error": "id_clie obrigatório"}), 400

        conn = get_db_conn()
        _ensure_contexto_columns(conn)
        cursor = conn.cursor()

        cidade = (data.get('cidade_clie') or '').strip()
        estado = (data.get('estado_clie') or '').strip()
        localizacao = (data.get('localizacao_sede') or '').strip()
        if not localizacao and cidade and estado:
            localizacao = f"{cidade} - {estado}"

        obrigatorios = {
            'tipo_ensino': data.get('tipo_ensino'),
            'qtd_alunos': data.get('qtd_alunos'),
            'zipn_clie': data.get('zipn_clie'),
            'adre_clie': data.get('adre_clie'),
            'dados_mercado': data.get('dados_mercado'),
            'dados_etnograficos': data.get('dados_etnograficos'),
            'clima_organizacional': data.get('clima_organizacional'),
        }
        faltando = [k for k, v in obrigatorios.items() if v is None or str(v).strip() == '']
        if faltando:
            return jsonify({
                "error": "Preencha todos os campos obrigatórios do contexto institucional.",
                "missing": faltando,
            }), 400

        cursor.execute(
            """
            SELECT moderacao_dados_mercado,
                   moderacao_dados_etnograficos,
                   moderacao_clima_organizacional
            FROM ctdi_clie
            WHERE id_clie = %s
            """,
            (id_clie,),
        )
        mod_existente = cursor.fetchone() or (None, None, None)

        def _moderacao_efetiva(chave, indice):
            valor = data.get(chave)
            if valor is not None and str(valor).strip():
                return valor
            return mod_existente[indice]

        mod_mercado = _moderacao_efetiva('moderacao_dados_mercado', 0)
        mod_etno = _moderacao_efetiva('moderacao_dados_etnograficos', 1)
        mod_clima = _moderacao_efetiva('moderacao_clima_organizacional', 2)

        cursor.execute("""
                       UPDATE ctdi_clie
                       SET tipo_ensino                        = %s,
                           qtd_alunos                         = %s,
                           qtd_colaboradores                  = %s,
                           qtd_unidades                       = %s,
                           localizacao_sede                   = %s,
                           rede_ensino                        = %s,
                           clima_organizacional               = %s,
                           adre_clie                          = %s,
                           zipn_clie                          = %s,
                           bairro_clie                        = %s,
                           cidade_clie                        = %s,
                           estado_clie                        = %s,
                           dados_etnograficos                 = %s,
                           dados_mercado                      = %s,
                           moderacao_dados_mercado            = %s,
                           moderacao_dados_etnograficos       = %s,
                           moderacao_clima_organizacional     = %s
                       WHERE id_clie = %s
                       """, (
            data.get('tipo_ensino'),
            data.get('qtd_alunos'),
            data.get('qtd_colaboradores'),
            data.get('qtd_unidades'),
            localizacao,
            data.get('rede_ensino'),
            data.get('clima_organizacional'),
            data.get('adre_clie'),
            data.get('zipn_clie'),
            data.get('bairro_clie'),
            cidade,
            estado,
            data.get('dados_etnograficos'),
            data.get('dados_mercado'),
            mod_mercado,
            mod_etno,
            mod_clima,
            id_clie,
        ))

        cursor.execute("""
                       UPDATE ctdi_matu
                       SET status_ia = 'CONTEXTO OK'
                       WHERE id_clie = %s
                       """, (id_clie,))

        conn.commit()
        return jsonify({"success": True, "message": "Contexto institucional salvo com sucesso."}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


MODERATOR_CONTEXTO_CAMPOS = {
    'dados_mercado': {
        'db_col': 'moderacao_dados_mercado',
        'label': 'contexto de mercado',
        'system': (
            'Você é um consultor educacional sênior. Avalie o resumo de MERCADO fornecido para uma escola. '
            'Em no máximo 3 frases, elogie um ponto forte do texto e faça uma provocação empática sobre '
            'concorrência, posicionamento, sazonalidade de matrículas ou mobilidade das famílias que provavelmente '
            'faltou mencionar. Seja direto, acolhedor e prático. Responda apenas com o texto da sugestão.'
        ),
        'fallback_hint': (
            'inclua concorrentes diretos, ticket médio percebido, raio de captação e sazonalidade de matrículas'
        ),
    },
    'dados_etnograficos': {
        'db_col': 'moderacao_dados_etnograficos',
        'label': 'perfil da comunidade escolar',
        'system': (
            'Você é um consultor educacional sênior. Avalie o perfil ETNOGRÁFICO da comunidade escolar descrito. '
            'Em no máximo 3 frases, elogie um ponto forte e sugira dados sobre famílias, cultura local, renda, '
            'trajetória escolar dos alunos ou diversidade do território que enriqueceriam o diagnóstico. '
            'Seja empático e prático. Responda apenas com o texto da sugestão.'
        ),
        'fallback_hint': (
            'descreva perfil socioeconômico das famílias, origem cultural, distância casa-escola e expectativas educacionais'
        ),
    },
    'clima_organizacional': {
        'db_col': 'moderacao_clima_organizacional',
        'label': 'clima organizacional e expectativas',
        'system': (
            'Você é um consultor educacional sênior. Avalie o relato de CLIMA ORGANIZACIONAL e expectativas sobre IA. '
            'Em no máximo 3 frases, elogie um ponto forte e provoque sobre resistências, liderança, capacitação da '
            'equipe, ritmo de mudança ou medos não verbalizados que impactam a transformação digital. '
            'Seja acolhedor e prático. Responda apenas com o texto da sugestão.'
        ),
        'fallback_hint': (
            'mencione nível de prontidão da equipe, histórico de mudanças, patrocínio da direção e medos sobre IA'
        ),
    },
}


def _chamar_bedrock_moderador(system_prompt, user_content):
    """Invoca Bedrock com timeout rígido; levanta exceção se falhar ou estourar tempo."""
    import concurrent.futures

    def _invoke():
        bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=BEDROCK_REGION,
            config=BEDROCK_BOTO_CONFIG,
        )
        body_request = json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 400,
            'temperature': 0.55,
            'system': system_prompt,
            'messages': [{'role': 'user', 'content': user_content}],
        })
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=body_request,
        )
        raw = json.loads(response.get('body').read())['content'][0]['text']
        return str(raw or '').strip()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_invoke)
        return future.result(timeout=MODERADOR_BEDROCK_TIMEOUT_S)


def _moderador_contexto_fallback(campo, cidade, bairro, texto):
    """Sugestão local quando Bedrock estiver indisponível."""
    meta = MODERATOR_CONTEXTO_CAMPOS.get(campo, {})
    label = meta.get('label', 'este campo')
    hint = meta.get('fallback_hint', 'adicione mais detalhes concretos')
    local = ', '.join(p for p in [bairro, cidade] if p) or 'sua região'
    trecho = (texto or '').strip()[:100]
    elogio = (
        f"Você já avançou bem ao descrever o {label} em {local}"
        + (f' — especialmente ao citar "{trecho}…".' if trecho else '.')
    )
    return f"{elogio} Para enriquecer o diagnóstico, {hint}."


def _persistir_moderacao_contexto(conn, id_clie, campo, suggestion):
    meta = MODERATOR_CONTEXTO_CAMPOS.get(campo)
    if not meta or not id_clie:
        return
    _ensure_contexto_columns(conn)
    col = meta['db_col']
    cur = conn.cursor()
    try:
        cur.execute(
            f"UPDATE ctdi_clie SET {col} = %s WHERE id_clie = %s",
            (suggestion, id_clie),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f'⚠️ Falha ao persistir moderação ({campo}): {e}', file=sys.stderr)
    finally:
        cur.close()


@app.route('/api/ai/moderator/contexto', methods=['POST'])
def ai_moderator_contexto():
    """Agente moderador: complementa cada campo longo do contexto institucional."""
    data = request.json or {}
    campo = (data.get('campo') or 'dados_mercado').strip()
    if campo not in MODERATOR_CONTEXTO_CAMPOS:
        return jsonify({'error': 'Campo de moderação inválido.'}), 400

    cidade = (data.get('cidade') or data.get('cidade_clie') or '').strip()
    bairro = (data.get('bairro') or data.get('bairro_clie') or '').strip()
    tipo_ensino = (data.get('tipo_ensino') or '').strip()
    texto = (data.get('texto') or data.get(campo) or '').strip()
    id_clie = data.get('id_clie')

    if len(texto) < 15:
        label = MODERATOR_CONTEXTO_CAMPOS[campo]['label']
        return jsonify({
            'error': f'Descreva um pouco mais o {label} antes de pedir a análise da IA (mínimo 15 caracteres).',
        }), 400

    local_label = ', '.join(p for p in [bairro, cidade] if p) or 'local não informado'
    meta = MODERATOR_CONTEXTO_CAMPOS[campo]
    user_content = (
        f"Escola localizada em: {local_label}\n"
        f"Tipo de ensino: {tipo_ensino or 'não informado'}\n\n"
        f"Texto do gestor sobre {meta['label']}:\n{texto}"
    )

    suggestion = None
    try:
        suggestion = _chamar_bedrock_moderador(meta['system'], user_content)
    except Exception as aws_err:
        print(f'⚠️ Moderador contexto ({campo}) usando fallback local: {aws_err}', file=sys.stderr)
        suggestion = _moderador_contexto_fallback(campo, cidade, bairro, texto)

    if not suggestion:
        suggestion = _moderador_contexto_fallback(campo, cidade, bairro, texto)

    if len(suggestion) > 900:
        suggestion = suggestion[:897].rstrip() + '...'

    if id_clie:
        conn = None
        try:
            conn = get_db_conn()
            _persistir_moderacao_contexto(conn, id_clie, campo, suggestion)
        except Exception as db_err:
            print(f'⚠️ Moderador contexto ({campo}) sem persistência DB: {db_err}', file=sys.stderr)
        finally:
            if conn:
                conn.close()

    return jsonify({
        'suggestion': suggestion,
        'campo': campo,
        'persisted': bool(id_clie),
    }), 200


@app.route('/api/admin/clientes-search', methods=['GET'])
def admin_search_clientes():
    conn = None
    try:
        conn = get_db_conn()
        _ensure_contexto_columns(conn)
        cursor = conn.cursor()
        term = request.args.get('term', '')
        search_term = f"%{term}%"
        _ensure_holding_columns(conn)

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
                    CASE WHEN p.status = 'ATIVO' THEN true ELSE false END as has_active,
                    c.id_rede,
                    COALESCE(c.is_holding, false) as is_holding,
                    COALESCE(lic.usado_licencas, 0) AS usado_licencas,
                    COALESCE(plano.max_usuarios, 5) AS max_usuarios
                FROM ctdi_clie c
                LEFT JOIN ctdi_projetos p ON c.id_clie = p.id_clie AND p.status = 'ATIVO'
                LEFT JOIN LATERAL (
                    SELECT COUNT(*)::int AS usado_licencas
                    FROM public.paneldx_usuarios u
                    WHERE u.id_clie = c.id_clie
                      AND u.ativo = TRUE
                      AND u.system_role NOT IN ('consultor', 'sysadmin')
                ) lic ON TRUE
                LEFT JOIN LATERAL (
                    SELECT dp.max_usuarios
                    FROM public.dx_contratos dc
                    JOIN public.dx_planos dp ON dp.id = dc.id_plano
                    WHERE dc.id_clie = c.id_clie
                    ORDER BY
                        CASE dc.status
                            WHEN 'ativo' THEN 0
                            WHEN 'trial' THEN 1
                            WHEN 'inadimplente' THEN 2
                            WHEN 'cancelado' THEN 3
                            ELSE 4
                        END,
                        dc.data_inicio DESC,
                        dc.id DESC
                    LIMIT 1
                ) plano ON TRUE
                WHERE c.nome_clie ILIKE %s
                   OR c.empresa_clie ILIKE %s
                   OR c.docu_clie ILIKE %s
                   OR COALESCE(c.id_rede, '') ILIKE %s
                ORDER BY c.id_clie DESC
                """

        cursor.execute(query, (search_term, search_term, search_term, search_term))
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
                "hasActiveProject": row[15],
                "id_rede": row[16] or "",
                "is_holding": bool(row[17]),
                "usado_licencas": int(row[18] or 0),
                "max_usuarios": int(row[19] or 5),
            })

        cursor.close()
        return jsonify(clientes), 200
    except Exception as e:
        print(f"ERRO NO SEARCH: {str(e)}") # Isso ajuda você a ver o erro real no terminal do Python
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/admin/clientes/<int:id_clie>/rede', methods=['PUT'])
def admin_atualizar_rede_cliente(id_clie):
    """Vincula cliente a uma rede (id_rede) e define se é gestor holding (is_holding)."""
    conn = None
    try:
        data = request.json or {}
        id_rede_raw = data.get('id_rede')
        id_rede = (str(id_rede_raw).strip().upper() if id_rede_raw else '') or None
        is_holding = bool(data.get('is_holding', False))

        conn = get_db_conn()
        _ensure_holding_columns(conn)
        cursor = conn.cursor()

        cursor.execute("SELECT id_clie FROM public.ctdi_clie WHERE id_clie = %s", (id_clie,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({"success": False, "error": "Cliente não encontrado."}), 404

        cursor.execute(
            """
            UPDATE public.ctdi_clie
            SET id_rede = %s,
                is_holding = %s
            WHERE id_clie = %s
            """,
            (id_rede, is_holding, id_clie),
        )
        conn.commit()
        cursor.close()

        return jsonify({
            "success": True,
            "message": "Atualizado com sucesso",
            "id_clie": id_clie,
            "id_rede": id_rede,
            "is_holding": is_holding,
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"ERRO AO ATUALIZAR REDE DO CLIENTE {id_clie}: {e}", file=sys.stderr)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# =============================================================================
# MICRO-CMS — Landing Page + Instruções (conteúdo público editável)
# =============================================================================
_cms_table_ensured = False

LEACTION_BLOG_URL = "https://leaction.com.br/blog"
LEACTION_BLOG_BASE = "https://leaction.com.br"
BLOG_CACHE_TTL_SEC = int(os.environ.get("LEACTION_BLOG_CACHE_TTL", "1800"))
_blog_ssl_verify = os.environ.get("CMS_BLOG_SSL_VERIFY", "true").lower() not in (
    "0", "false", "no", "off",
)
_blog_cache = {"posts": None, "fetched_at": 0.0}


def _cms_log_stderr(message):
    """Evita OSError no Windows ao escrever emoji/UTF-8 em stderr."""
    try:
        print(message, file=sys.stderr, flush=True)
    except OSError:
        try:
            sys.stderr.write(f"{message}\n")
            sys.stderr.flush()
        except OSError:
            pass


def _parse_leaction_blog_posts(html, limit=2):
    """Extrai os posts mais recentes do HTML do blog LeAction (ordem da listagem)."""
    posts = []
    pattern = re.compile(
        r'data-blog-post-alias="([^"]+)"'
        r'.*?background-image:\s*url\(\'([^\']+)\'\)'
        r'.*?postTitle.*?<h3>\s*<a[^>]+>(.*?)</a>'
        r'.*?postDescription">(.*?)</div>',
        re.DOTALL | re.IGNORECASE,
    )
    seen = set()
    for match in pattern.finditer(html):
        alias = match.group(1).strip()
        if alias in seen:
            continue
        seen.add(alias)
        image_url = match.group(2).strip()
        title = unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", match.group(3)))).strip()
        description = unescape(re.sub(r"\s+", " ", match.group(4))).strip()
        if len(description) > 340:
            description = description[:337].rsplit(" ", 1)[0] + "..."
        posts.append({
            "image_url": image_url,
            "title": title,
            "description": description,
            "link_url": f"{LEACTION_BLOG_BASE}/{alias}",
            "link_text": "Leia mais →",
            "source": "blog",
        })
        if len(posts) >= limit:
            break
    return posts


def _fetch_leaction_blog_posts(limit=2):
    now = time.time()
    cached = _blog_cache.get("posts") or []
    if cached and (now - float(_blog_cache.get("fetched_at") or 0)) < BLOG_CACHE_TTL_SEC:
        return cached[:limit]

    try:
        response = requests.get(
            LEACTION_BLOG_URL,
            timeout=15,
            headers={"User-Agent": "PanelDX-CMS/1.0 (+https://leaction.com.br)"},
            verify=_blog_ssl_verify,
        )
        response.raise_for_status()
        posts = _parse_leaction_blog_posts(response.text, limit=limit)
        if posts:
            _blog_cache["posts"] = posts
            _blog_cache["fetched_at"] = now
            return posts
    except Exception as exc:
        _cms_log_stderr(f"[CMS] Falha ao sincronizar blog LeAction: {exc}")

    if cached:
        return cached[:limit]
    return []


def _blog_post_to_column(post):
    return {
        "image_url": post.get("image_url") or "",
        "title": post.get("title") or "",
        "description": post.get("description") or "",
        "link_url": post.get("link_url") or "",
        "link_text": post.get("link_text") or "Leia mais →",
        "source": "blog",
    }


def _apply_blog_posts_to_landing(landing):
    posts = _fetch_leaction_blog_posts(2)
    if not posts:
        return landing

    columns = list(landing.get("columns") or [])
    while len(columns) < 4:
        columns.append({
            "image_url": "",
            "title": "",
            "description": "",
            "link_url": "",
            "link_text": "Leia mais →",
            "source": "blog",
        })

    for idx, post in zip((2, 3), posts):
        columns[idx] = _blog_post_to_column(post)

    landing["columns"] = columns
    landing["blog_sync"] = {
        "source_url": LEACTION_BLOG_URL,
        "synced_at": datetime.utcnow().isoformat() + "Z",
        "posts_count": len(posts),
    }
    return landing


def _strip_blog_columns_from_landing(landing):
    """Remove slots dinâmicos do blog antes de persistir no CMS."""
    if not isinstance(landing, dict):
        return landing
    cleaned = dict(landing)
    cleaned.pop("blog_sync", None)
    cols = cleaned.get("columns")
    if isinstance(cols, list):
        cleaned["columns"] = cols[:2]
    return cleaned


def _default_app_version():
    return {
        "version_label": "v1.3.0",
        "title": "Versão atual do PanelDX",
        "summary": (
            "Micro-CMS na landing, Cockpit da Rede integrado ao layout, "
            "grid expandido e melhorias de UX administrativa."
        ),
        "link_text": "Ver histórico de modificações",
        "image_url": "/images/cms-version-default.png",
        "details_html": (
            "<h2>PanelDX — Notas da versão</h2>"
            "<p><strong>Versão atual:</strong> v1.3.0</p>"
            "<h3>Principais entregas</h3>"
            "<ul>"
            "<li>Micro-CMS interno para gestão da landing page e instruções de uso</li>"
            "<li>Grid expandido na home com segunda linha de destaques</li>"
            "<li>Cockpit da Rede enquadrado no layout padrão da aplicação</li>"
            "<li>Área dedicada à versão da aplicação e histórico de modificações</li>"
            "</ul>"
            "<h3>Correções e ajustes</h3>"
            "<ul>"
            "<li>Contraste e enquadramento visual no painel CMS</li>"
            "<li>Exibição de imagens das colunas com ajuste proporcional (sem corte)</li>"
            "<li>Reorganização de links na sidebar do Sysadmin</li>"
            "</ul>"
            "<p><em>Atualize este conteúdo em Administrador → Gestão de Conteúdo (CMS).</em></p>"
        ),
    }


def _default_coluna1():
    """Banner premium — Coluna 1 (Mesa de Inovação), espelho do hero_cta."""
    return {
        "visibility": True,
        "pill_text": "✨ Mesa de Inovação",
        "title": "Leve sua escola ao próximo nível",
        "subtitle": "Transforme o plano gratuito em um Roadmap executável",
        "cta_text": "Agendar Mesa Gratuita",
        "cta_url": "",
        "image_path": "/images/logo3.jpg",
        "bg_color_start": "#0b0c10",
        "bg_color_end": "#1a0b2e",
        "border_color": "rgba(0, 191, 255, 0.2)",
        "title_color": "#ffffff",
        "subtitle_color": "rgba(255, 255, 255, 0.82)",
        "pill_bg_color": "#FF6B00",
        "pill_text_color": "#ffffff",
        "accent_color": "#FF6B00",
        "button_bg_color": "#FF6B00",
        "button_text_color": "#ffffff",
        "button_shadow_color": "#b34700",
    }


def _coerce_cms_color(value, default):
    """Aceita #hex ou rgba/rgb; retorna default se inválido."""
    s = str(value or "").strip()
    if re.match(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", s):
        return s
    if re.match(r"^rgba?\([^)]+\)$", s, re.I):
        return s
    return default


def _default_cms_landing():
    return {
        "hero": {
            "leaction_title": "LeAction System",
            "paneldx_title": "PanelDX",
            "subtitle": "Transformação Digital Educacional DX",
            "description": "Inteligência, metodologia e execução para escolas e redes de ensino.",
        },
        "columns": [
            {
                "image_url": "/images/logo3.jpg",
                "title": "Leve sua escola ao próximo nível",
                "description": "Transforme o plano gratuito em um Roadmap executável",
                "visible": True,
                "layout": "premium_banner",
            },
            {
                "video_url": "",
                "image_url": "",
                "title": "Metodologia CTDI",
                "description": "Framework integrado para diagnóstico, planejamento e execução da transformação digital educacional.",
                "visible": True,
            },
            {
                "image_url": "",
                "title": "",
                "description": "",
                "link_url": "",
                "link_text": "Leia mais →",
                "source": "blog",
            },
            {
                "image_url": "",
                "title": "",
                "description": "",
                "link_url": "",
                "link_text": "Leia mais →",
                "source": "blog",
            },
        ],
        "app_version": _default_app_version(),
        "hero_cta": {
            "visible": True,
            "badge_text": "Novo Agent IA",
            "title": "Descubra como resolver seu maior desafio de gestão em segundos.",
            "subtitle": "Consultor IA 100% Gratuito — cruzamos seu desafio com o framework LeAction em segundos.",
            "button_text": "Falar com Consultor IA",
            "button_url": "/consultor-leaction",
            "image_url": "",
        },
        "coluna1": _default_coluna1(),
        "cta_consultor": {
            "title": "Descubra como resolver seu maior desafio de gestão em segundos.",
            "button_text": "Falar com Consultor IA (Gratuito)",
            "visible": True,
        },
        "insights_section": {
            "title": "Insights e Casos de Uso",
            "subtitle": "Conteúdo estratégico para gestores e tomadores de decisão na educação digital.",
        },
        "insights": [
            {
                "title": "Diagnóstico As-Is gratuito",
                "summary": "Avalie a maturidade tecnológica da sua instituição com o framework LeAction e receba um roadmap inicial.",
                "link_url": "/cadastro",
                "link_text": "Iniciar diagnóstico →",
            },
            {
                "title": "Framework LeAction F na prática",
                "summary": "Conheça como as 105 competências do framework orientam a transformação digital centrada no aluno.",
                "link_url": "https://leactionf.com.br/index.html",
                "link_text": "Explorar o framework →",
            },
            {
                "title": "Agilidade na gestão educacional",
                "summary": "Metodologia CTDI: ciclos iterativos para alinhar diretoria, pedagogia e tecnologia na rede de ensino.",
                "link_url": "https://leaction.com.br/blog",
                "link_text": "Ler no blog LeAction →",
            },
        ],
    }


def _default_cms_instructions():
    return (
        "<h2>Guia Rápido: Diagnóstico de Maturidade Digital</h2>"
        "<p>A <strong>Transformação Digital</strong> é um imperativo no setor educacional. "
        "A <strong>Avaliação de Maturidade LeAction</strong> oferece um diagnóstico preciso "
        "da situação atual de sua organização.</p>"
        "<h3>1. Oportunidade e Estratégia</h3>"
        "<p>Use o framework LeActionF como espinha dorsal do processo.</p>"
        "<h3>2. Sobre a Avaliação</h3>"
        "<ul><li><strong>90 questões</strong> estratégicas (escala 1 a 5)</li>"
        "<li>Respostas completas são essenciais para a precisão do diagnóstico</li></ul>"
        "<h3>3. Fluxo de Acesso</h3>"
        "<ol><li>Cadastre-se em <strong>Iniciar Diagnóstico</strong></li>"
        "<li>Aceite o Termo de Privacidade</li><li>Obtenha o código por e-mail</li>"
        "<li>Faça login e preencha o questionário</li><li>Exporte o relatório em PDF</li></ol>"
        "<p><strong>Suporte:</strong> "
        "<a href=\"mailto:conhecer@leaction.com.br\">conhecer@leaction.com.br</a></p>"
    )


def _ensure_cms_table(conn):
    global _cms_table_ensured
    if _cms_table_ensured:
        return
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.ctdi_cms_config (
                id_cms              SERIAL PRIMARY KEY,
                config_key          VARCHAR(50) NOT NULL DEFAULT 'default',
                landing_page_data   JSONB NOT NULL DEFAULT '{}'::jsonb,
                instructions_data   TEXT,
                updated_at          TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_ctdi_cms_config_key UNIQUE (config_key)
            );
            """
        )
        conn.commit()
        _cms_table_ensured = True
    except Exception as e:
        conn.rollback()
        _cms_log_stderr(f"[CMS] Falha ao garantir tabela CMS: {e}")
    finally:
        cur.close()


def _seed_cms_default_if_needed(conn):
    import psycopg2.extras as pg_extras

    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id_cms FROM public.ctdi_cms_config WHERE config_key = 'default' LIMIT 1"
        )
        if cur.fetchone():
            return
        cur.execute(
            """
            INSERT INTO public.ctdi_cms_config (config_key, landing_page_data, instructions_data)
            VALUES (%s, %s, %s)
            ON CONFLICT (config_key) DO NOTHING
            """,
            ("default", pg_extras.Json(_default_cms_landing()), _default_cms_instructions()),
        )
        conn.commit()
    finally:
        cur.close()


def _default_cms_insights():
    return list(_default_cms_landing().get("insights") or [])


def _normalize_cms_insights(insights, defaults=None):
    """Garante exatamente 3 slots de insights na landing."""
    if defaults is None:
        defaults = _default_cms_insights()
    result = []
    for i in range(3):
        base = defaults[i] if i < len(defaults) and isinstance(defaults[i], dict) else {}
        stored = insights[i] if isinstance(insights, list) and i < len(insights) and isinstance(insights[i], dict) else {}
        merged = {**base, **stored}
        result.append(
            {
                "title": str(merged.get("title") or "").strip(),
                "summary": str(merged.get("summary") or "").strip(),
                "link_url": str(merged.get("link_url") or "").strip(),
                "link_text": str(merged.get("link_text") or "Leia mais →").strip(),
            }
        )
    return result


def _coerce_cms_visible(value, default=True):
    """Interpreta flag de visibilidade do CMS (bool, string ou ausente)."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in ("false", "0", "nao", "não", "no", "oculto", "hidden", "off"):
        return False
    if normalized in ("true", "1", "sim", "yes", "visivel", "visível", "on"):
        return True
    return default


def _normalize_coluna1(landing):
    """Normaliza coluna1 (Mesa de Inovação) — compatível com columns[0] legado."""
    defaults = _default_coluna1()
    if not isinstance(landing, dict):
        return dict(defaults)

    raw = landing.get("coluna1") if isinstance(landing.get("coluna1"), dict) else {}
    legacy = {}
    stored_cols = landing.get("columns")
    if isinstance(stored_cols, list) and stored_cols and isinstance(stored_cols[0], dict):
        legacy = stored_cols[0]

    merged = {**defaults, **legacy, **raw}

    if legacy.get("title") and not raw.get("title"):
        merged["title"] = legacy["title"]
    if legacy.get("description") and not raw.get("subtitle"):
        merged["subtitle"] = legacy["description"]
    if legacy.get("image_url") and not raw.get("image_path"):
        merged["image_path"] = legacy["image_url"]
    if legacy.get("pill_text") and not raw.get("pill_text"):
        merged["pill_text"] = legacy["pill_text"]
    if legacy.get("cta_text") and not raw.get("cta_text"):
        merged["cta_text"] = legacy.get("cta_text") or legacy.get("button_text") or legacy.get("link_text")
    if legacy.get("cta_url") and not raw.get("cta_url"):
        merged["cta_url"] = legacy.get("cta_url") or legacy.get("button_url") or legacy.get("link_url")

    vis_src = raw.get("visibility")
    if vis_src is None and raw.get("visible") is not None:
        vis_src = raw.get("visible")
    if vis_src is None and legacy.get("visible") is not None:
        vis_src = legacy.get("visible")
    if vis_src is None and legacy.get("visibility") is not None:
        vis_src = legacy.get("visibility")
    merged["visibility"] = _coerce_cms_visible(vis_src, default=True)

    merged["pill_text"] = str(
        merged.get("pill_text") or merged.get("badge_text") or defaults["pill_text"]
    ).strip() or defaults["pill_text"]
    merged["title"] = str(merged.get("title") or defaults["title"]).strip() or defaults["title"]
    merged["subtitle"] = str(merged.get("subtitle") or merged.get("description") or defaults["subtitle"]).strip()
    merged["cta_text"] = str(
        merged.get("cta_text") or merged.get("button_text") or merged.get("link_text") or defaults["cta_text"]
    ).strip() or defaults["cta_text"]
    merged["cta_url"] = str(
        merged.get("cta_url") or merged.get("button_url") or merged.get("link_url") or ""
    ).strip()
    merged["image_path"] = str(
        merged.get("image_path") or merged.get("image_url") or defaults["image_path"]
    ).strip()

    for key in (
        "bg_color_start", "bg_color_end", "border_color", "title_color", "subtitle_color",
        "pill_bg_color", "pill_text_color", "accent_color",
        "button_bg_color", "button_text_color", "button_shadow_color",
    ):
        merged[key] = _coerce_cms_color(merged.get(key), defaults[key])

    return merged


def _coluna1_to_column_slot(coluna1):
    """Projeta coluna1 normalizada no slot columns[0] (retrocompatível com a home legada)."""
    return {
        "visible": coluna1.get("visibility", True),
        "visibility": coluna1.get("visibility", True),
        "image_url": coluna1.get("image_path", ""),
        "image_path": coluna1.get("image_path", ""),
        "title": coluna1.get("title", ""),
        "description": coluna1.get("subtitle", ""),
        "subtitle": coluna1.get("subtitle", ""),
        "pill_text": coluna1.get("pill_text", ""),
        "badge_text": coluna1.get("pill_text", ""),
        "cta_text": coluna1.get("cta_text", ""),
        "cta_url": coluna1.get("cta_url", ""),
        "button_text": coluna1.get("cta_text", ""),
        "button_url": coluna1.get("cta_url", ""),
        "layout": "premium_banner",
        "bg_color_start": coluna1.get("bg_color_start"),
        "bg_color_end": coluna1.get("bg_color_end"),
        "border_color": coluna1.get("border_color"),
        "title_color": coluna1.get("title_color"),
        "subtitle_color": coluna1.get("subtitle_color"),
        "pill_bg_color": coluna1.get("pill_bg_color"),
        "pill_text_color": coluna1.get("pill_text_color"),
        "accent_color": coluna1.get("accent_color"),
        "button_bg_color": coluna1.get("button_bg_color"),
        "button_text_color": coluna1.get("button_text_color"),
        "button_shadow_color": coluna1.get("button_shadow_color"),
    }


def _default_hero_cta():
    return {
        "visible": True,
        "badge_text": "Novo Agent IA",
        "title": "Descubra como resolver seu maior desafio de gestão em segundos.",
        "subtitle": (
            "Consultor IA 100% Gratuito — cruzamos seu desafio com o framework LeAction em segundos."
        ),
        "button_text": "Falar com Consultor IA",
        "button_url": "/consultor-leaction",
        "image_url": "",
    }


def _normalize_hero_cta(landing):
    """Banner Hero CTA 3D — compatível com chave legada cta_consultor."""
    defaults = _default_hero_cta()
    legacy = landing.get("cta_consultor") if isinstance(landing.get("cta_consultor"), dict) else {}
    raw = landing.get("hero_cta") if isinstance(landing.get("hero_cta"), dict) else {}
    merged = {**defaults, **legacy, **raw}
    if legacy.get("title") and not raw.get("title"):
        merged["title"] = legacy["title"]
    if legacy.get("button_text") and not raw.get("button_text"):
        merged["button_text"] = legacy["button_text"]
    merged["visible"] = _coerce_cms_visible(
        raw.get("visible") if raw else legacy.get("visible") if legacy else merged.get("visible"),
        default=True,
    )
    merged["button_url"] = str(merged.get("button_url") or "/consultor-leaction").strip() or "/consultor-leaction"
    return merged


def _normalize_cms_landing(landing):
    """Garante estrutura completa do JSON de landing (4 colunas + bloco de versão + insights)."""
    defaults = _default_cms_landing()
    if not isinstance(landing, dict):
        return defaults
    hero = {**defaults.get("hero", {}), **(landing.get("hero") or {})}
    hero_cta = _normalize_hero_cta(landing)
    coluna1 = _normalize_coluna1(landing)
    cta = {
        "title": hero_cta.get("title"),
        "button_text": hero_cta.get("button_text"),
        "visible": hero_cta.get("visible"),
    }
    app_version = {**defaults.get("app_version", {}), **(landing.get("app_version") or {})}
    insights_section = {
        **defaults.get("insights_section", {}),
        **(landing.get("insights_section") or {}),
    }
    insights = _normalize_cms_insights(
        landing.get("insights"),
        defaults.get("insights"),
    )
    stored_cols = landing.get("columns") if isinstance(landing.get("columns"), list) else []
    default_cols = defaults.get("columns") or []
    columns = []
    for i, default_col in enumerate(default_cols):
        if i in (2, 3):
            columns.append(dict(default_col))
            continue
        if i == 0:
            slot = _coluna1_to_column_slot(coluna1)
            columns.append(slot)
            continue
        stored = stored_cols[i] if i < len(stored_cols) and isinstance(stored_cols[i], dict) else {}
        merged = {**default_col, **stored}
        for key, default_val in default_col.items():
            if key == "visible":
                continue
            if not str(merged.get(key) or "").strip():
                merged[key] = default_val
        merged["visible"] = _coerce_cms_visible(
            stored.get("visible") if stored else merged.get("visible"),
            default=default_col.get("visible", True),
        )
        columns.append(merged)
    landing = {
        "hero": hero,
        "columns": columns,
        "coluna1": coluna1,
        "app_version": app_version,
        "hero_cta": hero_cta,
        "cta_consultor": cta,
        "insights_section": insights_section,
        "insights": insights,
    }
    return _apply_blog_posts_to_landing(landing)


def _serialize_cms_row(row):
    if not row:
        return {
            "landing_page_data": _normalize_cms_landing(_default_cms_landing()),
            "instructions_data": _default_cms_instructions(),
            "updated_at": None,
        }
    landing = row.get("landing_page_data") or {}
    if isinstance(landing, str):
        try:
            landing = json.loads(landing)
        except json.JSONDecodeError:
            landing = _default_cms_landing()
    if not landing:
        landing = _default_cms_landing()
    landing = _normalize_cms_landing(landing)
    updated = row.get("updated_at")
    return {
        "landing_page_data": landing,
        "instructions_data": row.get("instructions_data") or _default_cms_instructions(),
        "updated_at": updated.isoformat() if hasattr(updated, "isoformat") else updated,
    }


def _fetch_cms_row(conn):
    _ensure_cms_table(conn)
    _seed_cms_default_if_needed(conn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT landing_page_data, instructions_data, updated_at
        FROM public.ctdi_cms_config
        WHERE config_key = 'default'
        LIMIT 1
        """
    )
    row = cur.fetchone()
    cur.close()
    return row


@app.route("/api/public/cms", methods=["GET"])
def get_public_cms():
    conn = None
    try:
        conn = get_db_conn()
        row = _fetch_cms_row(conn)
        return jsonify({"success": True, **_serialize_cms_row(row)}), 200
    except Exception as e:
        _cms_log_stderr(f"[CMS] Erro CMS publico: {e}")
        return jsonify({"success": True, **_serialize_cms_row(None)}), 200
    finally:
        if conn:
            conn.close()


@app.route("/api/admin/cms", methods=["GET", "PUT"])
def admin_cms():
    import psycopg2.extras as pg_extras

    conn = None
    try:
        conn = get_db_conn()
        if request.method == "GET":
            row = _fetch_cms_row(conn)
            return jsonify({"success": True, **_serialize_cms_row(row)}), 200

        data = request.json or {}
        landing = data.get("landing_page_data")
        instructions = data.get("instructions_data")
        if landing is None and instructions is None:
            return jsonify({"success": False, "error": "Nenhum dado para atualizar."}), 400

        _ensure_cms_table(conn)
        _seed_cms_default_if_needed(conn)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if landing is not None and instructions is not None:
            cur.execute(
                """
                UPDATE public.ctdi_cms_config
                SET landing_page_data = %s,
                    instructions_data = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE config_key = 'default'
                RETURNING landing_page_data, instructions_data, updated_at
                """,
                (pg_extras.Json(_strip_blog_columns_from_landing(landing)), instructions),
            )
        elif landing is not None:
            cur.execute(
                """
                UPDATE public.ctdi_cms_config
                SET landing_page_data = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE config_key = 'default'
                RETURNING landing_page_data, instructions_data, updated_at
                """,
                (pg_extras.Json(_strip_blog_columns_from_landing(landing)),),
            )
        else:
            cur.execute(
                """
                UPDATE public.ctdi_cms_config
                SET instructions_data = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE config_key = 'default'
                RETURNING landing_page_data, instructions_data, updated_at
                """,
                (instructions,),
            )

        row = cur.fetchone()
        conn.commit()
        cur.close()
        return jsonify({
            "success": True,
            "message": "Conteúdo atualizado com sucesso.",
            **_serialize_cms_row(row),
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        _cms_log_stderr(f"[CMS] Erro CMS admin: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
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


def _gerar_codigo_acesso_la():
    """Código LA-XXXXXX padronizado para ctdi_lead_access."""
    return f"LA-{generate_random_code(6)}"


def _codigos_acesso_coincidem(stored, provided):
    """Aceita LA-ABC123 ou ABC123 de forma equivalente."""
    s = (stored or '').strip().upper()
    p = (provided or '').strip().upper()
    if not s or not p:
        return False
    if s == p:
        return True
    s_core = s[3:] if s.startswith('LA-') else s
    p_core = p[3:] if p.startswith('LA-') else p
    return s_core == p_core


def _b64url_decode(value):
    """Decodifica segmento JWT base64url."""
    padding = '=' * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode('ascii'))


def _verify_leaction_hub_jwt(token):
    """
    Valida JWT HS256 emitido pelo Action Hub (gateway-api/server.js).
    Payload esperado:
      iss, status_tecnico, order_id, customer_email, gateway_ref, id_matu
    """
    secret = os.environ.get('HUB_JWT_SECRET') or os.environ.get('JWT_SECRET') or 'super-secret-hub-key-2026'
    parts = (token or '').split('.')
    if len(parts) != 3:
        raise ValueError('token JWT malformado')

    header_b64, payload_b64, signature_b64 = parts
    signing_input = f'{header_b64}.{payload_b64}'.encode('ascii')
    expected_sig = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(signature_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError('assinatura JWT inválida')

    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError('token JWT ilegível') from exc

    if header.get('alg') not in (None, 'HS256'):
        raise ValueError('algoritmo JWT não suportado')

    exp = payload.get('exp')
    if exp is not None:
        try:
            if int(exp) < int(time.time()):
                raise ValueError('token JWT expirado')
        except (TypeError, ValueError) as exc:
            raise ValueError('claim exp inválida no JWT') from exc

    return payload


# Mesmo status usado pelo admin em POST /api/admin/toggle-project (is_active=true)
HUB_MATU_ACTIVE_STATUS = 'PROJETO OK'
HUB_PROJETO_ACTIVE_STATUS = 'ATIVO'
_STATUS_IA_PRESERVE_ON_ACTIVATE = frozenset({
    'AVALIACAO OK',
    'PENDENTE',
    'PROCESSANDO',
    'CONCLUIDO',
    'ERRO_IA',
})


def _resolve_status_ia_on_activate(current_status):
    """Não regride assessment/gênese já avançados ao ativar o projeto."""
    normalized = (current_status or '').strip().upper()
    if normalized in _STATUS_IA_PRESERVE_ON_ACTIVATE:
        return normalized
    return HUB_MATU_ACTIVE_STATUS


class HubFulfillmentError(ValueError):
    """Erro de negócio no fulfillment do webhook Action Hub."""


def _parse_hub_id_matu(value):
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return None
    return parsed if parsed > 0 else None


def _fulfill_leaction_hub_payment(order_id, customer_email, gateway_ref, id_matu):
    """
    Ativa o diagnóstico existente via id_matu (sem criar lead).
    Espelha a lógica do admin toggle: status_ia PROJETO OK + projeto ATIVO.
    Idempotente: reprocessar o mesmo pedido retorna 200 sem efeitos colaterais.
    """
    id_matu_int = _parse_hub_id_matu(id_matu)
    if not id_matu_int:
        raise HubFulfillmentError('id_matu inválido')

    conn = get_db_conn()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT m.id_matu, m.id_clie, m.status_ia, c.mail_clie, c.has_active_project
            FROM public.ctdi_matu m
            JOIN public.ctdi_clie c ON c.id_clie = m.id_clie
            WHERE m.id_matu = %s
            LIMIT 1
            """,
            (id_matu_int,),
        )
        row = cursor.fetchone()
        if not row:
            raise HubFulfillmentError(f'id_matu {id_matu_int} não encontrado')

        id_matu_db, id_clie, status_ia, mail_clie, has_active_project = row
        email_db = (mail_clie or '').strip().lower()
        email_hub = (customer_email or '').strip().lower()
        if email_hub and email_db and email_hub != email_db:
            raise HubFulfillmentError('customer_email não corresponde ao id_matu informado')

        cursor.execute(
            "SELECT status FROM public.ctdi_projetos WHERE id_clie = %s LIMIT 1",
            (id_clie,),
        )
        projeto_row = cursor.fetchone()
        projeto_status = projeto_row[0] if projeto_row else None

        already_active = (
            projeto_status == HUB_PROJETO_ACTIVE_STATUS
            and bool(has_active_project)
            and (status_ia or '').strip().upper() == _resolve_status_ia_on_activate(status_ia)
        )
        if already_active:
            print(
                f'ℹ️ [HUB WEBHOOK] id_matu={id_matu_int} já ativo '
                f'(order_id={order_id}, gateway_ref={gateway_ref})',
                file=sys.stderr,
            )
            return {
                'status': 'already_active',
                'id_matu': id_matu_int,
                'id_clie': id_clie,
                'status_ia': status_ia,
                'order_id': order_id,
                'gateway_ref': gateway_ref,
            }

        next_status = _resolve_status_ia_on_activate(status_ia)

        cursor.execute(
            """
            UPDATE public.ctdi_clie
            SET has_active_project = %s
            WHERE id_clie = %s
            """,
            (True, id_clie),
        )
        cursor.execute(
            """
            UPDATE public.ctdi_matu
            SET status_ia = %s
            WHERE id_matu = %s
            """,
            (next_status, id_matu_int),
        )
        cursor.execute(
            """
            INSERT INTO public.ctdi_projetos (id_clie, status)
            VALUES (%s, %s)
            ON CONFLICT (id_clie)
            DO UPDATE SET status = EXCLUDED.status
            """,
            (id_clie, HUB_PROJETO_ACTIVE_STATUS),
        )
        conn.commit()

        print(
            f'✅ [HUB WEBHOOK] Diagnóstico ativado id_matu={id_matu_int} id_clie={id_clie} '
            f'order_id={order_id} gateway_ref={gateway_ref}',
            file=sys.stderr,
        )
        return {
            'status': 'activated',
            'id_matu': id_matu_int,
            'id_clie': id_clie,
            'status_ia': next_status,
            'projeto_status': HUB_PROJETO_ACTIVE_STATUS,
            'order_id': order_id,
            'gateway_ref': gateway_ref,
        }
    except HubFulfillmentError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


@app.route('/api/hub/payment-webhook', methods=['POST'])
def hub_payment_webhook():
    """
    Webhook do Action Hub após pagamento confirmado.
    Corpo JSON (gateway-api/server.js → axios.post(webhook_url, { token })):
      { "token": "<JWT HS256>" }
    Claims no JWT:
      iss=leaction-hub, status_tecnico=PAYMENT_CONFIRMED,
      order_id, customer_email, gateway_ref, id_matu
    """
    data = request.get_json(silent=True) or {}
    token = data.get('token')
    if not token or not str(token).strip():
        return jsonify({'error': 'Campo obrigatório ausente: token'}), 400

    try:
        payload = _verify_leaction_hub_jwt(str(token).strip())
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 401

    if payload.get('iss') != 'leaction-hub':
        return jsonify({'error': 'JWT com emissor inválido'}), 401

    if payload.get('status_tecnico') != 'PAYMENT_CONFIRMED':
        return jsonify({
            'error': 'Status de pagamento não confirmado',
            'status_tecnico': payload.get('status_tecnico'),
        }), 400

    product_type = (payload.get('product_type') or '').strip()
    hub_payload = payload.get('hub_payload') if isinstance(payload.get('hub_payload'), dict) else {}
    order_id = payload.get('order_id')
    customer_email = (payload.get('customer_email') or '').strip().lower()
    gateway_ref = (payload.get('gateway_ref') or '').strip()
    id_matu = payload.get('id_matu')

    if not order_id or not customer_email:
        return jsonify({'error': 'JWT incompleto: order_id e customer_email são obrigatórios'}), 400

    if product_type == 'PANELDX_SUBSCRIPTION':
        try:
            id_clie = int(hub_payload.get('id_clie'))
            id_plano = int(hub_payload.get('id_plano'))
        except (TypeError, ValueError):
            return jsonify({'error': 'hub_payload inválido: id_clie e id_plano obrigatórios.'}), 400

        id_matu_opt = _parse_hub_id_matu(hub_payload.get('id_matu') or id_matu)
        valor = hub_payload.get('valor_negociado')
        try:
            valor_f = float(valor) if valor is not None else None
        except (TypeError, ValueError):
            valor_f = None

        conn = get_db_conn()
        cur = conn.cursor()
        try:
            from services.hub_fulfillment import fulfill_hub_subscription, HubFulfillmentError as SubFulfillErr

            result = fulfill_hub_subscription(
                cur,
                id_clie=id_clie,
                id_plano=id_plano,
                id_matu=id_matu_opt,
                order_id=order_id,
                gateway_ref=gateway_ref,
                valor_negociado=valor_f,
            )
            conn.commit()
            return jsonify({
                'success': True,
                'payment': {
                    'order_id': order_id,
                    'gateway_ref': gateway_ref,
                    'customer_email': customer_email,
                    'product_type': product_type,
                },
                **result,
            }), 200
        except SubFulfillErr as exc:
            conn.rollback()
            return jsonify({'error': str(exc)}), 400
        except Exception as exc:
            conn.rollback()
            print(f'❌ [HUB WEBHOOK] Erro subscription: {exc}', file=sys.stderr)
            traceback.print_exc()
            return jsonify({'error': 'Erro interno ao ativar contrato'}), 500
        finally:
            cur.close()
            conn.close()

    if id_matu is None or str(id_matu).strip() == '':
        return jsonify({'error': 'JWT incompleto: id_matu é obrigatório'}), 400

    try:
        result = _fulfill_leaction_hub_payment(order_id, customer_email, gateway_ref, id_matu)
        return jsonify({
            'success': True,
            'payment': {
                'order_id': order_id,
                'gateway_ref': gateway_ref,
                'customer_email': customer_email,
                'id_matu': result.get('id_matu'),
                'status_tecnico': payload.get('status_tecnico'),
            },
            **result,
        }), 200
    except HubFulfillmentError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        print(f'❌ [HUB WEBHOOK] Erro ao liberar acesso: {exc}', file=sys.stderr)
        traceback.print_exc()
        return jsonify({'error': 'Erro interno ao processar confirmação de pagamento'}), 500


@app.route('/api/webhooks/ativar-addon', methods=['POST'])
def webhook_ativar_addon():
    """
    Webhook do Action Hub após pagamento de pacote add-on de licenças.
    JWT: product_type=PANELDX_ADDON, hub_payload={id_clie, id_plano_addon, quantidade}
    """
    data = request.get_json(silent=True) or {}
    token = data.get('token')
    if not token or not str(token).strip():
        return jsonify({'error': 'Campo obrigatório ausente: token'}), 400

    try:
        payload = _verify_leaction_hub_jwt(str(token).strip())
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 401

    if payload.get('iss') != 'leaction-hub':
        return jsonify({'error': 'JWT com emissor inválido'}), 401

    if payload.get('status_tecnico') != 'PAYMENT_CONFIRMED':
        return jsonify({
            'error': 'Status de pagamento não confirmado',
            'status_tecnico': payload.get('status_tecnico'),
        }), 400

    product_type = (payload.get('product_type') or '').strip()
    if product_type and product_type != 'PANELDX_ADDON':
        return jsonify({'error': 'Tipo de produto inválido para este webhook.'}), 400

    hub_payload = payload.get('hub_payload') or {}
    if not isinstance(hub_payload, dict):
        hub_payload = {}

    try:
        id_clie = int(hub_payload.get('id_clie'))
        id_plano_addon = int(hub_payload.get('id_plano_addon') or hub_payload.get('id_plano'))
        quantidade = int(hub_payload.get('quantidade') or 1)
    except (TypeError, ValueError):
        return jsonify({'error': 'hub_payload inválido: id_clie e id_plano_addon obrigatórios.'}), 400

    order_id = payload.get('order_id')
    gateway_ref = (payload.get('gateway_ref') or '').strip()

    from services.addon_engine import ativar_addon_contrato

    conn = get_db_conn()
    cur = conn.cursor()
    try:
        result = ativar_addon_contrato(
            cur,
            id_clie=id_clie,
            id_plano_addon=id_plano_addon,
            quantidade=max(1, quantidade),
            hub_order_id=str(order_id) if order_id else gateway_ref or None,
        )
        conn.commit()
        return jsonify({'success': True, 'addon': result, 'order_id': order_id}), 200
    except ValueError as exc:
        conn.rollback()
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        conn.rollback()
        print(f'❌ [ADDON WEBHOOK] Erro: {exc}', file=sys.stderr)
        traceback.print_exc()
        return jsonify({'error': 'Erro interno ao ativar add-on'}), 500
    finally:
        cur.close()


def _ensure_matu_for_client(cursor, conn, id_clie, init_role='GENERAL'):
    """Garante slot em ctdi_matu (clientes legados criados sem maturidade)."""
    cursor.execute(
        "SELECT id_matu FROM public.ctdi_matu WHERE id_clie = %s ORDER BY id_matu DESC LIMIT 1",
        (id_clie,),
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    papel = (init_role or 'GENERAL').upper().strip()
    status = 'SANDBOX' if papel == 'SOLO' else 'AGUARDANDO CONTEXTO'
    cursor.execute(
        """
        INSERT INTO public.ctdi_matu (id_clie, status_ia)
        VALUES (%s, %s)
        RETURNING id_matu
        """,
        (id_clie, status),
    )
    new_id = cursor.fetchone()[0]
    conn.commit()
    print(f"-> Slot ctdi_matu criado para id_clie={id_clie} (id_matu={new_id})", file=sys.stderr)
    return new_id


# --- NOVA ROTA: CHECAGEM DE E-MAIL (O Porteiro) ---
@app.route('/api/check-email', methods=['POST'])
def check_email_type():
    data = request.json
    email = data.get('email', '').lower().strip()

    conn = get_db_conn()
    cursor = conn.cursor()

    try:
        # 1. Verifica LEADS/CLIENTES com código de acesso (prioridade se também for admin)
        cursor.execute("""
            SELECT c.id_clie
            FROM ctdi_clie c
            JOIN ctdi_lead_access a ON c.id_clie = a.id_clie
            WHERE LOWER(c.mail_clie) = LOWER(%s)
            LIMIT 1
        """, (email,))
        lead_com_codigo = cursor.fetchone()

        from rbac.users import rbac_paneldx_usuarios_disponivel

        # 2. Verifica paneldx_usuarios (conta global sem squad)
        if rbac_paneldx_usuarios_disponivel(cursor):
            cursor.execute(
                """
                SELECT id_usuario FROM public.paneldx_usuarios
                WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s)) AND ativo = true
                LIMIT 1
                """,
                (email,),
            )
            if cursor.fetchone():
                return jsonify({"type": "TEAM", "message": "Digite sua senha de acesso."})

        # 3. Verifica EQUIPE (ctdi_team)
        cursor.execute(
            "SELECT id_team FROM ctdi_team WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s)) AND ativo = true",
            (email,),
        )
        is_team = cursor.fetchone()

        if lead_com_codigo:
            msg = "Digite o código de acesso enviado no momento do cadastro."
            if is_team:
                msg = "Este e-mail também é de administração. Use o código LA-* recebido no cadastro."
            return jsonify({"type": "LEAD", "message": msg})

        if is_team:
            return jsonify({"type": "TEAM", "message": "Digite sua senha de acesso."})

        # 3. Cliente sem código (legado) — tenta criar slot de acesso
        cursor.execute(
            "SELECT id_clie, init_role FROM ctdi_clie WHERE LOWER(TRIM(mail_clie)) = LOWER(TRIM(%s))",
            (email,),
        )
        leads = cursor.fetchall()

        if leads:
            codigo_final = None

            try:
                for lead in leads:
                    id_clie = lead[0]
                    init_role = lead[1]

                    cursor.execute(
                        "SELECT access_code FROM public.ctdi_lead_access WHERE id_clie = %s LIMIT 1",
                        (id_clie,),
                    )
                    access_existente = cursor.fetchone()
                    if access_existente and access_existente[0]:
                        return jsonify({
                            "type": "LEAD",
                            "message": "Digite o código de acesso enviado no momento do cadastro.",
                        })

                    _ensure_matu_for_client(cursor, conn, id_clie, init_role)
                    codigo_final = _gerar_codigo_acesso_la()

                    cursor.execute("""
                                   INSERT INTO ctdi_lead_access (id_clie, access_code, created_at)
                                   VALUES (%s, %s, NOW())
                                   ON CONFLICT (id_clie) DO NOTHING
                                   """, (id_clie, codigo_final))

                conn.commit()
            except Exception as e_db:
                conn.rollback()
                print(f"Erro DB: {e_db}", file=sys.stderr)
                return jsonify({"error": "Erro ao processar credenciais."}), 500

            if codigo_final:
                dispatch_access_code_email(email, codigo_final)
                return jsonify({
                    "type": "LEAD",
                    "message": "Código de acesso enviado para o seu e-mail.",
                })

        return jsonify({"error": "E-mail não encontrado."}), 404

    except Exception as e:
        print(f"Erro check-email: {e}", file=sys.stderr)
        return jsonify({"error": "Erro interno"}), 500
    finally:
        cursor.close()


# =========================================================================
# 🧲 ISCA DIGITAL PÚBLICA: CONSULTOR LEACTION (Lead Magnet com IA)
# Rota pública e isolada — não exige login. Analisa o framework e devolve
# um mini-plano empático para servir de CTA ao cadastro no PanelDX.
# =========================================================================
@lru_cache(maxsize=1)
def _obter_contexto_framework():
    """Monta a string de contexto do framework (Dimensão > Domínio > Bloco).

    O framework muda raramente, então o resultado é memorizado com lru_cache:
    a primeira chamada vai ao banco; as seguintes servem direto da memória.
    Se precisar forçar atualização, chame _obter_contexto_framework.cache_clear().
    Retorna (framework_texto, blocos_amostra) — a amostra alimenta o fallback.
    """
    conn = None
    try:
        # Conexão própria: não usar get_db_conn() — o finally fecha a conexão e
        # envenenaria g.db_conn para o restante da mesma requisição.
        conn = db_manager._connect_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            """
            SELECT b.id_bloc, b.name_bloc, b.desc_bloc,
                   d.name_dime, dom.name_doma
            FROM public.leaf_bloc b
                     JOIN public.leaf_dime d ON b.id_dime = d.id_dime
                     JOIN public.leaf_doma dom ON b.id_doma = dom.id_doma
            ORDER BY d.name_dime, dom.name_doma, b.name_bloc;
            """
        )
        blocos = cursor.fetchall()
        cursor.close()

        if not blocos:
            return None, []

        linhas_framework = []
        for b in blocos:
            desc = (b['desc_bloc'] or '').strip().replace('\n', ' ')
            if len(desc) > 180:
                desc = desc[:180] + '...'
            linhas_framework.append(
                f"- Bloco: \"{b['name_bloc']}\" (Dimensão: {b['name_dime']} | Domínio: {b['name_doma']}). Foco: {desc}"
            )

        amostra = [
            {"name_bloc": b['name_bloc'], "name_dime": b['name_dime'], "name_doma": b['name_doma']}
            for b in blocos[:3]
        ]
        return "\n".join(linhas_framework), amostra
    finally:
        if conn:
            conn.close()


def _instrucao_formato_mini_plano():
    """Instrução embutida no system prompt do Consultor IA para o campo mini_plano."""
    return (
        'O campo "mini_plano" deve ser UMA string com exatamente 3 a 5 ações numeradas (uma por linha), '
        'sem markdown, sem bullets, sem JSON aninhado, sem parágrafo introdutório e sem conclusão solta. '
        'Formato OBRIGATÓRIO de cada linha:\n'
        'N) NOME_DO_DOMINIO_EM_MAIUSCULAS: Descrição objetiva da ação em 1–2 frases.\n'
        'Exemplo válido:\n'
        '1) GESTÃO DE PESSOAS: Definir indicadores trimestrais e ritual de acompanhamento com a equipe.\n'
        '2) TECNOLOGIA EDUCACIONAL: Mapear ferramentas digitais em uso e eliminar redundâncias.\n'
        '3) EXECUÇÃO: Estabelecer sprint piloto de 2 semanas com entregáveis mensuráveis.\n'
        'Use nomes de DOMÍNIO reais do framework (em MAIÚSCULAS) antes dos dois pontos — '
        'não escreva apenas "DOMÍNIO:" como rótulo genérico.'
    )


def _normalizar_mini_plano_consultor(mini_plano):
    """Padroniza mini_plano para o parser Kanban do frontend (N) DOMÍNIO: ação."""
    texto = str(mini_plano or '').strip()
    if not texto:
        return texto

    texto = texto.replace('\r\n', '\n')
    segmentos = re.split(r'(?=\d+[\)\.]\s+)', texto)
    linhas_saida = []

    for segmento in segmentos:
        segmento = segmento.strip()
        if not segmento:
            continue
        m = re.match(r'^(\d+)[\)\.]\s*(.+)$', segmento, re.DOTALL)
        if not m:
            continue
        num, corpo = m.group(1), re.sub(r'\s+', ' ', m.group(2).strip())
        if ':' in corpo:
            dom, acao = corpo.split(':', 1)
            dom = re.sub(r'^dom[ií]nio\s*', '', dom.strip(), flags=re.I).upper()
            acao = acao.strip()
            linhas_saida.append(f'{num}) {dom}: {acao}')
        else:
            linhas_saida.append(f'{num}) AÇÃO RECOMENDADA: {corpo}')

    if linhas_saida:
        return '\n'.join(linhas_saida)
    return texto


def _mini_plano_fallback_consultor(amostra_blocos):
    """Mini-plano local no formato numerado quando Bedrock estiver indisponível."""
    blocos = amostra_blocos or [
        {'name_bloc': 'Diagnóstico Inicial', 'name_dime': 'Estratégia', 'name_doma': 'Gestão'}
    ]
    dom1 = str(blocos[0].get('name_doma') or 'Gestão').upper()
    dom2 = str(blocos[0].get('name_dime') or 'Estratégia').upper()
    nomes_blocos = ', '.join(
        b.get('name_bloc', '') for b in blocos[:3] if b.get('name_bloc')
    ) or 'recomendados'
    return (
        f'1) {dom1}: Mapear o cenário atual do desafio relatado e registrar os principais gargalos.\n'
        f'2) {dom2}: Priorizar ações práticas dos blocos {nomes_blocos}, com foco em impacto rápido.\n'
        '3) EXECUÇÃO: Agendar diagnóstico completo no PanelDX para converter o roteiro em tarefas no Kanban.'
    )


@app.route('/api/public/consultor-ia', methods=['POST'])
def consultor_leaction_publico():
    data = request.json or {}
    desafio = (data.get('desafio') or '').strip()

    if len(desafio) < 10:
        return jsonify({
            "status": "error",
            "message": "Descreva o desafio com um pouco mais de detalhe (mínimo 10 caracteres)."
        }), 400

    try:
        # PASSO A: Contexto do framework (servido do cache após a 1ª chamada)
        framework_texto, blocos_amostra = _obter_contexto_framework()

        if not framework_texto:
            return jsonify({"status": "error", "message": "Framework indisponível no momento."}), 503

        # PASSO B: Chamada ao agente (Bedrock / Claude 3.5 Sonnet)
        system_prompt = (
            "Você é o Consultor LeAction, um especialista empático em transformação digital. "
            "O usuário vai desabafar um problema. Sua missão: "
            "1) Demonstrar empatia breve. "
            "2) Analisar a lista de blocos metodológicos fornecida e escolher exatamente de 1 a 3 blocos que resolvem o problema. "
            "3) Montar um mini-plano de ação prático baseado nesses blocos. "
            "Retorne estritamente em formato JSON (sem markdown, sem comentários) com as chaves: "
            "\"mensagem_empatia\", \"dimensao_identificada\", \"dominio_identificado\", "
            "\"blocos_recomendados\" (array com nomes exatos dos blocos escolhidos), e \"mini_plano\" (string). "
            + _instrucao_formato_mini_plano()
        )

        user_content = (
            f"DESAFIO RELATADO PELO GESTOR:\n{desafio}\n\n"
            f"BLOCOS DISPONÍVEIS NO FRAMEWORK LEACTION:\n{framework_texto}"
        )

        resposta_ia = None
        try:
            bedrock = boto3.client(service_name='bedrock-runtime', region_name=BEDROCK_REGION)
            body_request = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "temperature": 0.6,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_content}]
            })
            response = bedrock.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                contentType='application/json', accept='application/json',
                body=body_request
            )
            resposta_ia = _extrair_json_da_resposta(
                json.loads(response.get('body').read())['content'][0]['text']
            )
        except Exception as aws_err:
            print(f"⚠️ Consultor IA usando fallback local: {aws_err}", file=sys.stderr)
            amostra = blocos_amostra or [{"name_bloc": "Diagnóstico Inicial", "name_dime": "Estratégia", "name_doma": "Gestão"}]
            resposta_ia = {
                "mensagem_empatia": (
                    "Entendemos perfeitamente o seu desafio — esse é um cenário comum e "
                    "totalmente superável com a abordagem certa."
                ),
                "dimensao_identificada": amostra[0]['name_dime'],
                "dominio_identificado": amostra[0]['name_doma'],
                "blocos_recomendados": [b['name_bloc'] for b in amostra],
                "mini_plano": _mini_plano_fallback_consultor(amostra),
            }

        if isinstance(resposta_ia, dict):
            resposta_ia["mini_plano"] = _normalizar_mini_plano_consultor(
                resposta_ia.get("mini_plano")
            )

        # PASSO C: Retorno para o frontend
        return jsonify({"status": "success", "data": resposta_ia}), 200

    except Exception as e:
        print(f"❌ ERRO CONSULTOR IA: {e}", file=sys.stderr)
        return jsonify({"status": "error", "message": "Erro ao processar a análise."}), 500


def _garantir_kr_inovacao(cursor, id_clie):
    """Garante um KR-âncora para o cliente (ctdi_okr_atividades.id_kr é NOT NULL).

    Reaproveita a trilha 'Inovação Sob Demanda' se já existir; caso contrário cria a
    cadeia mínima Direcionador -> Objetivo -> KR. Retorna o id_kr.
    """
    cursor.execute(
        """
        SELECT k.id_kr
        FROM public.ctdi_okr_direcionadores d
                 JOIN public.ctdi_okr_objetivos_dt o ON o.id_direc = d.id_direc
                 JOIN public.ctdi_okr_krs k ON k.id_obj_dt = o.id_obj_dt
        WHERE d.id_clie = %s AND d.nome_direc = 'Inovação Sob Demanda'
        ORDER BY k.id_kr ASC LIMIT 1;
        """,
        (id_clie,)
    )
    existente = cursor.fetchone()
    if existente:
        return existente['id_kr']

    cursor.execute(
        """
        INSERT INTO public.ctdi_okr_direcionadores (id_clie, nome_direc, desc_direc)
        VALUES (%s, 'Inovação Sob Demanda', 'Trilha expressa gerada pelo Consultor LeAction interno.')
        RETURNING id_direc;
        """,
        (id_clie,)
    )
    id_direc = cursor.fetchone()['id_direc']

    cursor.execute(
        """
        INSERT INTO public.ctdi_okr_objetivos_dt (id_direc, nome_obj, desc_obj)
        VALUES (%s, 'Resolver dores imediatas de gestão', 'Objetivo âncora para sprints avulsas de fast track.')
        RETURNING id_obj_dt;
        """,
        (id_direc,)
    )
    id_obj_dt = cursor.fetchone()['id_obj_dt']

    cursor.execute(
        """
        INSERT INTO public.ctdi_okr_krs (id_obj_dt, nome_kr, kpi_nome, valor_inicial, valor_alvo, valor_atual)
        VALUES (%s, 'Execução de Sprints Sob Demanda', 'Sprints concluídas', 0, 100, 0)
        RETURNING id_kr;
        """,
        (id_obj_dt,)
    )
    return cursor.fetchone()['id_kr']


# =========================================================================
# ⚡ CONSULTOR INTERNO (FAST TRACK): AGENTE GERADOR DE SPRINT AVULSA
# Usuário logado que ainda não preencheu o questionário full pode descrever
# uma dor e receber uma Sprint completa, acoplada, direto no Backlog.
# =========================================================================
@app.route('/api/consultor-interno/gerar-sprint-avulsa', methods=['POST'])
def gerar_sprint_avulsa():
    data = request.json or {}
    problema = (data.get('problema') or '').strip()
    id_clie = data.get('id_clie')
    id_matu = data.get('id_matu')

    if len(problema) < 10:
        return jsonify({"success": False, "error": "Descreva o desafio com mais detalhe (mínimo 10 caracteres)."}), 400
    if not id_clie or not id_matu:
        return jsonify({"success": False, "error": "id_clie e id_matu são obrigatórios."}), 400

    # PASSO A: contexto do framework (cacheado)
    framework_texto, _ = _obter_contexto_framework()
    if not framework_texto:
        return jsonify({"success": False, "error": "Framework indisponível no momento."}), 503

    # PASSO B: chamada ao agente
    system_prompt = (
        "Você é o Consultor LeAction interno. O usuário relatou este problema: "
        f"{problema}. Escolha apenas 1 bloco do framework que resolve isso. "
        "Retorne um JSON estrito (sem markdown): "
        "{ \"nome_sprint\": \"...\", \"objetivo_sprint\": \"...\", "
        "\"nome_bloco_recomendado\": \"...\", \"atividades_taticas\": [\"...\", \"...\"] }."
    )
    user_content = (
        f"PROBLEMA DO GESTOR:\n{problema}\n\n"
        f"BLOCOS DISPONÍVEIS NO FRAMEWORK:\n{framework_texto}"
    )

    ia = None
    try:
        bedrock = boto3.client(service_name='bedrock-runtime', region_name=BEDROCK_REGION)
        body_request = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1200,
            "temperature": 0.6,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}]
        })
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType='application/json', accept='application/json',
            body=body_request
        )
        ia = _extrair_json_da_resposta(json.loads(response.get('body').read())['content'][0]['text'])
    except Exception as aws_err:
        print(f"⚠️ Sprint avulsa usando fallback local: {aws_err}", file=sys.stderr)
        ia = {
            "nome_sprint": "Sprint Tática de Solução Rápida",
            "objetivo_sprint": f"Endereçar de forma estruturada o desafio: {problema[:120]}",
            "nome_bloco_recomendado": "",
            "atividades_taticas": [
                "Mapear a situação atual e os gargalos relacionados ao desafio.",
                "Definir uma ação piloto de impacto rápido.",
                "Estabelecer métrica de acompanhamento do resultado."
            ]
        }

    nome_sprint = (ia.get('nome_sprint') or 'Sprint Tática Sob Demanda').strip()[:250]
    objetivo = (ia.get('objetivo_sprint') or 'Objetivo gerado pelo Consultor LeAction.').strip()
    nome_bloco = (ia.get('nome_bloco_recomendado') or '').strip()
    atividades = ia.get('atividades_taticas') or []
    if not isinstance(atividades, list):
        atividades = []

    # PASSO C: transação estrutural (Bloco -> Iteração -> Squad -> Sprint -> Atividades)
    conn = None
    cursor = None
    try:
        conn = get_db_conn()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 1. Bloco recomendado (ILIKE); fallback para o primeiro bloco do framework
        id_bloc = None
        id_dime = None
        if nome_bloco:
            cursor.execute(
                "SELECT id_bloc, id_dime FROM public.leaf_bloc WHERE name_bloc ILIKE %s LIMIT 1;",
                (f"%{nome_bloco}%",)
            )
            row = cursor.fetchone()
            if row:
                id_bloc, id_dime = row['id_bloc'], row['id_dime']
        if id_bloc is None:
            cursor.execute("SELECT id_bloc, id_dime FROM public.leaf_bloc ORDER BY id_bloc ASC LIMIT 1;")
            row = cursor.fetchone()
            if not row:
                raise Exception("Framework sem blocos cadastrados.")
            id_bloc, id_dime = row['id_bloc'], row['id_dime']

        # 2. Garantia de Iteração — ctdi_itera liga-se a ctdi_main via id_ctdi (não há id_matu aqui)
        cursor.execute(
            """
            SELECT i.id_itera
            FROM public.ctdi_main m
                     JOIN public.ctdi_itera i ON m.id_ctdi = i.id_ctdi
            WHERE m.id_matu = %s
            ORDER BY i.id_itera ASC LIMIT 1;
            """,
            (id_matu,)
        )
        row_it = cursor.fetchone()
        if row_it:
            id_itera = row_it['id_itera']
        else:
            cursor.execute("SELECT id_ctdi FROM public.ctdi_main WHERE id_matu = %s LIMIT 1;", (id_matu,))
            row_main = cursor.fetchone()
            if row_main:
                id_ctdi = row_main['id_ctdi']
            else:
                cursor.execute(
                    """
                    INSERT INTO public.ctdi_main (id_dime, name_ctdi, id_matu)
                    VALUES (%s, 'Inovação Sob Demanda', %s)
                    RETURNING id_ctdi;
                    """,
                    (id_dime, id_matu)
                )
                id_ctdi = cursor.fetchone()['id_ctdi']

            cursor.execute(
                """
                INSERT INTO public.ctdi_itera (id_ctdi, name_itera, stat_itera)
                VALUES (%s, 'Inovação Sob Demanda', 'ativa')
                RETURNING id_itera;
                """,
                (id_ctdi,)
            )
            id_itera = cursor.fetchone()['id_itera']

        # 3. KR-âncora (ctdi_okr_atividades.id_kr é NOT NULL)
        id_kr = _garantir_kr_inovacao(cursor, id_clie)

        # 4. Squad vazia (Regra 4) — membros só via LED / Gestão de Time
        from sprint_squad import (
            atualizar_nome_squad_pos_sprint,
            criar_squad_vazia_para_sprint,
            resolver_ou_criar_projeto_cliente,
        )

        id_proj = resolver_ou_criar_projeto_cliente(cursor, int(id_clie))
        id_squad = criar_squad_vazia_para_sprint(
            cursor, id_proj=id_proj, nome_sprint=nome_sprint
        )

        # 5. Sprint em análise — atividades ficam no backlog até planejamento manual
        backlog_dx = [
            {"titulo": texto[:250], "descricao": "", "subtasks": []}
            for texto in (str(atv).strip() for atv in atividades)
            if texto
        ]
        metrics_payload = {
            "backlog_dx": backlog_dx,
            "schema_versao": "1.0.0",
            "id_clie": id_clie,
            "origem": "Consultor LeAction - PanelDX",
            "tipo_mesa": "consultor_adhoc",
            "problema_declarado": problema[:500],
        }
        cursor.execute(
            """
            INSERT INTO public.ctdi_sprn
                (id_bloc, id_itera, id_squad, name_sprn, desc_sprn, stat_sprn, url_kanban, metrics_scores)
            VALUES (%s, %s, %s, %s, %s, 'em_analise', 'IMPORTACAO_JSON_DX', %s)
            RETURNING id_sprn;
            """,
            (
                id_bloc,
                id_itera,
                id_squad,
                nome_sprint,
                objetivo,
                psycopg2.extras.Json(metrics_payload),
            )
        )
        id_sprn = cursor.fetchone()['id_sprn']
        atualizar_nome_squad_pos_sprint(cursor, id_squad, nome_sprint, id_sprn)

        conn.commit()
        return jsonify({
            "success": True,
            "id_sprn": id_sprn,
            "nome_sprint": nome_sprint,
            "atividades_criadas": 0,
            "itens_backlog": len(backlog_dx),
            "stat_sprn": "em_analise",
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ ERRO SPRINT AVULSA: {e}", file=sys.stderr)
        return jsonify({"success": False, "error": "Não foi possível gerar a sprint."}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/api/login', methods=['POST'])
def login_unificado():
    print("\n--- INICIANDO LOGIN INTELIGENTE (Tabela ctdi_projetos) ---")

    try:
        conn = db_manager._connect_db()  # Ou get_db_conn(), use o que estiver configurado
    except Exception as e:
        return jsonify({"error": "Erro de conexão DB"}), 500

    data = request.json or {}
    email = (data.get('email') or '').lower().strip()
    credential = (data.get('credential') or data.get('codigo') or '').strip()

    if not email or not credential:
        return jsonify({"error": "Informe e-mail e código/senha."}), 401

    print(f"Tentativa de login para: {email}")

    cursor = conn.cursor()

    def _falha_lead(result):
        if result == "NO_ACCESS":
            return jsonify({
                "error": "Conta sem código de acesso. Entre em contato com o suporte."
            }), 401
        if result == "BAD_CODE":
            return jsonify({
                "error": "Código incorreto. Verifique o código recebido no momento do cadastro."
            }), 401
        return None

    def _tentar_login_lead():
        """Valida e-mail + código em ctdi_clie / ctdi_lead_access."""
        cursor.execute(
            """
            SELECT c.id_clie,
                   c.nome_clie,
                   c.init_role,
                   c.mail_clie,
                   COALESCE(c.is_holding, false) AS is_holding,
                   c.id_rede,
                   (SELECT fase_atual
                    FROM ctdi_projetos p
                    WHERE p.id_clie = c.id_clie
                      AND p.status = 'ATIVO'
                    LIMIT 1) AS projeto_fase
            FROM public.ctdi_clie c
            WHERE LOWER(TRIM(c.mail_clie)) = LOWER(TRIM(%s))
            LIMIT 1
            """,
            (email,),
        )
        clie = cursor.fetchone()
        if not clie:
            return None

        id_clie, nome_clie, init_role, mail_clie, is_holding, id_rede, fase_proj = clie

        cursor.execute(
            "SELECT access_code FROM public.ctdi_lead_access WHERE id_clie = %s LIMIT 1",
            (id_clie,),
        )
        access_row = cursor.fetchone()
        if not access_row:
            print(f"-> Cliente {id_clie} existe, mas sem ctdi_lead_access.", file=sys.stderr)
            return "NO_ACCESS"

        stored_code = access_row[0]
        if not _codigos_acesso_coincidem(stored_code, credential):
            print(f"-> Código inválido para cliente {id_clie}.", file=sys.stderr)
            return "BAD_CODE"

        print(f"-> LEAD ENCONTRADO: {nome_clie}")
        has_active = bool(fase_proj)
        id_matu = _ensure_matu_for_client(cursor, conn, id_clie, init_role)

        from rbac.users import rbac_ensure_usuario_lead
        id_usuario = rbac_ensure_usuario_lead(
            cursor, id_clie=id_clie, email=mail_clie, nome=nome_clie
        )
        conn.commit()

        papel = (init_role or 'GENERAL').upper().strip()
        holding_flag = bool(is_holding)
        return jsonify({
            "success": True,
            "redirect": "/cockpit-rede" if holding_flag else "/projeto",
            "id_clie": id_clie,
            "id_usuario": id_usuario,
            "nome_clie": nome_clie,
            "email": mail_clie,
            "role": "LEAD",
            "system_role": "led",
            "auth_type": "lead",
            "init_role": papel,
            "perfil_lead": "INOVADOR" if papel == "SOLO" else "GENERAL",
            "hasActiveProject": has_active,
            "faseAtual": fase_proj or 'Diagnóstico Inicial',
            "id_matu": id_matu,
            "is_holding": holding_flag,
            "id_rede": (str(id_rede).strip().upper() if id_rede else None)
        })

    try:
        # ==================================================================
        # 1. SENHA — paneldx_usuarios + ctdi_team (prioridade sobre LA-* de lead)
        #    Evita que senhas como LA-PANEL1 sejam tratadas como código de lead.
        # ==================================================================
        from rbac.constants import ROLE_SYSADMIN
        from rbac.context import RbacContext, redirect_for_role, store_rbac_session
        from rbac.users import (
            rbac_buscar_membership_ativa,
            rbac_buscar_usuario_por_email,
            rbac_sync_usuario_from_team_row,
            rbac_vincular_team_ao_usuario,
        )

        admin_email = (os.environ.get("ADMIN_EMAIL") or "sysadmin@leaction.com.br").strip()

        def _senha_valida(db_hash, credential_value):
            if not db_hash:
                return False
            if db_hash.startswith('scrypt:') or db_hash.startswith('pbkdf2:'):
                from werkzeug.security import check_password_hash
                return check_password_hash(db_hash, credential_value)
            return db_hash == credential_value

        def _resposta_login_team(*, system_role, id_usuario, id_member, id_squad, id_proj,
                                 id_clie_team, nome, role_db, position, auth_type="team"):
            if admin_email and email.lower() == admin_email.lower():
                system_role = ROLE_SYSADMIN
            ctx = RbacContext(
                system_role=system_role,
                id_usuario=id_usuario,
                id_member=id_member,
                id_clie=id_clie_team,
                id_proj=id_proj,
                id_squad=id_squad,
                email=email,
                position=position,
                auth_type=auth_type,
            )
            store_rbac_session(ctx)
            id_matu_team = None
            if id_clie_team:
                id_matu_team = _ensure_matu_for_client(cursor, conn, id_clie_team, "GENERAL")
            conn.commit()
            return jsonify({
                "success": True,
                "redirect": redirect_for_role(system_role),
                "auth_type": auth_type,
                "system_role": system_role,
                "id_usuario": id_usuario,
                "id_member": id_member,
                "id_squad": id_squad,
                "id_proj": id_proj,
                "id_clie": id_clie_team,
                "nome_clie": nome,
                "email": email,
                "role": role_db,
                "position": position,
                "id_matu": id_matu_team,
                "hasActiveProject": bool(id_clie_team),
            })

        usuario = rbac_buscar_usuario_por_email(cursor, email)
        if usuario and usuario.get("ativo") and _senha_valida(usuario.get("password_hash"), credential):
            print("-> Login via paneldx_usuarios (papel global).")
            membership = rbac_buscar_membership_ativa(cursor, usuario["id_usuario"])
            return _resposta_login_team(
                system_role=usuario["system_role"],
                id_usuario=usuario["id_usuario"],
                id_member=membership["id_member"] if membership else None,
                id_squad=membership["id_squad"] if membership else None,
                id_proj=membership["id_proj"] if membership else None,
                id_clie_team=usuario.get("id_clie") or (membership["id_clie"] if membership else None),
                nome=usuario["nome"],
                role_db=(membership or {}).get("position") or usuario["system_role"].upper(),
                position=(membership or {}).get("position"),
                auth_type="usuario",
            )

        # Fallback legado: ctdi_team (sincroniza paneldx_usuarios na primeira autenticação)
        cursor.execute(
            """
            SELECT t.id_member, t.id_team, t.nome, t.role, t.position,
                   t.password_hash, t.id_squad, sq.id_proj, p.id_clie
            FROM public.ctdi_team t
            LEFT JOIN public.ctdi_squads sq ON sq.id_squad = t.id_squad
            LEFT JOIN public.ctdi_projetos p ON p.id_proj = sq.id_proj
            WHERE LOWER(TRIM(t.email)) = LOWER(TRIM(%s)) AND t.ativo = true
            ORDER BY t.id_member DESC
            LIMIT 1
            """,
            (email,),
        )
        admin_user = cursor.fetchone()

        if admin_user:
            print("-> Email encontrado na tabela de EQUIPE (ctdi_team) — sincronizando usuário global.")
            (
                id_member, _id_team_legacy, nome, role_db, position,
                db_hash, id_squad, id_proj, id_clie_team,
            ) = admin_user

            if _senha_valida(db_hash, credential):
                id_usuario = rbac_sync_usuario_from_team_row(
                    cursor,
                    email=email,
                    nome=nome,
                    role=role_db,
                    position=position,
                    password_hash=db_hash,
                    admin_email=admin_email,
                )
                rbac_vincular_team_ao_usuario(cursor, id_member=id_member, id_usuario=id_usuario)
                usuario_sync = rbac_buscar_usuario_por_email(cursor, email)
                system_role = usuario_sync["system_role"] if usuario_sync else "executor"
                return _resposta_login_team(
                    system_role=system_role,
                    id_usuario=id_usuario,
                    id_member=id_member,
                    id_squad=id_squad,
                    id_proj=id_proj,
                    id_clie_team=id_clie_team,
                    nome=nome,
                    role_db=role_db,
                    position=position,
                )

            print("-> Senha admin inválida; tentando fallback como lead...")
            lead_resp = _tentar_login_lead()
            falha = _falha_lead(lead_resp)
            if falha:
                return falha
            if lead_resp:
                return lead_resp
            return jsonify({"error": "Senha incorreta."}), 401

        # ==================================================================
        # 2. CÓDIGO DE LEAD (LA-* do cadastro)
        # ==================================================================
        if credential.upper().startswith('LA-'):
            print("-> Credencial LA-*: tentando ctdi_lead_access...")
            lead_resp = _tentar_login_lead()
            falha = _falha_lead(lead_resp)
            if falha:
                return falha
            if lead_resp:
                return lead_resp

        # ==================================================================
        # 3. LEAD (fallback)
        # ==================================================================
        lead_resp = _tentar_login_lead()
        falha = _falha_lead(lead_resp)
        if falha:
            return falha
        if lead_resp:
            return lead_resp

        print("-> FALHA: Credenciais inválidas.")
        return jsonify({"error": "E-mail ou código inválidos."}), 401

    except Exception as e:
        print(f"ERRO CRITICO LOGIN: {e}")
        traceback.print_exc()
        return jsonify({"error": "Erro interno no servidor."}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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

        conn = get_db_conn()
        cursor = conn.cursor()

        # A nossa Máquina de Estado — não regredir AVALIACAO OK / CONCLUIDO
        cursor.execute(
            "SELECT status_ia FROM ctdi_matu WHERE id_clie = %s ORDER BY id_matu DESC LIMIT 1",
            (id_clie,),
        )
        matu_row = cursor.fetchone()
        status_atual = matu_row[0] if matu_row else None
        if is_active:
            novo_status = _resolve_status_ia_on_activate(status_atual)
        else:
            # Desativar não apaga gênese; volta ao estágio de avaliação se ainda não concluiu.
            atual = (status_atual or '').strip().upper()
            novo_status = atual if atual in ('CONCLUIDO', 'PENDENTE', 'PROCESSANDO', 'ERRO_IA') else 'AVALIACAO OK'

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

        # 4. SINCRONIZA CONTRATO CRM (dx_contratos) — toggle admin também é contratação operacional
        if is_active:
            cursor.execute(
                """
                SELECT id FROM public.dx_contratos
                WHERE id_clie = %s AND status IN ('ativo', 'trial', 'inadimplente')
                ORDER BY id DESC LIMIT 1
                """,
                (id_clie,),
            )
            contrato = cursor.fetchone()
            if contrato:
                cursor.execute(
                    """
                    UPDATE public.dx_contratos
                    SET status = 'ativo', atualizado_em = NOW()
                    WHERE id = %s
                    """,
                    (contrato[0],),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO public.dx_contratos
                        (id_clie, id_plano, valor_negociado, status, data_inicio, data_vencimento)
                    SELECT %s, p.id, COALESCE(p.valor_mensal, 1), 'ativo', CURRENT_DATE, CURRENT_DATE + 365
                    FROM public.dx_planos p
                    WHERE p.ativo = TRUE
                    ORDER BY p.id
                    LIMIT 1
                    """,
                    (id_clie,),
                )
        else:
            cursor.execute(
                """
                UPDATE public.dx_contratos
                SET status = 'cancelado', atualizado_em = NOW()
                WHERE id_clie = %s AND status IN ('ativo', 'trial', 'inadimplente')
                """,
                (id_clie,),
            )

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

# ENDPOINT PARA ADMIN: Retorna maturidades de clientes empresariais (exclui inovador solo)
def _is_cliente_empresarial_avaliacao(record):
    """Inovadores solo não passam pela avaliação inicial de diagnóstico."""
    if not record:
        return False
    init_role = str(record.get('init_role') or 'GENERAL').upper().strip()
    status_ia = str(record.get('status_ia') or '').upper().strip()
    justificativa = str(record.get('justificativa_solo') or '').strip()
    if init_role == 'SOLO':
        return False
    if status_ia == 'SANDBOX':
        return False
    if justificativa:
        return False
    return True


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
        empresariais = [m for m in all_maturities if _is_cliente_empresarial_avaliacao(m)]
        return jsonify(empresariais), 200

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
                                     WHEN s.stat_sprn IN ('em_andamento', 'ativa') THEN 1 \
                                     WHEN s.stat_sprn IN ('planejada_backlog', 'planejada') THEN 2 \
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
    conn = None
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
            from estrategia_matriz import resolver_hierarquia_objetivo
            from sprint_qualidade import enriquecer_sprint_details

            payload = dict(sprint_data)
            oid = payload.get("objetivo_id")
            if oid:
                hier = resolver_hierarquia_objetivo(conn, int(oid))
                if hier:
                    payload["estrategia_okr"] = hier
            try:
                payload = enriquecer_sprint_details(conn, payload)
            except Exception as enrich_err:
                print(f"⚠️ sprint_qualidade enrich: {enrich_err}")
            return jsonify(payload), 200
        return jsonify({"error": "Sprint não encontrada no repositório."}), 404
    except Exception as e:
        print(f"❌ Erro no Python (sprint_details): {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/sprints/metricas/comprovar', methods=['POST'])
def sprints_metricas_comprovar():
    """Cliente envia comprovação (documento_url e/ou depoimento) de uma métrica."""
    conn = None
    try:
        from rbac.context import resolve_rbac_context
        from sprint_qualidade import comprovar_metrica, e_moderador

        ctx = resolve_rbac_context()
        if e_moderador(ctx):
            return jsonify({
                "error": "O Moderador não submete comprovação — apenas avalia a qualidade das entregas do Cliente."
            }), 403

        data = request.get_json(silent=True) or {}
        id_metrica = data.get('id_metrica') or data.get('id')
        if not id_metrica:
            return jsonify({"error": "id_metrica é obrigatório."}), 400

        conn = get_db_conn()
        result = comprovar_metrica(
            conn,
            id_metrica=int(id_metrica),
            documento_url=data.get('documento_url'),
            depoimento=data.get('depoimento'),
        )
        return jsonify({"success": True, **result}), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except LookupError as le:
        return jsonify({"error": str(le)}), 404
    except Exception as e:
        print(f"❌ Erro comprovar métrica: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/sprints/metricas/submeter-analise', methods=['POST'])
def sprints_metricas_submeter_analise():
    """
    Cliente submete a comprovação de UMA métrica.
    Nota automática (regra interna): só texto 40, só documento 40, ambos 100.
    """
    conn = None
    try:
        from rbac.context import resolve_rbac_context
        from sprint_qualidade import (
            aplicar_nota_em_metrica,
            calcular_nota_por_evidencia,
            comprovar_metrica,
            e_moderador,
        )

        ctx = resolve_rbac_context()
        if e_moderador(ctx):
            return jsonify({
                "error": "Apenas o Cliente submete métricas para análise do Modulador."
            }), 403

        data = request.get_json(silent=True) or {}
        id_metrica = data.get('id_metrica') or data.get('id')
        if not id_metrica:
            return jsonify({"error": "id_metrica é obrigatório."}), 400

        documento_url = (data.get('documento_url') or '').strip()
        depoimento = (data.get('depoimento') or '').strip()
        if not documento_url and not depoimento:
            return jsonify({"error": "Informe documento (link) e/ou depoimento para esta métrica."}), 400

        nota = calcular_nota_por_evidencia(documento_url, depoimento)
        status_mod = 'Aprovado' if nota >= 100 else 'Revisão Necessária'

        conn = get_db_conn()
        comprovar_metrica(
            conn,
            id_metrica=int(id_metrica),
            documento_url=documento_url or None,
            depoimento=depoimento or None,
        )
        result = aplicar_nota_em_metrica(conn, int(id_metrica), nota)
        return jsonify({
            "success": True,
            "status": status_mod,
            "nota": nota,
            **result,
        }), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except LookupError as le:
        return jsonify({"error": str(le)}), 404
    except Exception as e:
        print(f"❌ Erro submeter-analise métrica: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/sprints/metricas/avaliar', methods=['POST'])
def sprints_metricas_avaliar():
    """
    Consultor humano revisa a nota do Modulador — somente sob solicitação do Cliente.
    """
    conn = None
    try:
        from sprint_qualidade import avaliar_metrica, pode_revisar_nota_consultor
        from rbac.context import resolve_rbac_context

        ctx = resolve_rbac_context()
        data = request.get_json(silent=True) or {}
        id_metrica = data.get('id_metrica') or data.get('id')
        if id_metrica is None:
            return jsonify({"error": "id_metrica é obrigatório."}), 400
        if 'nota_qualidade' not in data:
            return jsonify({"error": "nota_qualidade é obrigatória."}), 400

        conn = get_db_conn()

        # Descobre a sprint da métrica para validar a exceção
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id_sprn FROM public.dx_entregas_metricas
            WHERE id = %s OR id_metrica = %s
            LIMIT 1
            """,
            (int(id_metrica), int(id_metrica)),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return jsonify({"error": "Métrica/entrega não encontrada."}), 404
        id_sprn = int(row[0])

        if not pode_revisar_nota_consultor(conn, id_sprn, ctx):
            return jsonify({
                "error": (
                    "Revisão do consultor é excepcional: só é permitida quando o Cliente "
                    "solicitar revisão da nota do Modulador."
                ),
                "codigo": "revisao_nao_solicitada",
            }), 403

        result = avaliar_metrica(
            conn,
            id_metrica=int(id_metrica),
            nota_qualidade=data.get('nota_qualidade'),
            id_moderador=ctx.id_usuario,
        )
        return jsonify({"success": True, **result}), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except LookupError as le:
        return jsonify({"error": str(le)}), 404
    except Exception as e:
        print(f"❌ Erro avaliar métrica: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/sprints/revisao-consultor/solicitar', methods=['POST'])
def sprints_revisao_solicitar():
    """Cliente solicita revisão excepcional da nota do Modulador por consultor humano."""
    conn = None
    try:
        from rbac.context import resolve_rbac_context
        from sprint_qualidade import e_moderador, solicitar_revisao_consultor

        ctx = resolve_rbac_context()
        if e_moderador(ctx):
            return jsonify({
                "error": "Apenas o Cliente solicita revisão do consultor."
            }), 403

        data = request.get_json(silent=True) or {}
        id_sprn = data.get('id_sprn')
        if not id_sprn:
            return jsonify({"error": "id_sprn é obrigatório."}), 400

        conn = get_db_conn()
        result = solicitar_revisao_consultor(conn, int(id_sprn), data.get('motivo'))
        return jsonify({"success": True, **result}), 200
    except LookupError as le:
        return jsonify({"error": str(le)}), 404
    except Exception as e:
        print(f"❌ Erro solicitar revisão: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/sprints/revisao-consultor/finalizar', methods=['POST'])
def sprints_revisao_finalizar():
    """Cliente ou consultor encerra o ciclo de revisão excepcional."""
    conn = None
    try:
        from sprint_qualidade import finalizar_revisao_consultor

        data = request.get_json(silent=True) or {}
        id_sprn = data.get('id_sprn')
        if not id_sprn:
            return jsonify({"error": "id_sprn é obrigatório."}), 400

        conn = get_db_conn()
        result = finalizar_revisao_consultor(conn, int(id_sprn))
        return jsonify({"success": True, **result}), 200
    except LookupError as le:
        return jsonify({"error": str(le)}), 404
    except Exception as e:
        print(f"❌ Erro finalizar revisão: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/sprints/dod/atualizar', methods=['POST'])
def sprints_dod_atualizar():
    """Persiste checkboxes DoD (concluido boolean). Não altera nota de qualidade. Só Cliente."""
    conn = None
    try:
        from sprint_qualidade import atualizar_dod_checklist, dod_100_porcento, e_moderador
        from rbac.context import resolve_rbac_context

        ctx = resolve_rbac_context()
        if e_moderador(ctx):
            return jsonify({"error": "O Moderador não altera DoD — apenas o Cliente marca critérios e solicita o fechamento."}), 403

        data = request.get_json(silent=True) or {}
        id_sprn = data.get('id_sprn')
        itens = data.get('itens') or data.get('dod_itens') or []
        if not id_sprn:
            return jsonify({"error": "id_sprn é obrigatório."}), 400

        conn = get_db_conn()
        dod = atualizar_dod_checklist(conn, int(id_sprn), itens)
        completo, total, ok = dod_100_porcento(conn, int(id_sprn))
        return jsonify({
            "success": True,
            "dod_itens": dod,
            "dod_completo": completo,
            "dod_resumo": {"total": total, "concluidos": ok},
        }), 200
    except Exception as e:
        print(f"❌ Erro atualizar DoD: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/sprints/fechar', methods=['POST'])
def sprints_fechar():
    """
    Cliente solicita encerramento da Sprint.
    Exige: DoD 100% + média das notas do Moderador >= 80.
    """
    conn = None
    try:
        from rbac.context import resolve_rbac_context
        from sprint_qualidade import (
            atualizar_dod_checklist,
            pode_fechar_sprint,
            validar_prontidao_fechamento,
        )
        from sprint_governance import STAT_CONCLUIDA

        ctx = resolve_rbac_context()
        if not pode_fechar_sprint(ctx):
            return jsonify({
                "error": "Apenas o Cliente pode solicitar o encerramento da Sprint. O Moderador apenas pontua a qualidade."
            }), 403

        data = request.get_json(silent=True) or {}
        id_sprn = data.get('id_sprn')
        if not id_sprn:
            return jsonify({"error": "id_sprn é obrigatório."}), 400

        conn = get_db_conn()

        dod_itens = data.get('dod_itens') or data.get('itens')
        if isinstance(dod_itens, list) and dod_itens:
            atualizar_dod_checklist(conn, int(id_sprn), dod_itens)

        prontidao = validar_prontidao_fechamento(conn, int(id_sprn))
        if not prontidao["ok"]:
            status = 400
            # Prioriza feedback de qualidade < 80 quando aplicável (mensagem pedida no fluxo)
            msg = prontidao["mensagem"]
            if not prontidao.get("qualidade_ok") and prontidao.get("dod_completo"):
                from sprint_qualidade import MSG_QUALIDADE_ABAIXO
                msg = MSG_QUALIDADE_ABAIXO
            return jsonify({
                "success": False,
                "error": msg,
                "codigo": prontidao.get("codigo"),
                **{k: v for k, v in prontidao.items() if k not in ("ok", "mensagem")},
            }), status

        progresso = prontidao["progresso_qualidade"]
        update_data = {
            "stat_sprn": STAT_CONCLUIDA,
            "realv_sprn": str(int(progresso)),
        }
        success = db_manager.update_record(conn, 'ctdi_sprn', int(id_sprn), update_data)
        if not success:
            return jsonify({"error": "Falha ao encerrar a Sprint no banco."}), 500

        return jsonify({
            "success": True,
            "message": "Sprint encerrada com sucesso.",
            "progresso_qualidade": progresso,
            "stat_sprn": STAT_CONCLUIDA,
        }), 200
    except Exception as e:
        print(f"❌ Erro fechar sprint: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# =========================================================================
# 🧑‍⚖️ MODULADOR IA (O Juiz) — avaliação síncrona de evidência vs. DoD
# =========================================================================
_modulador_cols_ensured = False


def _ensure_modulador_columns(conn):
    """Garante (idempotente) as colunas do Modulador e tags da vitrine em ctdi_sprn."""
    global _modulador_cols_ensured
    if _modulador_cols_ensured:
        return
    cur = conn.cursor()
    try:
        cur.execute(
            """
            ALTER TABLE public.ctdi_sprn
                ADD COLUMN IF NOT EXISTS evidencia_texto    TEXT,
                ADD COLUMN IF NOT EXISTS modulador_status   VARCHAR(50),
                ADD COLUMN IF NOT EXISTS modulador_feedback TEXT,
                ADD COLUMN IF NOT EXISTS tags               TEXT[] NOT NULL DEFAULT '{}';
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ctdi_sprn_tags_gin
                ON public.ctdi_sprn USING GIN (tags);
            """
        )
        conn.commit()
        _modulador_cols_ensured = True
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Falha ao garantir colunas do Modulador: {e}", file=sys.stderr)
    finally:
        cur.close()


def _strip_html(html_text):
    """Converte o HTML do Quill em texto limpo para o prompt."""
    import re as _re
    if not html_text:
        return ''
    txt = _re.sub(r'(?i)<br\s*/?>', '\n', html_text)
    txt = _re.sub(r'(?i)</(p|div|li|h[1-6]|tr)>', '\n', txt)
    txt = _re.sub(r'(?i)<li[^>]*>', '• ', txt)
    txt = _re.sub(r'<[^>]+>', '', txt)
    replacements = {
        '&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>',
        '&quot;': '"', '&#39;': "'", '&apos;': "'",
    }
    for k, v in replacements.items():
        txt = txt.replace(k, v)
    return _re.sub(r'\n{3,}', '\n\n', txt).strip()


def _formatar_dod(criteria_dod, fallback_desc=None):
    """Formata os Critérios de Aceite (Definition of Done) para o prompt."""
    if not criteria_dod:
        if fallback_desc:
            return f"Sem DoD formal cadastrado. Avalie pelo objetivo declarado: {fallback_desc}"
        return "Nenhum critério de aceite formal cadastrado. Avalie pela descrição/objetivo da sprint."
    try:
        dod = criteria_dod if isinstance(criteria_dod, (dict, list)) else json.loads(criteria_dod)
    except Exception:
        return str(criteria_dod)

    itens = []
    if isinstance(dod, dict):
        for item in (dod.get('required') or []):
            itens.append(f"- (Obrigatório) {item}")
        for item in (dod.get('context_education') or []):
            itens.append(f"- (Contextual) {item}")
    elif isinstance(dod, list):
        itens = [f"- {item}" for item in dod]

    return "\n".join(itens) if itens else "Critérios de aceite não estruturados."


@app.route('/api/modulador/avaliar', methods=['POST'])
def avaliar_modulador():
    """
    O Modulador IA: compara a Evidência do usuário com o Definition of Done da Sprint
    via AWS Bedrock (Claude) e devolve um veredito JSON estruturado.
    """
    data = request.json or {}
    id_sprn = data.get('id_sprn')
    evidencia = (data.get('evidencia') or '').strip()

    if not id_sprn:
        return jsonify({"success": False, "error": "ID da sprint não informado."}), 400
    if len(_strip_html(evidencia)) < 10:
        return jsonify({
            "success": False,
            "error": "Descreva a evidência com mais detalhes antes de submeter ao Modulador."
        }), 400

    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro de conexão (modulador): {e}", file=sys.stderr)
        return jsonify({"success": False, "error": "Erro de conexão com o banco de dados."}), 500

    _ensure_modulador_columns(conn)

    # 1) Contexto da sprint + Definition of Done (criteria_dod do entregável)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT s.id_sprn, s.name_sprn, s.desc_sprn, s.stat_sprn,
               d.name_derv, d.derv_defi, d.derv_metr, d.criteria_dod
        FROM public.ctdi_sprn s
        LEFT JOIN public.leaf_derv d ON s.id_bloc = d.id_bloc
        WHERE s.id_sprn = %s
        """,
        (id_sprn,),
    )
    sprint = cur.fetchone()
    cur.close()
    if not sprint:
        return jsonify({"success": False, "error": "Sprint não encontrada."}), 404

    dod_texto = _formatar_dod(sprint.get('criteria_dod'), sprint.get('desc_sprn'))

    # 2) Prompts — AUDITOR RIGOROSO E CÉTICO (regras inegociáveis)
    system_prompt = (
        "Você é um Auditor de Qualidade extremamente rigoroso e cético. Seu papel é comparar a "
        "Evidência fornecida pelo usuário com o Definition of Done (Critérios de Aceite) da Sprint, "
        "exigindo PROVAS CONCRETAS para cada critério obrigatório. Responda sempre em português do Brasil.\n\n"
        "REGRAS INEGOCIÁVEIS:\n"
        "REGRA 1: Não acredite em declarações vagas do usuário (ex.: 'documento anexado', 'feito', "
        "'aprovado', 'concluído'). Afirmação sem prova material NÃO é evidência.\n"
        "REGRA 2: Se o Definition of Done (DoD) exigir um link, publicação ou portal, a evidência DEVE "
        "conter obrigatoriamente uma URL válida (começando com http:// ou https://). Sem URL = REPROVADO.\n"
        "REGRA 3: Se o DoD exigir aprovação formal, e-mail ou ata, a evidência DEVE conter a "
        "transcrição/cópia desse e-mail/ata no próprio texto. Apenas dizer 'foi aprovado' = REPROVADO.\n"
        "REGRA 4: Se faltar prova concreta para QUALQUER critério obrigatório do DoD, atribua nota "
        "menor que 50 e retorne o status 'Revisão Necessária'.\n\n"
        "A 'nota' (inteiro de 0 a 100) deve refletir o percentual de critérios obrigatórios efetivamente "
        "COMPROVADOS com prova material. Critério sem prova concreta NÃO conta como cumprido."
    )
    user_content = (
        f"TÍTULO DA SPRINT:\n{sprint.get('name_sprn') or 'N/A'}\n\n"
        f"DESCRIÇÃO / OBJETIVO:\n{sprint.get('desc_sprn') or 'N/A'}\n\n"
        f"ENTREGÁVEL DE REFERÊNCIA:\n{sprint.get('name_derv') or 'N/A'} — "
        f"{sprint.get('derv_defi') or 'sem definição adicional'}\n\n"
        f"DEFINITION OF DONE (CRITÉRIOS DE ACEITE):\n{dod_texto}\n\n"
        f"EVIDÊNCIA APRESENTADA PELO USUÁRIO:\n{_strip_html(evidencia)}\n\n"
        "Audite a evidência critério a critério, aplicando as REGRAS INEGOCIÁVEIS. Retorne APENAS um JSON "
        "estrito, sem markdown e sem texto fora do objeto, no formato exato:\n"
        '{"status": "Aprovado" ou "Revisão Necessária", '
        '"nota": número inteiro de 0 a 100, '
        '"feedback": "parecer objetivo e construtivo", '
        '"pontos_fortes": ["..."], "pendencias": ["..."]}'
    )

    # 3) Invocação do Bedrock
    try:
        bedrock = boto3.client(service_name='bedrock-runtime', region_name=BEDROCK_REGION)
        body_request = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "temperature": 0.2,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        })
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType='application/json', accept='application/json',
            body=body_request,
        )
        raw = json.loads(response.get('body').read())['content'][0]['text']
        veredito = _extrair_json_da_resposta(raw)
    except Exception as e:
        print(f"❌ Modulador IA indisponível: {e}", file=sys.stderr)
        return jsonify({
            "success": False,
            "error": "O Modulador IA está temporariamente indisponível. Tente novamente em instantes."
        }), 502

    # 4) Normalização do veredito
    try:
        nota = int(round(float(veredito.get('nota'))))
    except (TypeError, ValueError):
        nota = None
    if nota is not None:
        nota = max(0, min(100, nota))

    status_raw = (veredito.get('status') or '').strip().lower()
    aprovado = status_raw == 'aprovado'

    pontos = veredito.get('pontos_fortes')
    pendencias = veredito.get('pendencias')
    resultado = {
        "status": "Aprovado" if aprovado else "Revisão Necessária",
        "nota": nota,
        "feedback": (veredito.get('feedback') or '').strip(),
        "pontos_fortes": pontos if isinstance(pontos, list) else [],
        "pendencias": pendencias if isinstance(pendencias, list) else [],
    }

    # 4.1) Backstop determinístico da REGRA 2 — DoD exige link/portal mas não há URL
    import re as _re_url
    dod_lower = dod_texto.lower()
    exige_url = any(p in dod_lower for p in ('link', 'http', 'url', 'portal', 'publica', 'publicad', 'publicaç'))
    tem_url = bool(_re_url.search(r'https?://', _strip_html(evidencia)))
    if exige_url and not tem_url:
        aprovado = False
        nota = min(nota, 45) if nota is not None else 40
        msg = "O DoD exige link/publicação, mas nenhuma URL (http/https) foi encontrada na evidência."
        if msg not in resultado["pendencias"]:
            resultado["pendencias"].insert(0, msg)

    # 4.2) Guardrail da REGRA 4 — nota < 50 nunca aprova; coerência nota x status
    if nota is None:
        nota = 80 if aprovado else 40
    if nota < 50:
        aprovado = False
    if aprovado and nota < 50:
        aprovado = False

    resultado["status"] = "Aprovado" if aprovado else "Revisão Necessária"
    resultado["nota"] = nota
    status = resultado["status"]

    # 5) Persistência: veredito + nota de qualidade.
    # Encerramento da Sprint é SEMPRE do Cliente (nunca do Modulador/consultor).
    progresso = float(nota)
    try:
        from sprint_qualidade import aplicar_nota_modulador, sync_entregas_metricas

        sync_entregas_metricas(conn, int(id_sprn), sprint.get('derv_metr'))

        cur = conn.cursor()
        feedback_json = json.dumps(resultado, ensure_ascii=False)
        cur.execute(
            """
            UPDATE public.ctdi_sprn
            SET evidencia_texto = %s,
                modulador_status = %s,
                modulador_feedback = %s
            WHERE id_sprn = %s
            """,
            (evidencia, status, feedback_json, id_sprn),
        )
        conn.commit()
        cur.close()
        progresso = aplicar_nota_modulador(conn, int(id_sprn), nota)
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Falha ao persistir veredito do Modulador: {e}", file=sys.stderr)
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE public.ctdi_sprn SET realv_sprn = %s WHERE id_sprn = %s",
                (str(int(nota)), id_sprn),
            )
            conn.commit()
            cur.close()
        except Exception:
            conn.rollback()

    return jsonify({
        "success": True,
        "id_sprn": id_sprn,
        "sprint_concluida": False,
        "progresso_qualidade": progresso,
        **resultado,
    }), 200


@app.route('/api/ctdi_sprn/update-strategic', methods=['PUT'])
def update_sprint_strategic():
    # 1. Obter conexão
    conn = get_db_conn()

    try:
        data = request.json or {}
        id_sprn = data.get('id_sprn')

        if not id_sprn:
            return jsonify({"error": "ID da sprint não fornecido"}), 400

        from rbac.context import resolve_rbac_context
        from sprint_qualidade import (
            atualizar_dod_checklist,
            e_moderador,
            recalcular_progresso_sprint,
        )

        ctx = resolve_rbac_context()

        # Encerramento oficial: usar POST /api/sprints/fechar (Cliente + DoD 100% + média >= 80)
        raw_status = data.get('status')
        if raw_status:
            from sprint_governance import canonicalizar_status_dnd, STAT_CONCLUIDA
            canon = canonicalizar_status_dnd(raw_status)
            if canon == STAT_CONCLUIDA:
                return jsonify({
                    "error": "Use POST /api/sprints/fechar para encerrar a Sprint (Cliente; exige DoD 100% e qualidade >= 80%).",
                    "codigo": "use_endpoint_fechar",
                }), 400

        # Moderador não altera DoD / evolução operacional do cliente
        dod_itens = data.get('dod_itens') or data.get('itens')
        if isinstance(dod_itens, list) and dod_itens:
            if e_moderador(ctx):
                return jsonify({
                    "error": "O Moderador não marca DoD nem encerra a Sprint — apenas pontua métricas."
                }), 403
            atualizar_dod_checklist(conn, int(id_sprn), dod_itens)

        # Progresso qualitativo é calculado pelo backend (média das notas do moderador)
        progresso = recalcular_progresso_sprint(conn, int(id_sprn))

        update_data = {
            "swot_type": data.get('swot_type'),
            "swot_justification": data.get('swot_justification'),
            "evidence_url": data.get('evidence_url'),
            "exec_notes": data.get('exec_notes'),
            "metrics_scores": psycopg2.extras.Json(data.get('metrics_scores', {})),
            "realv_sprn": str(int(progresso)),
        }
        if raw_status:
            from sprint_governance import canonicalizar_status_dnd
            canon = canonicalizar_status_dnd(raw_status)
            if canon:
                update_data["stat_sprn"] = canon

        print(f"--- [DEBUG PYTHON] Atualizando Sprint {id_sprn} com dados estratégicos ---")

        success = db_manager.update_record(conn, 'ctdi_sprn', id_sprn, update_data)

        if success:
            return jsonify({
                "success": True,
                "message": "Evolução gravada com sucesso!",
                "progresso_qualidade": progresso,
            }), 200
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
        raw_grad = data.get('grad_ques')
        if raw_grad is None or raw_grad == 'na' or raw_grad == '':
            grad_ques = None
        else:
            try:
                grad_ques = int(raw_grad)
            except (TypeError, ValueError):
                grad_ques = None
        quali_ques = data.get('quali_ques') or ''

        # 1. VERIFICAÇÃO MANUAL: Já existe resposta para essa questão nesta maturidade?
        cursor.execute(
            "SELECT id_surv FROM public.ctdi_surv WHERE id_matu = %s AND id_ques = %s",
            (id_matu, id_ques)
        )
        record = cursor.fetchone()

        if record:
            cursor.execute(
                """UPDATE public.ctdi_surv
                   SET grad_ques = %s, quali_ques = %s
                   WHERE id_matu = %s AND id_ques = %s""",
                (grad_ques, quali_ques, id_matu, id_ques)
            )
        else:
            cursor.execute(
                """INSERT INTO public.ctdi_surv (id_matu, id_ques, id_dime, id_doma, grad_ques, quali_ques) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (id_matu, id_ques, data.get('id_dime'), data.get('id_doma'), grad_ques, quali_ques)
            )

        conn.commit()
        return jsonify({"message": "Resposta processada com ID preservado"}), 200

    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()


@app.route('/api/assessment/ia-master/coverage/<int:id_matu>', methods=['GET'])
def ia_master_coverage(id_matu):
    try:
        conn = get_db_conn()
        is_mini = request.args.get('mini', 'false').lower() == 'true'
        from ai_engine.agents.assessment_master_agent import AssessmentMasterAgent

        agent = AssessmentMasterAgent(db_manager)
        coverage = agent.get_coverage(conn, id_matu, is_mini=is_mini)
        return jsonify({"status": "ok", "coverage": coverage}), 200
    except Exception as e:
        print(f"Erro IA Master coverage: {e}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/assessment/ia-master/turn', methods=['POST'])
def ia_master_turn():
    try:
        conn = get_db_conn()
        data = request.json or {}
        id_matu = data.get('id_matu')
        if not id_matu:
            return jsonify({"status": "error", "message": "id_matu obrigatório"}), 400

        # TODO: Ajustar System Prompt do Claude quando tipo_mesa == 'organizacional'
        # (Mesa de Inovação Organizacional — Framework de Maturidade, sem contexto pedagógico).
        if (data.get('tipo_mesa') or '').strip().lower() == 'organizacional':
            pass  # Reservado para ramo dedicado da Mesa Org no IA Master.

        from ai_engine.agents.assessment_master_agent import AssessmentMasterAgent

        agent = AssessmentMasterAgent(db_manager)
        result = agent.process_turn(
            conn,
            int(id_matu),
            user_message=(data.get('message') or '').strip(),
            action=data.get('action') or 'message',
            history=data.get('history') or [],
            pending_answers=data.get('pending_answers') or [],
            is_mini=bool(data.get('is_mini')),
        )
        return jsonify(result), 200
    except Exception as e:
        print(f"Erro IA Master turn: {e}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500


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

        # Estatísticas híbridas para matriz de desempenho (CV + elo fraco)
        answers_for_matrix = db_manager.read_surveys_by_maturity(conn, id_matu)
        matrix_domain_stats = compute_matrix_domain_stats(answers_for_matrix)
        matrix_meta = build_matrix_meta(matrix_domain_stats)

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
                    "id_bloc": b.get('id_bloc'),
                    "nome": b.get('name_bloc'),
                    "desc": b.get('desc_bloc'),
                    "id_dime": int(b.get('id_dime')),
                    "id_doma": id_doma,
                }
                for b in blocks_data
                if int(b.get('id_doma')) == id_doma and int(b.get('id_dime')) in dimensoes_com_dor
            ]

            if not blocos_assertivos: continue

            dominio_data = benchmark_map.get(f"DOMA_{id_doma}")
            suggestions.append({
                "id_doma": id_doma,
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
            "id_clie": maturity.get('id_clie'),
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

            "matrix_domain_stats": matrix_domain_stats,
            "matrix_meta": matrix_meta,

            "benchmark_setorial": benchmark_data_serialized,
            "suggestions": suggestions,
        }

        plano_json = maturity.get('json_plano_estrategico')
        if isinstance(plano_json, dict):
            reserva = plano_json.get('backlog_geral_relatorio') or []
            if reserva:
                report["backlog_geral_relatorio"] = reserva
            from estrategia_matriz import resolver_hierarquia_objetivo

            roadmap = plano_json.get('roadmap_estrategico') or []
            tatico = (plano_json.get('plano_tatico_problema') or {}).get('sprints_resolucao') or []
            objetivos_plano = []
            for item in list(roadmap) + list(tatico):
                if not isinstance(item, dict):
                    continue
                oid = item.get('id_objetivo') or item.get('objetivo_id')
                if not oid:
                    continue
                try:
                    hier = resolver_hierarquia_objetivo(conn, int(oid))
                except (TypeError, ValueError):
                    hier = None
                if hier:
                    objetivos_plano.append({
                        **hier,
                        'id_bloco': item.get('id_bloco'),
                        'nome_sprint': item.get('nome_sprint'),
                    })
            if objetivos_plano:
                report['objetivos_vinculados_plano'] = objetivos_plano

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
SES_BOTO_CONFIG = Config(connect_timeout=8, read_timeout=12, retries={'max_attempts': 2})
SES_PLACEHOLDER_DOMAINS = ('seudominio.com.br', 'example.com', 'seudominio.com')


def _resolve_email_sender():
    """Retorna remetente SES verificado, ignorando placeholders do .env.example."""
    candidates = [
        os.environ.get('EMAIL_SENDER'),
        os.environ.get('MAIL_USERNAME'),
        app.config.get('MAIL_USERNAME') if app else None,
        'consultant@paneldx.com.br',
    ]
    for sender in candidates:
        if not sender:
            continue
        normalized = sender.strip().lower()
        if any(domain in normalized for domain in SES_PLACEHOLDER_DOMAINS):
            continue
        return sender.strip()
    return 'consultant@paneldx.com.br'


def _resolve_ses_region():
    return (
        os.environ.get('AWS_DEFAULT_REGION')
        or os.environ.get('AWS_REGION')
        or 'us-east-2'
    )


def _resolve_paneldx_public_url():
    """URL pública do frontend PanelDX (link no e-mail de acesso)."""
    candidates = [
        os.environ.get('PANELDX_PUBLIC_URL'),
        os.environ.get('FRONTEND_URL'),
        'http://localhost:3000',
    ]
    for url in candidates:
        if url and str(url).strip():
            return str(url).strip().rstrip('/')
    return 'https://paneldx.com.br'


def dispatch_access_code_email(recipient, access_code, access_url_base=None):
    """Envia o código em background para não bloquear cadastro/login."""
    resolved_base = access_url_base or _resolve_paneldx_public_url()

    def _worker():
        with app.app_context():
            ok = send_report_email_ses(
                recipient=recipient,
                access_code=access_code,
                aws_region=_resolve_ses_region(),
                access_url_base=resolved_base,
            )
            if not ok:
                print(
                    f"⚠️ [SES] Falha ao enviar código para {recipient}. "
                    f"Verifique EMAIL_SENDER ({_resolve_email_sender()}) e identidades no SES.",
                    file=sys.stderr,
                )

    print(
        f"📧 [SES] Agendando e-mail para {recipient} (código {access_code}, base {resolved_base})...",
        file=sys.stderr,
    )
    threading.Thread(target=_worker, daemon=True, name=f"ses-{recipient}").start()


def send_report_email_ses(recipient, access_code, aws_region=None, access_url_base=None):
    """
    Envia o e-mail de código de acesso usando o AWS SES (Boto3), incluindo o corpo HTML.
    """
    aws_region = aws_region or _resolve_ses_region()

    # 1. Configurar o cliente SES
    try:
        ses_client = boto3.client('ses', region_name=aws_region, config=SES_BOTO_CONFIG)
    except Exception as e:
        print(f"ERRO CRÍTICO ao inicializar cliente Boto3/SES: {e}", file=sys.stderr)
        return False

    # 2. Definir o URL de Acesso (Usando a lógica de request.url_root)
    if access_url_base:
        access_url = access_url_base.rstrip('/') + '/acesso'
    else:
        try:
            access_url = request.url_root.replace('/api/', '') + 'acesso'
        except RuntimeError:
            access_url = f"{_resolve_paneldx_public_url()}/acesso"

    # Adiciona o access_code à URL
    access_url_with_code = f"{access_url}/{access_code}"

    # 3. Montar a Mensagem
    sender_email = _resolve_email_sender()
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
            dispatch_access_code_email(lead_data['MAIL_CLIE'], access_code)
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
# ROTA: STATUS DA GÊNESE IA (polling — máquina de estados)
# ========================================================================================
@app.route('/api/client/genese-status/<int:id_matu>', methods=['GET'])
def get_genese_status(id_matu):
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute(
            """
            SELECT m.status_ia, p.fase_atual
            FROM ctdi_matu m
            LEFT JOIN ctdi_projetos p ON p.id_clie = m.id_clie
            WHERE m.id_matu = %s
            LIMIT 1
            """,
            (id_matu,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Maturidade não encontrada"}), 404

        cur.execute(
            """
            SELECT COUNT(s.id_sprn) AS total_sprints
            FROM ctdi_main m
            JOIN ctdi_itera i ON m.id_ctdi = i.id_ctdi
            LEFT JOIN ctdi_sprn s ON i.id_itera = s.id_itera
            WHERE m.id_matu = %s
            """,
            (id_matu,),
        )
        sprint_row = cur.fetchone() or {}
        total_sprints = int(sprint_row.get('total_sprints') or 0)

        status_ia = (row.get('status_ia') or '').strip().upper()
        tem_sprints = total_sprints > 0
        plano_pronto = status_ia == 'CONCLUIDO' and tem_sprints
        em_processamento = status_ia in ('PENDENTE', 'PROCESSANDO')

        cur.close()
        conn.close()

        return jsonify({
            "status_ia": status_ia,
            "fase_atual": row.get('fase_atual') or '',
            "tem_sprints": tem_sprints,
            "total_sprints": total_sprints,
            "plano_pronto": plano_pronto,
            "em_processamento": em_processamento,
            "erro": status_ia == 'ERRO_IA',
        }), 200

    except Exception as e:
        if conn:
            conn.close()
        print(f"❌ Erro em genese-status: {e}")
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
                     s.dtend_sprn, \
                     s.url_kanban, \
                     s.metrics_scores
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
                    "id_sprn": row['id_sprn'],
                    "nome": row['name_sprn'],
                    "name_sprn": row['name_sprn'],
                    "objetivo": row['desc_sprn'] or 'Foco em implementação estratégica.',
                    "desc_sprn": row['desc_sprn'],
                    "status": row['stat_sprn'] or 'planejada',
                    "stat_sprn": row['stat_sprn'] or 'planejada',
                    "data_inicio": row['dtini_sprn'],
                    "dtini_sprn": row['dtini_sprn'],
                    "data_fim": row['dtend_sprn'],
                    "dtend_sprn": row['dtend_sprn'],
                    "url_kanban": row['url_kanban'],
                    "metrics_scores": row['metrics_scores']
                })

        # Sprints DX importadas da Mesa (sem iteração vinculada ainda) — visíveis no Kanban
        cursor.execute("SELECT id_clie FROM ctdi_matu WHERE id_matu = %s LIMIT 1;", (id_matu,))
        row_clie = cursor.fetchone()
        if row_clie:
            id_clie_hub = row_clie['id_clie']
            cursor.execute(
                """
                SELECT s.id_sprn,
                       s.name_sprn,
                       s.desc_sprn,
                       s.stat_sprn,
                       s.dtini_sprn,
                       s.dtend_sprn,
                       s.url_kanban,
                       s.metrics_scores
                FROM ctdi_sprn s
                WHERE s.url_kanban = 'IMPORTACAO_JSON_DX'
                  AND LOWER(TRIM(REPLACE(s.stat_sprn, '_', ' '))) IN (
                      'em analise', 'em_analise',
                      'planejada_backlog', 'planejada', 'planejado', 'pendente'
                  )
                  AND (s.metrics_scores ->> 'id_clie')::int = %s
                ORDER BY s.id_sprn DESC;
                """,
                (id_clie_hub,)
            )
            dx_rows = cursor.fetchall()
            ids_ja_na_jornada = {
                sp.get('id_sprn') or sp.get('id')
                for onda in jornada_map.values()
                for sp in onda.get('sprints', [])
            }
            dx_orfas = []
            for dx in dx_rows:
                if dx['id_sprn'] in ids_ja_na_jornada:
                    continue
                dx_orfas.append({
                    "id": dx['id_sprn'],
                    "id_sprn": dx['id_sprn'],
                    "nome": dx['name_sprn'],
                    "name_sprn": dx['name_sprn'],
                    "objetivo": dx['desc_sprn'] or 'Sprint gerada pela Mesa de Inovação.',
                    "desc_sprn": dx['desc_sprn'],
                    "status": dx['stat_sprn'] or 'em analise',
                    "stat_sprn": dx['stat_sprn'] or 'em analise',
                    "data_inicio": dx['dtini_sprn'],
                    "dtini_sprn": dx['dtini_sprn'],
                    "data_fim": dx['dtend_sprn'],
                    "dtend_sprn": dx['dtend_sprn'],
                    "url_kanban": dx['url_kanban'],
                    "metrics_scores": dx['metrics_scores']
                })

            if dx_orfas:
                jornada_map[-999] = {
                    "id": -999,
                    "nome": "Inovação DX",
                    "status": "em analise",
                    "sprints": dx_orfas
                }

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
                         stat_sprn  = 'em_andamento'
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
    id_clie = request.args.get('id_clie')
    email = (request.args.get('email') or '').strip()
    conn = db_manager._connect_db()
    cur = conn.cursor()

    try:
        base_query = """
                     SELECT DISTINCT ON (q.id_squad)
                                     q.id_squad,
                                     q.nome_squad,
                                     p.id_ctdi,
                                     COALESCE(m.name_ctdi, 'Projeto sem Nome') as name_ctdi,
                                     c.nome_clie,
                                     m.id_matu,
                                     p.id_proj,
                                     p.id_clie,
                                     s.name_sprn,
                                     s.stat_sprn
                     FROM ctdi_squads q
                              JOIN ctdi_projetos p ON q.id_proj = p.id_proj
                              JOIN ctdi_sprn s ON q.id_squad = s.id_squad
                              LEFT JOIN ctdi_main m ON p.id_ctdi = m.id_ctdi
                              LEFT JOIN ctdi_matu mt ON m.id_matu = mt.id_matu
                              LEFT JOIN ctdi_clie c ON p.id_clie = c.id_clie
                     WHERE p.status = 'ATIVO'
                       AND LOWER(TRIM(COALESCE(s.stat_sprn, ''))) NOT IN ('concluida', 'cancelada')
                     """

        def _fetch_projetos(for_id_clie):
            order_tail = """
                ORDER BY q.id_squad,
                    CASE WHEN LOWER(TRIM(COALESCE(s.stat_sprn, ''))) IN ('ativa', 'em_andamento') THEN 0 ELSE 1 END,
                    s.ordr_sprn ASC NULLS LAST,
                    q.id_squad ASC
            """
            if role == 'ADMIN':
                query = base_query + order_tail
                cur.execute(query)
            else:
                query = base_query + " AND p.id_clie = %s" + order_tail
                cur.execute(query, (for_id_clie,))
            return cur.fetchall()

        def _resolve_id_clie_by_email(mail):
            if not mail:
                return None
            cur.execute(
                """
                SELECT id_clie FROM public.ctdi_clie
                WHERE LOWER(TRIM(mail_clie)) = LOWER(TRIM(%s))
                LIMIT 1
                """,
                (mail,),
            )
            row = cur.fetchone()
            return row[0] if row else None

        if role != 'ADMIN':
            resolved = _resolve_id_clie_by_email(email)
            if resolved:
                id_clie = resolved
            if not id_clie:
                return jsonify([])

        rows = _fetch_projetos(id_clie)
        if role != 'ADMIN' and not rows and email:
            alt_id = _resolve_id_clie_by_email(email)
            if alt_id and str(alt_id) != str(id_clie):
                id_clie = alt_id
                rows = _fetch_projetos(id_clie)

        projetos = []
        for row in rows:
            projetos.append({
                "id_squad": row[0],
                "nome_squad": row[1],
                "id_ctdi": row[2],
                "name_ctdi": row[3],
                "nome_clie": row[4],
                "id_matu": row[5],
                "id_proj": row[6],
                "id_clie": row[7],
                "name_sprn": row[8],
                "stat_sprn": row[9],
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
              AND s.stat_sprn IN ('ativa', 'em_andamento')
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
            from rbac.constants import ROLE_LED, ROLE_SYSADMIN
            from rbac.context import resolve_rbac_context
            from rbac.users import rbac_id_clie_da_squad

            ctx = resolve_rbac_context()
            if ctx.system_role == ROLE_LED and ctx.id_clie:
                squad_clie = rbac_id_clie_da_squad(cur, int(id_squad))
                if squad_clie is None or int(squad_clie) != int(ctx.id_clie):
                    return jsonify({"error": "Squad não pertence à sua empresa."}), 403

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
                           id_usuario,
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
                    "id_team": r[6],
                    "id_squad": r[6],
                    "id_usuario": r[7],
                    "data_cadastro": r[8].strftime('%d/%m/%Y %H:%M') if r[8] else None
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
            from rbac.auth_helpers import rbac_map_system_role_to_team_role
            from rbac.constants import ROLE_LED
            from rbac.context import resolve_rbac_context
            from rbac.users import rbac_buscar_usuario_por_id, rbac_id_clie_da_squad, rbac_vincular_team_ao_usuario

            ctx = resolve_rbac_context()

            # 1. Limpeza de Segurança e Ajuste de IDs
            data.pop('id_member', None)  # Garante que o banco gere o ID (PK)

            id_usuario_payload = data.get('id_usuario')
            if not id_usuario_payload:
                return jsonify({
                    "error": "Selecione um membro da empresa ou cadastre um novo em Gestão de Time.",
                }), 403

            id_squad_novo = data.get('id_squad') or data.get('id_team')
            if ctx.system_role == ROLE_LED and ctx.id_clie and id_squad_novo:
                squad_clie = rbac_id_clie_da_squad(cur, int(id_squad_novo))
                if squad_clie is None or int(squad_clie) != int(ctx.id_clie):
                    return jsonify({"error": "Squad não pertence à sua empresa."}), 403

            usuario = rbac_buscar_usuario_por_id(cur, int(id_usuario_payload))
            if not usuario or not usuario.get('ativo'):
                return jsonify({"error": "Usuário não encontrado ou inativo."}), 404
            if ctx.system_role == ROLE_LED and ctx.id_clie:
                uid_clie = usuario.get('id_clie')
                role_user = (usuario.get('system_role') or '').lower()
                if role_user in ('consultor', 'sysadmin'):
                    return jsonify({"error": "Consultores são alocados apenas pelo SysAdmin."}), 403
                if uid_clie is None or int(uid_clie) != int(ctx.id_clie):
                    return jsonify({"error": "Usuário não pertence à sua empresa."}), 403

            data['nome'] = usuario['nome']
            data['email'] = usuario['email']
            data['role'] = rbac_map_system_role_to_team_role(usuario['system_role'])
            if usuario.get('password_hash'):
                data['password_hash'] = usuario['password_hash']
            data['id_usuario'] = int(id_usuario_payload)
            data.pop('senha', None)

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

            email_membro = (data.get('email') or '').strip()
            id_squad_novo = data.get('id_squad')
            capacidade_info = {}
            if email_membro and id_squad_novo:
                from rbac.capacity import CAPACIDADE_MSG_PADRAO, rbac_validar_capacidade_squad
                capacidade_info = rbac_validar_capacidade_squad(
                    cur, email=email_membro, id_squad=int(id_squad_novo)
                )
                if capacidade_info.get("bloqueado"):
                    return jsonify({
                        "error": capacidade_info.get("error") or CAPACIDADE_MSG_PADRAO,
                    }), 409

            data.pop('system_role', None)
            columns = [c for c in columns if c != 'system_role']
            if data.get('id_usuario') and 'id_usuario' not in columns:
                columns.append('id_usuario')

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

            id_usuario = int(data.get('id_usuario'))
            rbac_vincular_team_ao_usuario(cur, id_member=new_id, id_usuario=id_usuario)

            conn.commit()

            print(f"✅ [DEBUG POST] Sucesso! Novo ID: {new_id} na Squad: {data.get('id_squad')}")
            return jsonify({"success": True, "id": new_id, "id_usuario": id_usuario}), 201

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

            from rbac.auth_helpers import rbac_map_system_role_to_team_role
            from rbac.constants import ROLE_LED
            from rbac.context import resolve_rbac_context
            from rbac.users import rbac_buscar_usuario_por_id

            ctx = resolve_rbac_context()
            id_usuario_payload = data.get('id_usuario')

            if id_usuario_payload:
                usuario = rbac_buscar_usuario_por_id(cur, int(id_usuario_payload))
                if usuario:
                    data['nome'] = usuario['nome']
                    data['email'] = usuario['email']
                    data['role'] = rbac_map_system_role_to_team_role(usuario['system_role'])
            elif ctx.system_role == ROLE_LED:
                cur.execute(
                    "SELECT id_usuario, nome, email, role FROM ctdi_team WHERE id_member = %s LIMIT 1;",
                    (id_member,),
                )
                row = cur.fetchone()
                if row:
                    data['nome'] = row[1] if not isinstance(row, dict) else row.get('nome')
                    data['email'] = row[2] if not isinstance(row, dict) else row.get('email')
                    data['role'] = row[3] if not isinstance(row, dict) else row.get('role')

            # Ajuste de compatibilidade para o id_squad (caso venha como id_team)
            target_squad = data.get('id_squad') or data.get('id_team')
            email_membro = (data.get('email') or '').strip()

            if email_membro and target_squad:
                from rbac.capacity import CAPACIDADE_MSG_PADRAO, rbac_validar_capacidade_squad
                capacidade_info = rbac_validar_capacidade_squad(
                    cur,
                    email=email_membro,
                    id_squad=int(target_squad),
                    id_member_excluir=id_member,
                )
                if capacidade_info.get("bloqueado"):
                    return jsonify({
                        "error": capacidade_info.get("error") or CAPACIDADE_MSG_PADRAO,
                    }), 409

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

            from rbac.users import rbac_sync_usuario_from_team_row, rbac_vincular_team_ao_usuario
            id_usuario = data.get('id_usuario')
            if id_usuario:
                rbac_vincular_team_ao_usuario(cur, id_member=id_member, id_usuario=int(id_usuario))
            else:
                id_usuario = rbac_sync_usuario_from_team_row(
                    cur,
                    email=email_membro,
                    nome=data.get('nome') or email_membro,
                    role=data.get('role'),
                    position=data.get('position'),
                    password_hash=data.get('password_hash'),
                )
                rbac_vincular_team_ao_usuario(cur, id_member=id_member, id_usuario=int(id_usuario))

            conn.commit()
            return jsonify({"success": True, "id_usuario": id_usuario})

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


def _coluna_existe(cur, tabela, coluna):
    """Verifica se uma coluna existe (defensivo para colunas criadas dinamicamente)."""
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        LIMIT 1
        """,
        (tabela, coluna),
    )
    return cur.fetchone() is not None


def _tabela_existe(cur, tabela):
    cur.execute("SELECT to_regclass(%s)", (f"public.{tabela}",))
    row = cur.fetchone()
    return bool(row and row[0])


@app.route('/api/admin/agentes/metricas', methods=['GET'])
def get_agentes_metricas():
    """
    NOC Multi-Agentes (visão SysAdmin): agrega métricas operacionais dos 4 agentes
    de IA — Master (planejamento), Modulador (auditoria), Consultor (apoio tático)
    e Inovador (lapidação). Cada bloco é isolado em try/except para que a falha de
    uma métrica não derrube o painel inteiro. Sempre responde 200 com fallbacks.
    """
    resposta = {
        "success": True,
        "agentes": {
            "master": {"status": "online", "atuacoes": 0, "concluidos": 0, "com_pdf": 0,
                       "metrica_label": "Relatórios concluídos", "metrica_valor": 0},
            "modulador": {"status": "online", "atuacoes": 0, "aprovadas": 0, "reprovadas": 0,
                          "taxa_aprovacao": 0, "metrica_label": "Taxa de aprovação", "metrica_valor": 0},
            "consultor": {"status": "online", "atuacoes": 0,
                          "metrica_label": "Sessões de apoio", "metrica_valor": 0},
            "inovador": {"status": "online", "atuacoes": 0, "lapidadas": 0, "fallbacks": 0,
                         "taxa_fallback": 0, "alerta_fallback": False,
                         "metrica_label": "Inovações lapidadas", "metrica_valor": 0},
        },
        "totais": {"chamadas_globais": 0, "por_agente": {}},
        "grafico": {"labels": ["Master", "Modulador", "Consultor", "Inovador"], "volume": [0, 0, 0, 0]},
    }

    conn = None
    try:
        conn = db_manager._connect_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 1) AGENTE MASTER — relatórios de inteligência (ctdi_matu)
        try:
            cur.execute(
                """
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE UPPER(COALESCE(status_ia, '')) = 'CONCLUIDO') AS concluidos,
                       COUNT(*) FILTER (WHERE url_pdf_ia IS NOT NULL AND TRIM(url_pdf_ia) <> '') AS com_pdf
                FROM public.ctdi_matu
                """
            )
            row = cur.fetchone()
            m = resposta["agentes"]["master"]
            m["atuacoes"] = int(row["total"] or 0)
            m["concluidos"] = int(row["concluidos"] or 0)
            m["com_pdf"] = int(row["com_pdf"] or 0)
            m["metrica_valor"] = m["concluidos"]
        except Exception as e:
            print(f"⚠️ [NOC] Métrica Master falhou: {e}", file=sys.stderr)
            conn.rollback()

        # 2) AGENTE MODULADOR — sprints avaliadas (coluna dinâmica modulador_status)
        try:
            if _coluna_existe(cur, 'ctdi_sprn', 'modulador_status'):
                cur.execute(
                    """
                    SELECT COUNT(*) FILTER (WHERE modulador_status IS NOT NULL) AS avaliadas,
                           COUNT(*) FILTER (WHERE modulador_status = 'Aprovado') AS aprovadas,
                           COUNT(*) FILTER (WHERE modulador_status = 'Revisão Necessária') AS reprovadas
                    FROM public.ctdi_sprn
                    """
                )
                row = cur.fetchone()
                md = resposta["agentes"]["modulador"]
                md["atuacoes"] = int(row["avaliadas"] or 0)
                md["aprovadas"] = int(row["aprovadas"] or 0)
                md["reprovadas"] = int(row["reprovadas"] or 0)
                if md["atuacoes"] > 0:
                    md["taxa_aprovacao"] = round((md["aprovadas"] / md["atuacoes"]) * 100)
                md["metrica_valor"] = md["taxa_aprovacao"]
        except Exception as e:
            print(f"⚠️ [NOC] Métrica Modulador falhou: {e}", file=sys.stderr)
            conn.rollback()

        # 3) CONSULTOR LEACTION — proxy: sprints geradas via Fast Track ('Inovação Sob Demanda')
        try:
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM public.ctdi_sprn s
                         JOIN public.ctdi_itera i ON s.id_itera = i.id_itera
                WHERE i.name_itera ILIKE '%%Sob Demanda%%'
                """
            )
            row = cur.fetchone()
            cs = resposta["agentes"]["consultor"]
            cs["atuacoes"] = int(row["total"] or 0)
            cs["metrica_valor"] = cs["atuacoes"]
        except Exception as e:
            print(f"⚠️ [NOC] Métrica Consultor falhou: {e}", file=sys.stderr)
            conn.rollback()

        # 4) AGENTE INOVADOR — ações lapidadas + fallbacks (inov_acoes)
        try:
            if _tabela_existe(cur, 'inov_acoes'):
                cur.execute(
                    """
                    SELECT COUNT(*) AS total,
                           COUNT(*) FILTER (WHERE composicao_estruturada IS NOT NULL) AS lapidadas,
                           COUNT(*) FILTER (
                               WHERE composicao_estruturada IS NULL
                                 AND COALESCE(status_acao, 'Em Estruturacao') = 'Em Estruturacao'
                           ) AS fallbacks
                    FROM public.inov_acoes
                    """
                )
                row = cur.fetchone()
                inv = resposta["agentes"]["inovador"]
                inv["atuacoes"] = int(row["total"] or 0)
                inv["lapidadas"] = int(row["lapidadas"] or 0)
                inv["fallbacks"] = int(row["fallbacks"] or 0)
                if inv["atuacoes"] > 0:
                    inv["taxa_fallback"] = round((inv["fallbacks"] / inv["atuacoes"]) * 100)
                inv["alerta_fallback"] = inv["taxa_fallback"] >= 30
                inv["metrica_valor"] = inv["lapidadas"]
        except Exception as e:
            print(f"⚠️ [NOC] Métrica Inovador falhou: {e}", file=sys.stderr)
            conn.rollback()

        cur.close()

        # 5) TOTAIS / VOLUME GLOBAL (sem tabela de tokens: soma das atuações)
        ag = resposta["agentes"]
        por_agente = {
            "Master": ag["master"]["atuacoes"],
            "Modulador": ag["modulador"]["atuacoes"],
            "Consultor": ag["consultor"]["atuacoes"],
            "Inovador": ag["inovador"]["atuacoes"],
        }
        resposta["totais"]["por_agente"] = por_agente
        resposta["totais"]["chamadas_globais"] = sum(por_agente.values())
        resposta["grafico"]["volume"] = list(por_agente.values())

        return jsonify(resposta), 200

    except Exception as e:
        print(f"❌ Erro no NOC de agentes: {e}", file=sys.stderr)
        traceback.print_exc()
        resposta["success"] = False
        resposta["error"] = str(e)
        return jsonify(resposta), 200
    finally:
        if conn:
            conn.close()


# =========================================================================
# Panorama Executivo — taxonomia fixa de direcionadores + área escolar (leaf_dime)
# =========================================================================
_leaf_dime_area_ensured = False

PANORAMA_DIRECIONADORES_FIXOS = [
    {
        "slug": "digitalizacao_organizacional",
        "nome": "Digitalização Organizacional",
        "meta_financeira": "reducao_custo",
        "meta_label": "Redução de Custo",
        "icone": "📉",
        "keywords": ("digitalização organizacional", "digitalizacao organizacional"),
    },
    {
        "slug": "engajamento_comunidade",
        "nome": "Engajamento da Comunidade",
        "meta_financeira": "aumento_receita",
        "meta_label": "Aumento de Receita",
        "icone": "💰",
        "keywords": ("engajamento da comunidade", "engajamento"),
    },
    {
        "slug": "capacitacao_docente",
        "nome": "Capacitação Docente",
        "meta_financeira": "reducao_custo",
        "meta_label": "Redução de Custo",
        "icone": "📉",
        "keywords": ("capacitação docente", "capacitacao docente"),
    },
    {
        "slug": "prontidao_tecnologica",
        "nome": "Prontidão Tecnológica",
        "meta_financeira": "reducao_custo",
        "meta_label": "Redução de Custo",
        "icone": "📉",
        "keywords": ("prontidão tecnológica", "prontidao tecnologica", "infraestrutura"),
    },
    {
        "slug": "novos_modelos_negocio",
        "nome": "Novos Modelos de Negócio",
        "meta_financeira": "aumento_receita",
        "meta_label": "Aumento de Receita",
        "icone": "💰",
        "keywords": ("novos modelos de negócio", "novos modelos de negocio", "modelo de neg"),
    },
]

ORDEM_AREAS_ESCOLARES = [
    "Diretoria",
    "Desenvolvimento Humano",
    "Administração e Secretaria",
    "Pedagógico",
    "Tecnologia da Informação",
]


def _ensure_leaf_dime_area_escolar(conn):
    """Garante coluna area_escolar e carga SV/HC/FS/LA/DA (idempotente)."""
    global _leaf_dime_area_ensured
    if _leaf_dime_area_ensured:
        return
    cur = conn.cursor()
    try:
        cur.execute(
            """
            ALTER TABLE public.leaf_dime
                ADD COLUMN IF NOT EXISTS area_escolar VARCHAR(80);
            """
        )
        cur.execute(
            """
            UPDATE public.leaf_dime SET area_escolar = 'Diretoria'
            WHERE UPPER(TRIM(COALESCE(code_dime, ''))) = 'SV'
               OR name_dime ILIKE '%Visão Compartilhada%';
            UPDATE public.leaf_dime SET area_escolar = 'Desenvolvimento Humano'
            WHERE UPPER(TRIM(COALESCE(code_dime, ''))) = 'HC'
               OR name_dime ILIKE '%Coração e Conexão%';
            UPDATE public.leaf_dime SET area_escolar = 'Administração e Secretaria'
            WHERE UPPER(TRIM(COALESCE(code_dime, ''))) = 'FS'
               OR name_dime ILIKE '%Estrutura Fluida%';
            UPDATE public.leaf_dime SET area_escolar = 'Pedagógico'
            WHERE UPPER(TRIM(COALESCE(code_dime, ''))) = 'LA'
               OR name_dime ILIKE '%Aprendizagem em Ação%';
            UPDATE public.leaf_dime SET area_escolar = 'Tecnologia da Informação'
            WHERE UPPER(TRIM(COALESCE(code_dime, ''))) = 'DA'
               OR name_dime ILIKE '%Arquitetura Digital%';
            """
        )
        conn.commit()
        _leaf_dime_area_ensured = True
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Falha ao garantir area_escolar em leaf_dime: {e}", file=sys.stderr)
    finally:
        cur.close()


def _match_direcionador_db(nome_db: str, catalog_item: dict) -> bool:
    nome_l = (nome_db or "").strip().lower()
    if not nome_l:
        return False
    if nome_l == catalog_item["nome"].lower():
        return True
    return any(kw in nome_l for kw in catalog_item["keywords"])


def _montar_direcionadores_panorama(rows_db: list[dict]) -> list[dict]:
    """Mescla catálogo fixo com progresso vindo do módulo OKR (quando existir)."""
    saida = []
    for item in PANORAMA_DIRECIONADORES_FIXOS:
        percentual = 0
        sub_okrs = []
        total_objetivos = 0
        for row in rows_db:
            if _match_direcionador_db(row.get("nome_direc"), item):
                total = int(row.get("total_ativ") or 0)
                concl = int(row.get("concluidas") or 0)
                percentual = min(100, round((concl / total) * 100)) if total > 0 else 0
                sub_okrs = row.get("sub_okrs") or []
                total_objetivos = int(row.get("total_objetivos") or 0)
                break
        saida.append({
            "slug": item["slug"],
            "nome": item["nome"],
            "percentual": percentual,
            "meta_financeira": item["meta_financeira"],
            "meta_label": item["meta_label"],
            "icone": item["icone"],
            "total_objetivos": total_objetivos,
            "is_catalogo_fixo": True,
            "sub_okrs": sub_okrs,
        })
    return saida


def _direcionadores_panorama_from_painel(conn, id_clie: int) -> list[dict]:
    """Direcionadores canônicos primeiro, customizados depois — com progresso e contagem de objetivos."""
    from estrategia_matriz import carregar_painel_okr_cliente

    painel = carregar_painel_okr_cliente(conn, int(id_clie))
    dirs = painel.get("direcionadores") or []
    if not dirs:
        return _montar_direcionadores_panorama([])

    saida = []
    for d in dirs:
        slug = (d.get("slug_catalogo") or "").strip()
        canonical = next((c for c in PANORAMA_DIRECIONADORES_FIXOS if c["slug"] == slug), None)
        nome = d.get("nome_direc") or (canonical["nome"] if canonical else "Direcionador")
        meta_fin = d.get("meta_financeira") or (canonical["meta_financeira"] if canonical else "reducao_custo")
        meta_label = d.get("meta_label") or (canonical["meta_label"] if canonical else "Redução de Custo")
        icone = d.get("icone") or (canonical["icone"] if canonical else "🎯")
        saida.append({
            "slug": slug or f"custom_{d['id_direc']}",
            "nome": nome,
            "percentual": int(d.get("progresso_pct") or 0),
            "meta_financeira": meta_fin,
            "meta_label": meta_label,
            "icone": icone,
            "total_objetivos": int(d.get("total_objetivos") or 0),
            "is_catalogo_fixo": bool(d.get("is_catalogo_fixo")),
            "sub_okrs": [],
        })
    return saida


def _normalizar_heatmap_carga(linhas: list[dict]) -> dict:
    """Pivot area_escolar × sprint com intensidade 0–100."""
    if not linhas:
        return {"areas": [], "sprints": [], "matriz": []}

    areas_set = set()
    sprints_set = []
    sprint_index = {}
    pivot = {}

    for row in linhas:
        area = row.get("area_escolar") or "Sem área"
        sprint = row.get("sprint_nome") or "Sprint"
        raw = int(row.get("carga_raw") or 0)
        areas_set.add(area)
        if sprint not in sprint_index:
            sprint_index[sprint] = len(sprints_set)
            sprints_set.append(sprint)
        pivot[(area, sprint)] = pivot.get((area, sprint), 0) + raw

    areas = [a for a in ORDEM_AREAS_ESCOLARES if a in areas_set]
    areas += sorted(a for a in areas_set if a not in areas)

    matriz = []
    max_val = max(pivot.values()) if pivot else 1
    for area in areas:
        linha = []
        for sprint in sprints_set:
            raw = pivot.get((area, sprint), 0)
            pct = round((raw / max_val) * 100) if max_val > 0 else 0
            linha.append(min(100, pct))
        matriz.append(linha)

    sprint_labels = [f"Sprint {i + 1}" for i in range(len(sprints_set))]
    return {"areas": areas, "sprints": sprint_labels, "matriz": matriz}


@app.route('/api/dashboard/consolidado', methods=['GET'])
def get_dashboard_consolidado():
    """
    Cockpit Panorama Executivo: status de sprints (incl. Inovação em análise),
    direcionadores estratégicos fixos, heatmap por area_escolar e KPIs operacionais.
    """
    id_matu = request.args.get('id_matu')

    resposta = {
        "success": True,
        "id_matu": id_matu,
        "status_sprints": {
            "planejada": 0,
            "ativa": 0,
            "concluida": 0,
            "inovacao_analise": 0,
        },
        "kpis": {
            "sprints_ativas": 0,
            "tarefas_atrasadas": 0,
            "entregas_no_prazo": 0,
        },
        "direcionadores": _montar_direcionadores_panorama([]),
        "percentual_medio_direcionadores": 0,
        "heatmap_alocacao": {"areas": [], "sprints": [], "matriz": []},
        "progresso_okrs": [],
        "carga_squads": [],
        "totais": {"sprints": 0, "okrs": 0, "squads": 0},
    }

    if not id_matu:
        resposta["success"] = False
        resposta["error"] = "id_matu e obrigatorio."
        return jsonify(resposta), 400

    conn = None
    try:
        conn = db_manager._connect_db()
        _ensure_leaf_dime_area_escolar(conn)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 1) STATUS DAS SPRINTS — 4 baldes (inclui Mesa de Inovação / em análise)
        cur.execute(
            """
            SELECT CASE
                       WHEN LOWER(REPLACE(TRIM(COALESCE(s.stat_sprn, '')), '_', ' '))
                            = 'em analise' THEN 'inovacao_analise'
                       WHEN LOWER(TRIM(COALESCE(s.stat_sprn, ''))) = 'concluida' THEN 'concluida'
                       WHEN LOWER(TRIM(COALESCE(s.stat_sprn, '')))
                            IN ('ativa', 'em_andamento', 'em andamento') THEN 'ativa'
                       WHEN LOWER(TRIM(COALESCE(s.stat_sprn, ''))) IN (
                            'planejada_backlog', 'planejada', 'planejado', 'pendente'
                       ) THEN 'planejada'
                   END AS status_norm,
                   COUNT(*) AS total
            FROM ctdi_sprn s
                     JOIN ctdi_itera i ON s.id_itera = i.id_itera
                     JOIN ctdi_main m ON i.id_ctdi = m.id_ctdi
            WHERE m.id_matu = %s
            GROUP BY status_norm
            """,
            (id_matu,),
        )
        for row in cur.fetchall():
            key = row["status_norm"]
            if key in resposta["status_sprints"]:
                resposta["status_sprints"][key] = int(row["total"])

        # Sprints da Mesa de Inovação ainda sem iteração (importação DX)
        cur.execute("SELECT id_clie FROM ctdi_matu WHERE id_matu = %s LIMIT 1;", (id_matu,))
        row_clie = cur.fetchone()
        id_clie = int(row_clie["id_clie"]) if row_clie and row_clie.get("id_clie") else None
        if row_clie:
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM ctdi_sprn s
                WHERE s.url_kanban = 'IMPORTACAO_JSON_DX'
                  AND LOWER(REPLACE(TRIM(COALESCE(s.stat_sprn, '')), '_', ' ')) = 'em analise'
                  AND (s.metrics_scores ->> 'id_clie')::int = %s
                """,
                (row_clie["id_clie"],),
            )
            mesa = cur.fetchone()
            if mesa:
                resposta["status_sprints"]["inovacao_analise"] += int(mesa["total"] or 0)

        resposta["kpis"]["sprints_ativas"] = resposta["status_sprints"]["ativa"]

        # KPIs de tarefas (atividades OKR vinculadas às sprints do matu)
        cur.execute(
            """
            SELECT COUNT(a.id_ativ) FILTER (
                       WHERE LOWER(TRIM(COALESCE(a.status_ativ, ''))) <> 'entregue'
                         AND a.data_planejamento IS NOT NULL
                         AND a.data_planejamento < CURRENT_DATE
                   ) AS atrasadas,
                   COUNT(a.id_ativ) FILTER (
                       WHERE LOWER(TRIM(COALESCE(a.status_ativ, ''))) = 'entregue'
                   ) AS entregues
            FROM ctdi_okr_atividades a
                     JOIN ctdi_sprn s ON a.id_sprn = s.id_sprn
                     JOIN ctdi_itera i ON s.id_itera = i.id_itera
                     JOIN ctdi_main m ON i.id_ctdi = m.id_ctdi
            WHERE m.id_matu = %s
            """,
            (id_matu,),
        )
        kpi_row = cur.fetchone() or {}
        resposta["kpis"]["tarefas_atrasadas"] = int(kpi_row.get("atrasadas") or 0)
        resposta["kpis"]["entregas_no_prazo"] = int(kpi_row.get("entregues") or 0)

        # 2) DIRECIONADORES ESTRATÉGICOS (canônicos + customizados, ordenados)
        if id_clie:
            resposta["direcionadores"] = _direcionadores_panorama_from_painel(conn, id_clie)
        else:
            resposta["direcionadores"] = _montar_direcionadores_panorama([])
        percents = [d["percentual"] for d in resposta["direcionadores"]]
        resposta["percentual_medio_direcionadores"] = (
            round(sum(percents) / len(percents)) if percents else 0
        )

        # Compatibilidade legada (progresso_okrs = KRs individuais)
        cur.execute(
            """
            SELECT k.id_kr,
                   COALESCE(NULLIF(TRIM(k.nome_kr), ''), 'KR ' || k.id_kr) AS nome_kr,
                   COUNT(a.id_ativ) AS total_ativ,
                   COUNT(a.id_ativ) FILTER (
                       WHERE LOWER(TRIM(COALESCE(a.status_ativ, ''))) = 'entregue'
                   ) AS concluidas
            FROM ctdi_okr_krs k
                     JOIN ctdi_okr_objetivos_dt o ON k.id_obj_dt = o.id_obj_dt
                     JOIN ctdi_okr_direcionadores d ON o.id_direc = d.id_direc
                     JOIN ctdi_matu m ON m.id_clie = d.id_clie
                     LEFT JOIN ctdi_okr_atividades a ON a.id_kr = k.id_kr
            WHERE m.id_matu = %s
            GROUP BY k.id_kr, k.nome_kr
            HAVING COUNT(a.id_ativ) > 0
            ORDER BY concluidas DESC, k.id_kr ASC
            LIMIT 12
            """,
            (id_matu,),
        )
        for row in cur.fetchall():
            total = int(row["total_ativ"] or 0)
            concluidas = int(row["concluidas"] or 0)
            percentual = min(100, round((concluidas / total) * 100)) if total > 0 else 0
            resposta["progresso_okrs"].append({
                "id_kr": row["id_kr"],
                "name": row["nome_kr"],
                "total": total,
                "concluidos": concluidas,
                "percentual": percentual,
            })

        # 3) HEATMAP — area_escolar (leaf_dime) × sprint, via bloco metodológico
        cur.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(d.area_escolar), ''), 'Sem área') AS area_escolar,
                   COALESCE(NULLIF(TRIM(s.name_sprn), ''), 'Sprint ' || s.id_sprn::text) AS sprint_nome,
                   COUNT(a.id_ativ) AS carga_raw
            FROM ctdi_sprn s
                     JOIN ctdi_itera i ON s.id_itera = i.id_itera
                     JOIN ctdi_main m ON i.id_ctdi = m.id_ctdi
                     LEFT JOIN leaf_bloc b ON s.id_bloc = b.id_bloc
                     LEFT JOIN leaf_dime d ON b.id_dime = d.id_dime
                     LEFT JOIN ctdi_okr_atividades a ON a.id_sprn = s.id_sprn
            WHERE m.id_matu = %s
            GROUP BY d.area_escolar, s.id_sprn, s.name_sprn
            ORDER BY s.id_sprn ASC
            """,
            (id_matu,),
        )
        heat_rows = [dict(r) for r in cur.fetchall()]
        if not heat_rows:
            cur.execute(
                """
                SELECT COALESCE(NULLIF(TRIM(d.area_escolar), ''), 'Sem área') AS area_escolar,
                       COALESCE(NULLIF(TRIM(s.name_sprn), ''), 'Sprint ' || s.id_sprn::text) AS sprint_nome,
                       1 AS carga_raw
                FROM ctdi_sprn s
                         JOIN ctdi_itera i ON s.id_itera = i.id_itera
                         JOIN ctdi_main m ON i.id_ctdi = m.id_ctdi
                         LEFT JOIN leaf_bloc b ON s.id_bloc = b.id_bloc
                         LEFT JOIN leaf_dime d ON b.id_dime = d.id_dime
                WHERE m.id_matu = %s
                ORDER BY s.id_sprn ASC
                """,
                (id_matu,),
            )
            heat_rows = [dict(r) for r in cur.fetchall()]

        resposta["heatmap_alocacao"] = _normalizar_heatmap_carga(heat_rows)

        # 4) Carga por squad (legado)
        cur.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(sq.nome_squad), ''), 'Sem Squad') AS nome_squad,
                   COUNT(s.id_sprn) AS total
            FROM ctdi_sprn s
                     JOIN ctdi_itera i ON s.id_itera = i.id_itera
                     JOIN ctdi_main m ON i.id_ctdi = m.id_ctdi
                     LEFT JOIN ctdi_squads sq ON s.id_squad = sq.id_squad
            WHERE m.id_matu = %s
            GROUP BY sq.nome_squad
            ORDER BY total DESC
            """,
            (id_matu,),
        )
        for row in cur.fetchall():
            resposta["carga_squads"].append({
                "squad": row["nome_squad"],
                "total": int(row["total"] or 0),
            })

        cur.close()

        resposta["totais"] = {
            "sprints": sum(resposta["status_sprints"].values()),
            "okrs": len(resposta["progresso_okrs"]),
            "squads": len(resposta["carga_squads"]),
        }

        return jsonify(resposta), 200

    except Exception as e:
        print(f"❌ Erro na rota Dashboard Consolidado: {str(e)}", file=sys.stderr)
        resposta["success"] = False
        resposta["error"] = str(e)
        return jsonify(resposta), 500
    finally:
        if conn:
            conn.close()


# =========================================================================
# Agenda Executiva — eventos e bloco de notas (Dashboard)
# =========================================================================
_agenda_eventos_ensured = False


def _ensure_agenda_eventos_table(conn):
    global _agenda_eventos_ensured
    if _agenda_eventos_ensured:
        return
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.agenda_eventos (
                id_evento    SERIAL PRIMARY KEY,
                id_matu      INTEGER NOT NULL,
                data_evento  TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                titulo       VARCHAR(200) NOT NULL,
                nota_texto   TEXT,
                criado_em    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_agenda_eventos_matu
                    FOREIGN KEY (id_matu) REFERENCES public.ctdi_matu (id_matu) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_agenda_eventos_matu_data
                ON public.agenda_eventos (id_matu, data_evento);
            """
        )
        conn.commit()
        _agenda_eventos_ensured = True
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Falha ao garantir agenda_eventos: {e}", file=sys.stderr)
    finally:
        cur.close()


@app.route('/api/agenda-eventos', methods=['GET', 'POST'])
def agenda_eventos():
    conn = None
    try:
        conn = get_db_conn()
        _ensure_agenda_eventos_table(conn)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if request.method == 'GET':
            id_matu = request.args.get('id_matu')
            mes = request.args.get('mes')  # YYYY-MM
            if not id_matu:
                return jsonify({"success": False, "error": "id_matu obrigatório"}), 400

            sql = """
                SELECT id_evento, id_matu, data_evento, titulo, nota_texto, criado_em
                FROM public.agenda_eventos
                WHERE id_matu = %s
            """
            params = [id_matu]
            if mes:
                sql += " AND to_char(data_evento, 'YYYY-MM') = %s"
                params.append(mes)
            sql += " ORDER BY data_evento ASC, id_evento ASC"
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                if r.get("data_evento"):
                    r["data_evento"] = r["data_evento"].isoformat()
                if r.get("criado_em"):
                    r["criado_em"] = r["criado_em"].isoformat()
            cur.close()
            return jsonify({"success": True, "eventos": rows}), 200

        data = request.get_json() or {}
        id_matu = data.get('id_matu')
        titulo = (data.get('titulo') or '').strip()
        data_evento = data.get('data_evento')
        if not id_matu or not titulo or not data_evento:
            return jsonify({
                "success": False,
                "error": "id_matu, titulo e data_evento são obrigatórios"
            }), 400

        cur.execute(
            """
            INSERT INTO public.agenda_eventos (id_matu, data_evento, titulo, nota_texto)
            VALUES (%s, %s, %s, %s)
            RETURNING id_evento, id_matu, data_evento, titulo, nota_texto, criado_em
            """,
            (id_matu, data_evento, titulo, data.get('nota_texto') or ''),
        )
        row = dict(cur.fetchone())
        conn.commit()
        if row.get("data_evento"):
            row["data_evento"] = row["data_evento"].isoformat()
        if row.get("criado_em"):
            row["criado_em"] = row["criado_em"].isoformat()
        cur.close()
        return jsonify({"success": True, "evento": row}), 201

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Erro agenda-eventos: {e}", file=sys.stderr)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/agenda-eventos/<int:id_evento>', methods=['GET', 'PUT', 'DELETE'])
def agenda_evento_item(id_evento):
    conn = None
    try:
        conn = get_db_conn()
        _ensure_agenda_eventos_table(conn)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if request.method == 'GET':
            cur.execute(
                """
                SELECT id_evento, id_matu, data_evento, titulo, nota_texto, criado_em
                FROM public.agenda_eventos WHERE id_evento = %s
                """,
                (id_evento,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"success": False, "error": "Evento não encontrado"}), 404
            out = dict(row)
            if out.get("data_evento"):
                out["data_evento"] = out["data_evento"].isoformat()
            if out.get("criado_em"):
                out["criado_em"] = out["criado_em"].isoformat()
            return jsonify({"success": True, "evento": out}), 200

        if request.method == 'DELETE':
            cur.execute("DELETE FROM public.agenda_eventos WHERE id_evento = %s", (id_evento,))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"success": False, "error": "Evento não encontrado"}), 404
            return jsonify({"success": True}), 200

        data = request.get_json() or {}
        titulo = (data.get('titulo') or '').strip()
        if not titulo:
            return jsonify({"success": False, "error": "titulo obrigatório"}), 400

        cur.execute(
            """
            UPDATE public.agenda_eventos
            SET titulo = %s,
                nota_texto = %s,
                data_evento = COALESCE(%s, data_evento)
            WHERE id_evento = %s
            RETURNING id_evento, id_matu, data_evento, titulo, nota_texto, criado_em
            """,
            (
                titulo,
                data.get('nota_texto') or '',
                data.get('data_evento'),
                id_evento,
            ),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "Evento não encontrado"}), 404
        conn.commit()
        out = dict(row)
        if out.get("data_evento"):
            out["data_evento"] = out["data_evento"].isoformat()
        if out.get("criado_em"):
            out["criado_em"] = out["criado_em"].isoformat()
        return jsonify({"success": True, "evento": out}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# =========================================================================
# 🏛️ PADRÃO HOLDING — Multi-Tier BI (camada consolidada de Redes de Ensino)
# =========================================================================
_holding_cols_ensured = False
_contexto_cols_ensured = False


def _ensure_contexto_columns(conn):
    """Garante (idempotente) colunas de contexto institucional em ctdi_clie."""
    global _contexto_cols_ensured
    if _contexto_cols_ensured:
        return
    cur = conn.cursor()
    try:
        cur.execute(
            """
            ALTER TABLE public.ctdi_clie
                ADD COLUMN IF NOT EXISTS bairro_clie        VARCHAR(120),
                ADD COLUMN IF NOT EXISTS cidade_clie        VARCHAR(120),
                ADD COLUMN IF NOT EXISTS estado_clie        VARCHAR(2),
                ADD COLUMN IF NOT EXISTS dados_etnograficos TEXT,
                ADD COLUMN IF NOT EXISTS dados_mercado      TEXT,
                ADD COLUMN IF NOT EXISTS moderacao_dados_mercado          TEXT,
                ADD COLUMN IF NOT EXISTS moderacao_dados_etnograficos     TEXT,
                ADD COLUMN IF NOT EXISTS moderacao_clima_organizacional   TEXT;
            """
        )
        conn.commit()
        _contexto_cols_ensured = True
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Falha ao garantir colunas de contexto: {e}", file=sys.stderr)
    finally:
        cur.close()


def _ensure_holding_columns(conn):
    """Garante (idempotente) id_rede e is_holding em ctdi_clie."""
    global _holding_cols_ensured
    if _holding_cols_ensured:
        return
    cur = conn.cursor()
    try:
        cur.execute(
            """
            ALTER TABLE public.ctdi_clie
                ADD COLUMN IF NOT EXISTS id_rede    VARCHAR(100),
                ADD COLUMN IF NOT EXISTS is_holding BOOLEAN DEFAULT FALSE;
            """
        )
        conn.commit()
        _holding_cols_ensured = True
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Falha ao garantir colunas Holding: {e}", file=sys.stderr)
    finally:
        cur.close()


def _normalizar_id_rede(val):
    """Padroniza o identificador da rede (ex: REDE_OBJETIVO)."""
    if val is None:
        return None
    s = str(val).strip().upper()
    return s or None


def _holding_panorama_vazio(id_rede=None, nome_rede=None, aviso=None):
    """Resposta real vazia (sem mock) quando a rede não tem unidades."""
    rede = id_rede or ''
    return {
        "success": True,
        "mock": False,
        "id_rede": rede,
        "nome_rede": nome_rede or (rede.replace('_', ' ').title() if rede else "Rede não configurada"),
        "consolidado": {
            "total_sprints_concluidas": 0,
            "media_progresso_maturidade": 0.0,
            "total_inovacoes": 0,
            "total_unidades": 0,
        },
        "unidades": [],
        "aviso": aviso or "Nenhuma unidade vinculada a esta rede ainda.",
    }


def _buscar_nome_rede(cur, id_rede):
    """Nome amigável da rede a partir das empresas/unidades cadastradas."""
    cur.execute(
        """
        SELECT COALESCE(
                   MAX(CASE WHEN COALESCE(is_holding, false)
                       THEN NULLIF(TRIM(empresa_clie), '') END),
                   MAX(NULLIF(TRIM(empresa_clie), '')),
                   MAX(NULLIF(TRIM(nome_clie), ''))
               ) AS nome
        FROM public.ctdi_clie
        WHERE UPPER(TRIM(COALESCE(id_rede, ''))) = %s
        """,
        (id_rede,),
    )
    row = cur.fetchone()
    if row and row.get('nome'):
        return row['nome']
    return id_rede.replace('_', ' ').title()


def _holding_panorama_mock(id_rede=None):
    """Dados demonstrativos para desenhar o Cockpit quando a rede ainda não tem unidades."""
    rede = id_rede or 'REDE_XPTO'
    unidades = [
        {"id_clie": 101, "nome_clie": "Colégio Centro", "progresso_maturidade": 72.0,
         "sprints_concluidas": 15, "inovacoes_geradas": 4},
        {"id_clie": 102, "nome_clie": "Colégio Sul", "progresso_maturidade": 65.0,
         "sprints_concluidas": 12, "inovacoes_geradas": 3},
        {"id_clie": 103, "nome_clie": "Escola Norte", "progresso_maturidade": 58.0,
         "sprints_concluidas": 9, "inovacoes_geradas": 2},
        {"id_clie": 104, "nome_clie": "Unidade Leste", "progresso_maturidade": 79.0,
         "sprints_concluidas": 11, "inovacoes_geradas": 3},
    ]
    media = round(sum(u["progresso_maturidade"] for u in unidades) / len(unidades), 1)
    return {
        "success": True,
        "mock": True,
        "id_rede": rede,
        "nome_rede": rede.replace('_', ' ').title(),
        "consolidado": {
            "total_sprints_concluidas": sum(u["sprints_concluidas"] for u in unidades),
            "media_progresso_maturidade": media,
            "total_inovacoes": sum(u["inovacoes_geradas"] for u in unidades),
            "total_unidades": len(unidades),
        },
        "unidades": unidades,
    }


@app.route('/api/holding/redes', methods=['GET'])
def list_holding_redes():
    """Lista redes distintas cadastradas em ctdi_clie (para admin / fallback do cockpit)."""
    conn = None
    try:
        conn = db_manager._connect_db()
        _ensure_holding_columns(conn)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT UPPER(TRIM(id_rede)) AS id_rede,
                   COUNT(*) FILTER (WHERE NOT COALESCE(is_holding, false)) AS qtd_unidades,
                   COUNT(*) FILTER (WHERE COALESCE(is_holding, false))     AS qtd_gestores
            FROM public.ctdi_clie
            WHERE NULLIF(TRIM(COALESCE(id_rede, '')), '') IS NOT NULL
            GROUP BY UPPER(TRIM(id_rede))
            ORDER BY UPPER(TRIM(id_rede)) ASC
            """
        )
        redes = [dict(r) for r in cur.fetchall()]
        cur.close()
        return jsonify({"success": True, "redes": redes}), 200
    except Exception as e:
        print(f"❌ Erro ao listar redes holding: {e}", file=sys.stderr)
        return jsonify({"success": False, "error": str(e), "redes": []}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/holding/panorama', methods=['GET'])
def get_holding_panorama():
    """
    Panorama consolidado da Rede de Ensino (Padrão Holding).
    Agrupa todas as unidades (ctdi_clie) com o mesmo id_rede.
    Dados reais do banco; mock apenas com ?mock=1 (demonstração).
    """
    id_rede = _normalizar_id_rede(
        request.args.get('id_rede') or request.args.get('rede')
    )
    id_clie = request.args.get('id_clie')
    forcar_mock = str(request.args.get('mock', '')).lower() in ('1', 'true', 'yes')

    conn = None
    try:
        conn = db_manager._connect_db()
        _ensure_holding_columns(conn)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Resolve id_rede a partir do gestor logado, se não veio na query
        if not id_rede and id_clie:
            cur.execute(
                "SELECT id_rede FROM public.ctdi_clie WHERE id_clie = %s",
                (id_clie,),
            )
            row = cur.fetchone()
            if row:
                id_rede = _normalizar_id_rede(row.get('id_rede'))

        if forcar_mock:
            cur.close()
            return jsonify(_holding_panorama_mock(id_rede)), 200

        if not id_rede:
            cur.close()
            return jsonify(_holding_panorama_vazio(
                aviso="Nenhuma rede vinculada. Configure o id_rede no painel de Clientes."
            )), 200

        # Unidades da rede (exclui o login gestor holding)
        cur.execute(
            """
            SELECT c.id_clie,
                   COALESCE(
                       NULLIF(TRIM(c.empresa_clie), ''),
                       NULLIF(TRIM(c.nome_clie), ''),
                       NULLIF(TRIM(c.mail_clie), '')
                   ) AS nome_clie,
                   COALESCE(lm.pgen_pres, 0)::float AS progresso_maturidade,
                   COALESCE(sp.sprints_concluidas, 0)::int AS sprints_concluidas,
                   COALESCE(inv.inovacoes_geradas, 0)::int AS inovacoes_geradas
            FROM public.ctdi_clie c
                     LEFT JOIN LATERAL (
                SELECT m.pgen_pres
                FROM public.ctdi_matu m
                WHERE m.id_clie = c.id_clie
                ORDER BY m.id_matu DESC
                LIMIT 1
                ) lm ON TRUE
                     LEFT JOIN LATERAL (
                SELECT COUNT(*) AS sprints_concluidas
                FROM public.ctdi_sprn s
                         JOIN public.ctdi_itera i ON s.id_itera = i.id_itera
                         JOIN public.ctdi_main cm ON i.id_ctdi = cm.id_ctdi
                         JOIN public.ctdi_matu mat ON cm.id_matu = mat.id_matu
                WHERE mat.id_clie = c.id_clie
                  AND LOWER(TRIM(COALESCE(s.stat_sprn, ''))) IN (
                      'concluida', 'concluída', 'concluido', 'finalizada', 'done'
                  )
                ) sp ON TRUE
                     LEFT JOIN LATERAL (
                SELECT COUNT(*) AS inovacoes_geradas
                FROM public.inov_acoes ia
                WHERE ia.id_clie = c.id_clie
                ) inv ON TRUE
            WHERE UPPER(TRIM(COALESCE(c.id_rede, ''))) = %s
              AND COALESCE(c.is_holding, false) = false
            ORDER BY nome_clie ASC
            """,
            (id_rede,),
        )
        unidades_raw = cur.fetchall()
        nome_rede = _buscar_nome_rede(cur, id_rede)
        cur.close()

        if not unidades_raw:
            return jsonify(_holding_panorama_vazio(
                id_rede, nome_rede,
                "Nenhuma unidade vinculada a esta rede. Vincule escolas em Clientes → Configurar Rede."
            )), 200

        unidades = []
        for u in unidades_raw:
            unidades.append({
                "id_clie": u["id_clie"],
                "nome_clie": u["nome_clie"],
                "progresso_maturidade": round(float(u["progresso_maturidade"] or 0), 1),
                "sprints_concluidas": int(u["sprints_concluidas"] or 0),
                "inovacoes_geradas": int(u["inovacoes_geradas"] or 0),
            })

        total_sprints = sum(x["sprints_concluidas"] for x in unidades)
        total_inov = sum(x["inovacoes_geradas"] for x in unidades)
        media_mat = round(
            sum(x["progresso_maturidade"] for x in unidades) / len(unidades), 1
        ) if unidades else 0.0

        return jsonify({
            "success": True,
            "mock": False,
            "id_rede": id_rede,
            "nome_rede": nome_rede,
            "consolidado": {
                "total_sprints_concluidas": total_sprints,
                "media_progresso_maturidade": media_mat,
                "total_inovacoes": total_inov,
                "total_unidades": len(unidades),
            },
            "unidades": unidades,
        }), 200

    except Exception as e:
        print(f"❌ Erro na rota Holding Panorama: {e}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({"success": False, "mock": False, "error": str(e)}), 500
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
                SELECT m.id_matu, c.nome_clie, m.dt_fim_ia, m.url_pdf_ia, m.pgen_gap,
                       m.txt_diagnostico_ia, m.json_plano_estrategico, m.status_ia
                FROM ctdi_matu m
                         JOIN ctdi_clie c ON m.id_clie = c.id_clie
                WHERE m.id_matu = %s \
                """
        cur.execute(query, (id_matu,))
        registro = cur.fetchone()
        cur.close()

        if not registro:
            return jsonify({"error": "Plano vazio"}), 404

        txt = (registro.get('txt_diagnostico_ia') or '').strip()
        placeholder = txt.startswith('Aguardando Ativação')
        plano_json = registro.get('json_plano_estrategico')
        if (not txt or placeholder) and plano_json and isinstance(plano_json, dict):
            from ai_engine.gerar_diagnostico_ia import LeActionAIProcessor
            ts = registro.get('dt_fim_ia')
            if hasattr(ts, 'strftime'):
                ts = ts.strftime('%d/%m/%Y %H:%M')
            else:
                ts = str(ts or datetime.now().strftime('%d/%m/%Y %H:%M'))
            txt = LeActionAIProcessor._markdown_from_plano(plano_json, ts)
            registro['txt_diagnostico_ia'] = txt
        elif not txt or placeholder:
            return jsonify({"error": "Plano vazio"}), 404

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

        def media(lista):
            return sum(lista) / len(lista) if lista else 0.0

        def coerce_grad(nota):
            if nota is None:
                return None
            if isinstance(nota, str) and nota.strip().lower() in ('na', 'null', ''):
                return None
            try:
                return float(nota)
            except (TypeError, ValueError):
                return None

        p_count = f_count = 0
        for d_id, doma_id, prefu, nota in respostas:
            n = coerce_grad(nota)
            if n is None or d_id is None or doma_id is None:
                continue
            prefu_key = (prefu or 'P').strip().upper()
            if prefu_key not in ('P', 'F'):
                prefu_key = 'F' if prefu_key.startswith('F') else 'P'
            stats_dime[int(d_id)][prefu_key].append(n)
            if prefu_key == 'F':
                f_count += 1
            else:
                p_count += 1

            key = (int(d_id), int(doma_id))
            if key not in stats_doma:
                stats_doma[key] = {'P': [], 'F': []}
            stats_doma[key][prefu_key].append(n)

        print(f">>> [PRESURVEY] Respostas agregadas — Presente: {p_count}, Futuro: {f_count}")

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

        # Ordem das colunas: estrat (dime 1), organiz (dime 3), humana (dime 2), pedag (4), tecno (5)
        _ordem_dimensoes_presurvey = (1, 3, 2, 4, 5)
        valores = (
            id_matu,
            *[
                score
                for d in _ordem_dimensoes_presurvey
                for score in (
                    media(stats_dime.get(d, {}).get('P', [])),
                    media(stats_dime.get(d, {}).get('F', [])),
                )
            ],
            json.dumps(insights_data)
        )

        cur.execute(insert_query, valores)
        cur.execute("UPDATE public.ctdi_matu SET status_ia = 'PRESURVEY OK' WHERE id_matu = %s", (id_matu,))

        # Funil: assessment inicial concluído sem consultor → novo_lead (órfão)
        try:
            from services.funil_engine import garantir_oportunidade_orfao
            from psycopg2.extras import RealDictCursor as _RDC
            cur_funil = conn.cursor(cursor_factory=_RDC)
            cur_funil.execute(
                """
                SELECT m.id_clie, c.nome_clie, c.mail_clie, c.fone_clie, c.empresa_clie, c.init_role
                FROM public.ctdi_matu m
                INNER JOIN public.ctdi_clie c ON c.id_clie = m.id_clie
                WHERE m.id_matu = %s
                LIMIT 1;
                """,
                (id_matu,),
            )
            row_funil = cur_funil.fetchone()
            if row_funil:
                row_funil = dict(row_funil)
                if (row_funil.get("init_role") or "GENERAL").strip().upper() != "SOLO":
                    garantir_oportunidade_orfao(
                        cur_funil,
                        id_clie=int(row_funil["id_clie"]),
                        id_matu=int(id_matu),
                        nome=row_funil.get("nome_clie"),
                        email=row_funil.get("mail_clie"),
                        telefone=row_funil.get("fone_clie"),
                        empresa=row_funil.get("empresa_clie"),
                    )
            cur_funil.close()
        except Exception as funil_err:
            print(f"⚠️ [FUNIL] Falha ao garantir lead órfão pós-presurvey: {funil_err}", file=sys.stderr)

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
        cur.execute(
            """
            SELECT c.id_clie, c.mail_clie
            FROM public.ctdi_matu m
            JOIN public.ctdi_clie c ON m.id_clie = c.id_clie
            WHERE m.id_matu = %s
            LIMIT 1
            """,
            (id_matu,),
        )
        mail_row = cur.fetchone()
        id_clie_lead = int(mail_row[0]) if mail_row and mail_row[0] else None
        mail_clie = (mail_row[1] or "").strip() if mail_row else ""

        response = {
            "lead": {
                "id_matu": id_matu,
                "id_clie": id_clie_lead,
                "empresa_clie": row[0],
                "status_ia": row[1],
                "mail_clie": mail_clie,
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
_okr_gamificacao_ensured = False


def _ensure_okr_gamificacao_schema(conn):
    global _okr_gamificacao_ensured
    if _okr_gamificacao_ensured:
        return
    cur = conn.cursor()
    try:
        cur.execute(
            """
            ALTER TABLE public.ctdi_okr_direcionadores
                ADD COLUMN IF NOT EXISTS slug_catalogo VARCHAR(80);
            ALTER TABLE public.ctdi_okr_direcionadores
                ADD COLUMN IF NOT EXISTS meta_financeira VARCHAR(32);
            ALTER TABLE public.ctdi_okr_direcionadores
                ADD COLUMN IF NOT EXISTS icone VARCHAR(16);
            CREATE TABLE IF NOT EXISTS public.ctdi_okr_comentarios (
                id_comentario SERIAL PRIMARY KEY,
                id_clie       INTEGER NOT NULL,
                entidade_tipo VARCHAR(32) NOT NULL,
                entidade_id   INTEGER NOT NULL,
                autor_nome    VARCHAR(120),
                texto         TEXT NOT NULL,
                criado_em     TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_okr_comentarios_entidade
                ON public.ctdi_okr_comentarios (id_clie, entidade_tipo, entidade_id);
            """
        )
        conn.commit()
        _okr_gamificacao_ensured = True
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Falha ao garantir schema OKR gamificação: {e}", file=sys.stderr)
    finally:
        cur.close()


def _garantir_direcionadores_fixos_okr(conn, id_clie: int) -> None:
    """Garante a matriz canônica OKR instanciada para o cliente."""
    from estrategia_matriz import garantir_okr_cliente_desde_matriz

    _ensure_okr_gamificacao_schema(conn)
    garantir_okr_cliente_desde_matriz(conn, int(id_clie))


@app.route('/api/okr/consolidado', methods=['GET'])
@app.route('/api/okr/consolidado/<int:id_clie>', methods=['GET'])
def get_okr_consolidado(id_clie=None):
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
        id_clie = id_clie or request.args.get('id_clie')
        if not id_clie:
            return jsonify({"error": "O parâmetro 'id_clie' é obrigatório."}), 400

        _garantir_direcionadores_fixos_okr(conn, int(id_clie))

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
                       d.slug_catalogo, \
                       d.meta_financeira, \
                       d.icone, \
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
                              AND COALESCE(k.ativo, true) = true
                WHERE d.id_clie = %s
                ORDER BY
                    CASE WHEN d.slug_catalogo IS NOT NULL THEN 0 ELSE 1 END,
                    d.slug_catalogo ASC NULLS LAST,
                    d.id_direc ASC,
                    o.id_obj_dt ASC,
                    k.id_kr ASC; \
                """

        cur.execute(query, (id_clie,))
        rows = cur.fetchall()

        if not any(r.get('id_kr') for r in rows):
            _garantir_kr_inovacao(cur, int(id_clie))
            conn.commit()
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


@app.route('/api/okr/comentarios', methods=['GET', 'POST'])
def okr_comentarios():
    conn = None
    try:
        conn = get_db_conn()
        _ensure_okr_gamificacao_schema(conn)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if request.method == 'GET':
            id_clie = request.args.get('id_clie')
            entidade_tipo = request.args.get('entidade_tipo')
            entidade_id = request.args.get('entidade_id')
            if not id_clie:
                return jsonify({"error": "id_clie obrigatório"}), 400
            sql = """
                SELECT id_comentario, id_clie, entidade_tipo, entidade_id,
                       autor_nome, texto, criado_em
                FROM public.ctdi_okr_comentarios
                WHERE id_clie = %s
            """
            params = [id_clie]
            if entidade_tipo and entidade_id:
                sql += " AND entidade_tipo = %s AND entidade_id = %s"
                params.extend([entidade_tipo, entidade_id])
            sql += " ORDER BY criado_em DESC"
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                if r.get("criado_em"):
                    r["criado_em"] = r["criado_em"].isoformat()
            return jsonify({"success": True, "comentarios": rows}), 200

        data = request.get_json() or {}
        id_clie = data.get('id_clie')
        entidade_tipo = data.get('entidade_tipo')
        entidade_id = data.get('entidade_id')
        texto = (data.get('texto') or '').strip()
        if not id_clie or not entidade_tipo or not entidade_id or not texto:
            return jsonify({"error": "id_clie, entidade_tipo, entidade_id e texto são obrigatórios"}), 400
        cur.execute(
            """
            INSERT INTO public.ctdi_okr_comentarios
                (id_clie, entidade_tipo, entidade_id, autor_nome, texto)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_comentario, id_clie, entidade_tipo, entidade_id, autor_nome, texto, criado_em
            """,
            (
                id_clie,
                entidade_tipo,
                entidade_id,
                data.get('autor_nome') or 'Gestor',
                texto,
            ),
        )
        row = dict(cur.fetchone())
        conn.commit()
        if row.get("criado_em"):
            row["criado_em"] = row["criado_em"].isoformat()
        return jsonify({"success": True, "comentario": row}), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


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

        payload = dict(data)
        if not payload.get('desc_kr') and payload.get('nome_kr'):
            payload['desc_kr'] = payload['nome_kr']
        payload.setdefault('ativo', True)
        payload.setdefault('valor_inicial', 0)
        payload.setdefault('valor_alvo', 100)
        payload.setdefault('valor_atual', 0)
        payload.setdefault('status_kr', 'Em Andamento')
        if not payload.get('kpi_nome'):
            payload['kpi_nome'] = 'Meta personalizada'

        # Executa a escrita diretamente
        db_manager.create_record(conn, 'ctdi_okr_krs', payload)

        # Sucesso baseado em execução limpa
        return jsonify({"success": True, "message": "Key Result estabelecido com sucesso!"}), 201

    except Exception as e:
        print(f"Erro ao inserir KR: {e}", file=sys.stderr)
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/okr/atividades', methods=['GET', 'POST'])
def handle_atividades():
    """
    Gerenciamento do Nivel 4: Atividades operacionais vinculadas as Sprints
    """
    conn = None
    try:
        conn = get_db_conn()
    except Exception as e:
        print(f"Erro CRITICO ao obter conexao com DB: {e}", file=sys.stderr)
        return jsonify({"success": False, "error": "Erro de conexao com o banco de dados."}), 500

    try:
        if request.method == 'GET':
            id_sprn = request.args.get('id_sprn')
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            if id_sprn:
                query = "SELECT * FROM public.ctdi_okr_atividades WHERE id_sprn = %s ORDER BY id_ativ ASC"
                cur.execute(query, (id_sprn,))
            else:
                cur.execute("SELECT * FROM public.ctdi_okr_atividades ORDER BY id_ativ ASC")
            records = [
                db_manager.convert_record_to_json_safe(dict(row))
                for row in cur.fetchall()
            ]
            cur.close()
            return jsonify(records), 200

        # POST
        data = dict(request.json or {})
        if not data:
            return jsonify({"success": False, "error": "Payload JSON vazio."}), 400

        if data.get('status_ativ'):
            data['status_ativ'] = _normalize_status_atividade(data['status_ativ'])
        elif data.get('data_conclusao'):
            data['status_ativ'] = 'Entregue'

        if _normalize_status_atividade(data.get('status_ativ')) == 'Entregue':
            data['status_ativ'] = 'Entregue'
            if not data.get('data_conclusao'):
                data['data_conclusao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not data.get('id_kr'):
            return jsonify({
                "success": False,
                "error": "id_kr (Key Result alvo) é obrigatório para vincular a atividade ao OKR.",
            }), 400

        cur_val = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur_val.execute(
            """
            SELECT dx_kr_id, COALESCE(ativo, true) AS ativo
            FROM public.ctdi_okr_krs WHERE id_kr = %s
            """,
            (int(data['id_kr']),),
        )
        kr_row = cur_val.fetchone()
        cur_val.close()
        if not kr_row:
            return jsonify({
                "success": False,
                "error": "Key Result selecionado não encontrado.",
            }), 400
        if not kr_row.get('ativo', True):
            return jsonify({
                "success": False,
                "error": "Este KR está suprimido. Reative-o na matriz estratégica antes de vincular atividades.",
            }), 400
        # Canônico: sincroniza dx_kr_id. Personalizado: NULL permitido.
        data['dx_kr_id'] = int(kr_row['dx_kr_id']) if kr_row.get('dx_kr_id') else None

        executor_id = data.get('executor_id') or data.get('id_team')
        if not executor_id:
            return jsonify({
                "success": False,
                "error": "executor_id é obrigatório para registrar a atividade.",
            }), 400
        try:
            executor_id = int(executor_id)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "executor_id inválido."}), 400
        data['executor_id'] = executor_id
        data['id_team'] = executor_id

        new_id = db_manager.create_record(conn, 'ctdi_okr_atividades', data)
        if not new_id:
            return jsonify({"success": False, "error": "Nao foi possivel registrar a atividade (ID nao retornado)."}), 500

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT * FROM public.ctdi_okr_atividades WHERE id_ativ = %s",
            (new_id,),
        )
        created = cur.fetchone()
        cur.close()

        if created and executor_id:
            from rbac.notifications import rbac_notificar_nova_atribuicao
            cur_n = conn.cursor()
            try:
                rbac_notificar_nova_atribuicao(
                    cur_n,
                    executor_id=executor_id,
                    nome_ativ=data.get('nome_ativ') or 'Tarefa',
                    id_ativ=new_id,
                    id_sprn=data.get('id_sprn'),
                    alteracao=False,
                )
                conn.commit()
            finally:
                cur_n.close()

        registro = db_manager.convert_record_to_json_safe(dict(created)) if created else {"id_ativ": new_id}
        return jsonify({
            "success": True,
            "message": "Atividade operacional vinculada a Sprint!",
            "id": new_id,
            "data": registro,
        }), 201

    except Exception as e:
        print(f"Erro ao processar atividades operacionais: {e}", file=sys.stderr)
        traceback.print_exc()
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return jsonify({"success": False, "error": str(e)}), 500


def _normalize_status_atividade(status):
    """Mapeia rótulos de UI (Feito, Concluído…) para o valor canônico do banco."""
    if status is None:
        return None
    key = str(status).strip().lower()
    if key in ('entregue', 'feito', 'concluído', 'concluido', 'concluída', 'concluida'):
        return 'Entregue'
    return str(status).strip()


def _recalcular_valor_atual_kr(conn, id_kr):
    """
    Recalcula valor_atual do KR com base na proporção de atividades Entregue.
    Espelha fn_recalcular_progresso_kr (contribuição igualitária por atividade).
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status_ativ = 'Entregue') AS concluidas
            FROM public.ctdi_okr_atividades
            WHERE id_kr = %s
            """,
            (id_kr,),
        )
        counts = cur.fetchone()
        cur.execute(
            "SELECT valor_inicial, valor_alvo FROM public.ctdi_okr_krs WHERE id_kr = %s",
            (id_kr,),
        )
        kr = cur.fetchone()
        if not kr:
            return None

        total = int(counts['total'] or 0)
        concluidas = int(counts['concluidas'] or 0)
        if total > 0:
            novo_atual = kr['valor_inicial'] + (
                (kr['valor_alvo'] - kr['valor_inicial']) * concluidas / total
            )
            status_kr = 'Atingido' if concluidas == total else 'Em Andamento'
        else:
            novo_atual = kr['valor_inicial']
            status_kr = 'Em Andamento'

        cur.execute(
            """
            UPDATE public.ctdi_okr_krs
            SET valor_atual = %s,
                status_kr = %s,
                data_revisao = CURRENT_TIMESTAMP
            WHERE id_kr = %s
            RETURNING valor_atual
            """,
            (novo_atual, status_kr, id_kr),
        )
        row = cur.fetchone()
        conn.commit()
        return row['valor_atual'] if row else novo_atual
    finally:
        cur.close()


def _put_atividade_sprint(conn, record_id, data):
    """Atualiza status/datas de uma atividade operacional e dispara rollup do KR."""
    data = dict(data or {})
    if not data:
        return jsonify({"success": False, "error": "Payload JSON vazio."}), 400

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT status_ativ, id_kr FROM public.ctdi_okr_atividades WHERE id_ativ = %s",
        (record_id,),
    )
    existing = cur.fetchone()
    cur.close()
    if not existing:
        return jsonify({"success": False, "error": "Atividade não encontrada."}), 404

    old_status = (existing.get('status_ativ') or '').strip()
    id_kr = existing['id_kr']
    update_data = dict(data)

    if update_data.get('id_kr'):
        cur_kr = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur_kr.execute(
            """
            SELECT dx_kr_id, COALESCE(ativo, true) AS ativo
            FROM public.ctdi_okr_krs WHERE id_kr = %s
            """,
            (int(update_data['id_kr']),),
        )
        kr_row = cur_kr.fetchone()
        cur_kr.close()
        if not kr_row:
            return jsonify({
                "success": False,
                "error": "Key Result selecionado não encontrado.",
            }), 400
        if not kr_row.get('ativo', True):
            return jsonify({
                "success": False,
                "error": "Este KR está suprimido.",
            }), 400
        update_data['dx_kr_id'] = int(kr_row['dx_kr_id']) if kr_row.get('dx_kr_id') else None

    if update_data.get('executor_id') or update_data.get('id_team'):
        executor_id = update_data.get('executor_id') or update_data.get('id_team')
        try:
            update_data['executor_id'] = int(executor_id)
            update_data['id_team'] = int(executor_id)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "executor_id inválido."}), 400

    cur_sync = conn.cursor()
    try:
        from rbac.notifications import rbac_sincronizar_executor_atividade
        update_data, _, _ = rbac_sincronizar_executor_atividade(
            cur_sync, update_data, id_ativ_existente=record_id
        )
    finally:
        cur_sync.close()

    if 'status_ativ' in update_data:
        update_data['status_ativ'] = _normalize_status_atividade(update_data['status_ativ'])

    new_status = update_data.get('status_ativ', old_status)
    if _normalize_status_atividade(new_status) == 'Entregue':
        update_data['status_ativ'] = 'Entregue'
        if not update_data.get('data_conclusao'):
            update_data['data_conclusao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    old_concluida = _normalize_status_atividade(old_status) == 'Entregue'
    new_concluida = update_data.get('status_ativ') == 'Entregue'
    recém_concluida = new_concluida and not old_concluida

    if not db_manager.update_record(conn, 'ctdi_okr_atividades', record_id, update_data):
        return jsonify({"success": False, "error": "Não foi possível atualizar a atividade."}), 500

    valor_atual_kr = None
    if recém_concluida or new_concluida:
        valor_atual_kr = _recalcular_valor_atual_kr(conn, id_kr)

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM public.ctdi_okr_atividades WHERE id_ativ = %s",
        (record_id,),
    )
    updated = cur.fetchone()
    cur.close()

    registro = db_manager.convert_record_to_json_safe(dict(updated)) if updated else {}
    return jsonify({
        "success": True,
        "message": "Evolução salva!",
        "kr_atualizado": recém_concluida,
        "valor_atual_kr": float(valor_atual_kr) if valor_atual_kr is not None else None,
        "data": registro,
    }), 200


@app.route('/api/okr/<string:entity_type>/<int:record_id>', methods=['PUT', 'DELETE'])
def handle_single_okr_entity(entity_type, record_id):
    """
    Endpoint dinâmico para Atualização (PUT) e Deleção (DELETE) do OKR.
    entity_type aceita: 'direcionadores', 'objetivos', 'krs' ou 'atividades'
    """
    table_map = {
        "direcionadores": "ctdi_okr_direcionadores",
        "objetivos": "ctdi_okr_objetivos_dt",
        "krs": "ctdi_okr_krs",
        "atividades": "ctdi_okr_atividades",
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
            if entity_type == 'atividades':
                return _put_atividade_sprint(conn, record_id, request.json)

            data = request.json
            if db_manager.update_record(conn, table_name, record_id, data):
                return jsonify({"success": True, "message": "Registro atualizado com sucesso!"}), 200
            return jsonify({"error": "Não foi possível atualizar o registro estratégico."}), 500

        elif request.method == 'DELETE':
            if entity_type == 'direcionadores':
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    "SELECT slug_catalogo FROM public.ctdi_okr_direcionadores WHERE id_direc = %s",
                    (record_id,),
                )
                row = cur.fetchone()
                cur.close()
                if row and row.get('slug_catalogo'):
                    return jsonify({
                        "error": "Direcionadores do catálogo PanelDX não podem ser removidos."
                    }), 403

            # KRs canônicos: soft-suppress (seed não recria). Custom: hard delete.
            if entity_type == 'krs':
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    "SELECT dx_kr_id FROM public.ctdi_okr_krs WHERE id_kr = %s",
                    (record_id,),
                )
                kr_row = cur.fetchone()
                cur.close()
                if kr_row and kr_row.get('dx_kr_id'):
                    from estrategia_matriz import atualizar_kr_cliente
                    if atualizar_kr_cliente(conn, record_id, ativo=False):
                        return jsonify({
                            "success": True,
                            "message": "KR canônico suprimido (pode ser reativado na matriz).",
                            "suprimido": True,
                        }), 200
                    return jsonify({"error": "Não foi possível suprimir o KR."}), 500

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
                              AND COALESCE(k.ativo, true) = true
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
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
    except ImportError:
        pass

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
        try:
            from ai_engine.worker_runtime import spawn_background_workers
            spawn_background_workers(base_path)
        except Exception as worker_err:
            print(f"⚠️  Falha ao iniciar workers em background: {worker_err}", file=sys.stderr)

    # 3. START DO SERVIDOR FLASK
    # host='0.0.0.0' é vital para o mapeamento de portas de entrada do Docker/AWS
    # FLASK_PORT=5002 no .env evita conflito com outros apps locais na 5000 (ex.: MAtivas)
    flask_port = int(os.environ.get("FLASK_PORT", 5002))
    use_reloader = os.environ.get('FLASK_USE_RELOADER', '0').lower() in ('1', 'true', 'yes')
    print(f"🚀 PanelDX Flask iniciando na porta {flask_port}... (reloader={'on' if use_reloader else 'off'})", file=sys.stderr)
    app.run(debug=True, port=flask_port, host='0.0.0.0', use_reloader=use_reloader)