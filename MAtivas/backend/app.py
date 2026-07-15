"""
MAtivas - Backend API
Plataforma web (Mesa de Inovação) baseada na obra
"Metodologias Inov(ativas) na Educação" de Andrea Filatro.

Persiste a jornada do professor de ponta a ponta (cadastro, desafio,
roteiro gerado e histórico de interações com a IA) em PostgreSQL.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

from dotenv import load_dotenv

# Carrega variáveis do backend/.env antes de qualquer leitura de os.environ.
_backend_dir = Path(__file__).resolve().parent
_project_root = _backend_dir.parent
load_dotenv(_backend_dir / ".env", override=False)

_path_candidates = [
    _backend_dir,
    _project_root,
    _backend_dir / "services",
    _project_root / "services",
]
for _path in _path_candidates:
    _path_str = str(_path.resolve())
    if Path(_path_str).exists() and _path_str not in sys.path:
        sys.path.insert(0, _path_str)

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from flask_cors import CORS

from diagnostico import buscar_base_conhecimento
from diagnostico_arvore import diagnosticar_com_arvore, refinar_diagnostico_com_dialogo
from routes.admin import admin_bp
from ui_content_service import carregar_conteudo_ui
from database.models import get_db_session
from email_service import send_roteiro_email
from botocore.exceptions import BotoCoreError, ClientError

# ---------------------------------------------------------------------
# Logging detalhado para depuração local
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mativas")

# ---------------------------------------------------------------------
# App + CORS (libera o frontend Vite em localhost:5173)
# ---------------------------------------------------------------------
app = Flask(__name__)
# Origens permitidas para CORS (separadas por vírgula). Em produção,
# defina CORS_ORIGINS=http://3.141.12.134 via variável de ambiente.
_cors_origins = [
    origem.strip()
    for origem in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origem.strip()
]
CORS(app, resources={r"/*": {"origins": _cors_origins}})
app.register_blueprint(admin_bp)

# ---------------------------------------------------------------------
# Configuração do banco de dados via variáveis de ambiente
# com fallback seguro para desenvolvimento local.
# ---------------------------------------------------------------------
# Captura prévia para a lógica de senha resiliente da AWS/Local
env_pass = os.environ.get("DB_PASSWORD") or os.environ.get("DB_PASS")

DB_CONFIG = {
    # Alvo alterado para o banco do ecossistema atual
    "dbname": os.environ.get("DB_NAME", "MAtivas"),

    # Tenta USER (padrão local) ou USERNAME (padrão AWS/Fargate)
    "user": os.environ.get("DB_USER") or os.environ.get("DB_USERNAME") or "postgres",

    # Se houver senha na AWS/Docker, usa ela; caso contrário, cai no fallback local
    "password": env_pass if env_pass else "Cmgv6190!@",

    # Se estiver na AWS e houver HOST, usa o IP da instância/RDS; padrão local 127.0.0.1
    "host": os.environ.get("DB_HOST", "127.0.0.1"),

    "port": int(os.environ.get("DB_PORT", 5432)),
    
    # Suporta o modo disable local ou o que for injetado na AWS (ex: require/verify-full)
    "sslmode": os.environ.get("DB_SSLMODE", "disable")
}


def get_connection():
    """Abre uma nova conexão com o PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)


# =====================================================================
# Rotas de verificação
# =====================================================================
@app.route("/")
def index():
    return jsonify(
        {
            "projeto": "MAtivas",
            "descricao": "Mesa de Inovação - Metodologias Inov(ativas) na Educação",
            "status": "ok",
        }
    )


@app.route("/health")
def health():
    """Verifica a aplicação e a conectividade com o banco."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        return jsonify({"status": "healthy", "db": "ok"}), 200
    except Exception as exc:
        logger.error("Health check falhou na conexão com o banco: %s", exc)
        return jsonify({"status": "degraded", "db": "erro", "detalhe": str(exc)}), 503


@app.route("/api/ui/conteudo", methods=["GET"])
def conteudo_ui_publico():
    """Textos, imagens e substituições de vocabulário para a interface."""
    session = get_db_session()
    try:
        return jsonify(carregar_conteudo_ui(session)), 200
    except Exception as exc:
        logger.exception("Falha ao carregar conteúdo da UI.")
        return jsonify({"erro": "Falha ao carregar conteúdo.", "detalhe": str(exc)}), 500
    finally:
        session.close()


# =====================================================================
# POST /api/diagnostico
# Diagnóstico por Árvore de Decisão (Claude via Bedrock):
# match_perfeito + alternativas do mesmo ramo + fusão estratégica.
# Fallback automático para matching por palavras-chave se a AWS falhar.
# Usado em /resultado.
# =====================================================================
@app.route("/api/diagnostico", methods=["POST"])
def diagnostico():
    data = request.get_json(silent=True) or {}
    desafio = (data.get("desafio") or "").strip()
    sintese = (data.get("sintese") or "").strip()
    opcoes = data.get("opcoes") or []
    nivel = data.get("nivel") or None
    formato = data.get("formato") or None

    opcoes_txt = ", ".join(opcoes) if isinstance(opcoes, list) else str(opcoes)
    texto = " ".join(p for p in (desafio, sintese, opcoes_txt) if p).strip()

    if not texto:
        return jsonify({"erro": "Informe o desafio ou ao menos uma opção."}), 400

    conn = None
    try:
        conn = get_connection()
        registros = buscar_base_conhecimento(conn)
        resultado = diagnosticar_com_arvore(
            texto, registros, nivel=nivel, formato=formato
        )
        match = (resultado.get("match_perfeito") or {}).get("nome")
        logger.info(
            "Diagnóstico árvore: match=%s fonte=%s",
            match or resultado.get("metodologia"),
            resultado.get("fonte"),
        )
        return jsonify(resultado), 200
    except Exception as exc:
        logger.exception("Falha no diagnóstico por árvore.")
        return jsonify({"erro": "Falha ao diagnosticar.", "detalhe": str(exc)}), 500
    finally:
        if conn:
            conn.close()


# =====================================================================
# POST /api/diagnostico/refinar
# Diálogo: professor indica o que não se adequa na abordagem escolhida
# e recebe novas sugestões, cada uma com justificativa.
# =====================================================================
@app.route("/api/diagnostico/refinar", methods=["POST"])
def diagnostico_refinar():
    data = request.get_json(silent=True) or {}
    desafio = (data.get("desafio") or "").strip()
    sintese = (data.get("sintese") or "").strip()
    opcoes = data.get("opcoes") or []
    nivel = data.get("nivel") or None
    formato = data.get("formato") or None
    abordagem_atual = (data.get("abordagem_atual") or data.get("metodologia") or "").strip()
    feedback = (data.get("feedback") or data.get("inadequacao") or "").strip()
    categoria_atual = (data.get("categoria_atual") or data.get("categoria") or "").strip() or None
    justificativa_atual = (data.get("justificativa_atual") or "").strip() or None

    opcoes_txt = ", ".join(opcoes) if isinstance(opcoes, list) else str(opcoes)
    texto = " ".join(p for p in (desafio, sintese, opcoes_txt) if p).strip()

    if not texto:
        return jsonify({"erro": "Informe o desafio original."}), 400
    if not abordagem_atual:
        return jsonify({"erro": "Selecione antes a abordagem em discussão."}), 400
    if len(feedback) < 8:
        return jsonify(
            {"erro": "Descreva com mais detalhes o que não se adequa à sua realidade."}
        ), 400

    conn = None
    try:
        conn = get_connection()
        registros = buscar_base_conhecimento(conn)
        resultado = refinar_diagnostico_com_dialogo(
            texto,
            registros,
            abordagem_atual=abordagem_atual,
            feedback=feedback,
            categoria_atual=categoria_atual,
            justificativa_atual=justificativa_atual,
            nivel=nivel,
            formato=formato,
        )
        logger.info(
            "Refino diálogo: %d sugestões (fonte=%s)",
            len(resultado.get("sugestoes") or []),
            resultado.get("fonte"),
        )
        return jsonify(resultado), 200
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:
        logger.exception("Falha no refino do diagnóstico.")
        return jsonify({"erro": "Falha ao refinar sugestões.", "detalhe": str(exc)}), 500
    finally:
        if conn:
            conn.close()


# =====================================================================
# POST /api/roteiro
# Enfileira o trabalho: persiste professor (upsert) + desafio + roteiro
# com status 'Pendente' (passos_json NULL). O processamento da IA é
# feito de forma assíncrona pelo worker (services/ai_worker.py).
# =====================================================================
@app.route("/api/roteiro", methods=["POST"])
def criar_roteiro():
    data = request.get_json(silent=True) or {}
    logger.info("POST /api/roteiro - payload recebido: %s", data)

    # --- Extração e normalização dos campos -------------------------
    nome = (data.get("nome") or "").strip()
    email = (data.get("email") or "").strip().lower()
    estado = (data.get("estado") or "").strip().upper()[:2] or None

    desafio_txt = (data.get("desafio") or "").strip()
    opcoes = data.get("opcoes") or []
    nivel = data.get("nivel") or None
    formato = data.get("formato") or None
    participantes = data.get("participantes")
    sintese = (data.get("sintese") or "").strip()
    # Metodologia/justificativa pré-selecionadas no diagnóstico (lock-in).
    metodologia_pre = (data.get("metodologia") or "").strip() or None
    justificativa_pre = (data.get("justificativa") or "").strip() or None

    if not email:
        return jsonify({"erro": "O campo 'email' é obrigatório."}), 400

    opcoes_txt = ", ".join(opcoes) if isinstance(opcoes, list) else str(opcoes)

    try:
        qtd_participantes = (
            int(participantes) if participantes not in (None, "") else None
        )
    except (ValueError, TypeError):
        qtd_participantes = None

    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # a) Upsert do professor pelo e-mail ----------------------
            cur.execute("SELECT id FROM professores WHERE email = %s", (email,))
            existente = cur.fetchone()

            if existente:
                professor_id = existente["id"]
                cur.execute(
                    "UPDATE professores SET nome = %s, estado = %s WHERE id = %s",
                    (nome, estado, professor_id),
                )
                logger.info("Professor existente atualizado (id=%s)", professor_id)
            else:
                cur.execute(
                    """INSERT INTO professores (nome, email, estado)
                       VALUES (%s, %s, %s) RETURNING id""",
                    (nome, email, estado),
                )
                professor_id = cur.fetchone()["id"]
                logger.info("Novo professor inserido (id=%s)", professor_id)

            # b) Evita enfileirar duplicatas em sequência (duplo clique / retry HTTP)
            cur.execute(
                """
                SELECT r.id
                  FROM roteiros r
                  JOIN desafios d ON d.id = r.desafio_id
                 WHERE d.professor_id = %s
                   AND d.conteudo_desafio = %s
                   AND COALESCE(d.opcoes_selecionadas, '') = %s
                   AND r.status IN ('Pendente', 'Processando')
                   AND r.data_geracao > CURRENT_TIMESTAMP - INTERVAL '2 minutes'
              ORDER BY r.id DESC
                 LIMIT 1
                """,
                (professor_id, desafio_txt, opcoes_txt),
            )
            roteiro_existente = cur.fetchone()
            if roteiro_existente:
                roteiro_id = roteiro_existente["id"]
                logger.info(
                    "Roteiro pendente recente reutilizado (id=%s) para evitar duplicata.",
                    roteiro_id,
                )
            else:
                # c) Insere o desafio
                cur.execute(
                    """INSERT INTO desafios
                           (professor_id, conteudo_desafio, opcoes_selecionadas,
                            nivel_ensino, formato_aula, qtd_participantes, sintese)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       RETURNING id""",
                    (professor_id, desafio_txt, opcoes_txt, nivel, formato,
                     qtd_participantes, sintese),
                )
                desafio_id = cur.fetchone()["id"]
                logger.info("Desafio inserido (id=%s)", desafio_id)

                # d) Enfileira o roteiro (Pendente, sem passos)
                cur.execute(
                    """INSERT INTO roteiros
                           (desafio_id, metodologia_recomendada, justificativa,
                            passos_json, status)
                       VALUES (%s, %s, %s, NULL, 'Pendente')
                       RETURNING id""",
                    (desafio_id, metodologia_pre, justificativa_pre),
                )
                roteiro_id = cur.fetchone()["id"]
                logger.info("Roteiro enfileirado (id=%s, status=Pendente)", roteiro_id)

        conn.commit()
        logger.info("Tarefa enfileirada com sucesso (roteiro_id=%s)", roteiro_id)

        return jsonify({"roteiroId": roteiro_id, "status": "Pendente"}), 202

    except Exception as exc:
        if conn:
            conn.rollback()
        logger.exception("Falha ao enfileirar roteiro. ROLLBACK executado.")
        return jsonify({"erro": "Falha ao enfileirar o roteiro.", "detalhe": str(exc)}), 500
    finally:
        if conn:
            conn.close()


# =====================================================================
# GET /api/roteiro/<id>/status
# Consulta o estado do processamento assíncrono e devolve os passos
# quando já estiver concluído (usado pelo polling do frontend).
# =====================================================================
@app.route("/api/roteiro/<int:id>/status", methods=["GET"])
def status_roteiro(id):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT id, status, metodologia_recomendada, justificativa, passos_json
                     FROM roteiros
                    WHERE id = %s""",
                (id,),
            )
            roteiro = cur.fetchone()

        if not roteiro:
            return jsonify({"erro": "Roteiro não encontrado."}), 404

        return (
            jsonify(
                {
                    "roteiroId": roteiro["id"],
                    "status": roteiro["status"],
                    "metodologia_recomendada": roteiro["metodologia_recomendada"],
                    "justificativa": roteiro["justificativa"],
                    "passos": roteiro["passos_json"],
                }
            ),
            200,
        )

    except Exception as exc:
        logger.exception("Falha ao consultar status do roteiro id=%s.", id)
        return jsonify({"erro": "Falha ao consultar status.", "detalhe": str(exc)}), 500
    finally:
        if conn:
            conn.close()


# =====================================================================
# POST /api/roteiro/<id>/feedback
# Atualiza a mensagem para a autora em um roteiro existente.
# =====================================================================
@app.route("/api/roteiro/<int:id>/feedback", methods=["POST"])
def feedback_roteiro(id):
    data = request.get_json(silent=True) or {}
    feedback = (data.get("feedback_autora") or data.get("feedback") or "").strip()
    logger.info("POST /api/roteiro/%s/feedback", id)

    if not feedback:
        return jsonify({"erro": "O campo 'feedback_autora' é obrigatório."}), 400

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE roteiros SET feedback_autora = %s WHERE id = %s",
                (feedback, id),
            )
            if cur.rowcount == 0:
                conn.rollback()
                logger.warning("Roteiro id=%s não encontrado para feedback.", id)
                return jsonify({"erro": "Roteiro não encontrado."}), 404

        conn.commit()
        logger.info("Feedback gravado no roteiro id=%s", id)
        return jsonify({"id": id, "feedback_autora": feedback}), 200

    except Exception as exc:
        if conn:
            conn.rollback()
        logger.exception("Falha ao gravar feedback. ROLLBACK executado.")
        return jsonify({"erro": "Falha ao gravar feedback.", "detalhe": str(exc)}), 500
    finally:
        if conn:
            conn.close()


def _buscar_roteiro_completo(project_id: int):
    """Carrega roteiro + professor + desafio. project_id = roteiros.id."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT r.id,
                       r.status,
                       r.metodologia_recomendada,
                       r.justificativa,
                       r.passos_json,
                       p.nome              AS professor_nome,
                       p.email             AS professor_email,
                       d.conteudo_desafio,
                       d.opcoes_selecionadas,
                       d.nivel_ensino,
                       d.formato_aula,
                       d.qtd_participantes,
                       d.sintese
                  FROM roteiros r
                  JOIN desafios d ON d.id = r.desafio_id
                  JOIN professores p ON p.id = d.professor_id
                 WHERE r.id = %s
                """,
                (project_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def _montar_contexto_desafio(row: dict) -> dict:
    desafio_txt = (row.get("conteudo_desafio") or "").strip()
    opcoes = (row.get("opcoes_selecionadas") or "").strip()
    if opcoes:
        desafio_txt = f"{desafio_txt} ({opcoes})".strip() if desafio_txt else opcoes
    if not desafio_txt and row.get("sintese"):
        desafio_txt = row["sintese"]

    return {
        "desafio": desafio_txt,
        "nivel": row.get("nivel_ensino"),
        "formato": row.get("formato_aula"),
        "participantes": row.get("qtd_participantes"),
    }


# =====================================================================
# POST /api/roteiro/enviar-email
# Envia o plano de aula/roteiro por Amazon SES.
# project_id corresponde ao id do roteiro (tabela roteiros).
# =====================================================================
@app.route("/api/roteiro/enviar-email", methods=["POST"])
def enviar_roteiro_email_rota():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    project_id_raw = data.get("project_id")

    if not email:
        return jsonify({"erro": "O campo 'email' é obrigatório."}), 400
    if project_id_raw is None or project_id_raw == "":
        return jsonify({"erro": "O campo 'project_id' é obrigatório."}), 400

    try:
        project_id = int(project_id_raw)
    except (TypeError, ValueError):
        return jsonify({"erro": "O campo 'project_id' deve ser um número inteiro."}), 400

    logger.info("POST /api/roteiro/enviar-email project_id=%s email=%s", project_id, email)

    try:
        row = _buscar_roteiro_completo(project_id)
    except Exception as exc:
        logger.exception("Falha ao buscar roteiro project_id=%s", project_id)
        return jsonify({"erro": "Falha ao consultar o roteiro.", "detalhe": str(exc)}), 500

    if not row:
        return jsonify({"erro": "Projeto/roteiro não encontrado.", "project_id": project_id}), 404

    if row.get("status") != "Concluido":
        return (
            jsonify(
                {
                    "erro": "O roteiro ainda não está concluído.",
                    "project_id": project_id,
                    "status": row.get("status"),
                }
            ),
            409,
        )

    passos = row.get("passos_json")
    if not passos:
        return (
            jsonify(
                {
                    "erro": "O roteiro não possui passos gerados para envio.",
                    "project_id": project_id,
                }
            ),
            409,
        )

    roteiro_content = {
        "nome": row.get("professor_nome"),
        "metodologia": row.get("metodologia_recomendada"),
        "justificativa": row.get("justificativa"),
        "passos": passos,
        "contexto": _montar_contexto_desafio(row),
    }

    try:
        resultado = send_roteiro_email(
            email, roteiro_content, project_id, modo="manual"
        )
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except ClientError as exc:
        codigo = exc.response.get("Error", {}).get("Code", "SES_ERROR")
        mensagem = exc.response.get("Error", {}).get("Message", str(exc))
        logger.error("SES rejeitou envio project_id=%s: %s — %s", project_id, codigo, mensagem)
        return (
            jsonify(
                {
                    "erro": "Falha ao enviar e-mail pelo Amazon SES.",
                    "codigo": codigo,
                    "detalhe": mensagem,
                }
            ),
            502,
        )
    except BotoCoreError as exc:
        logger.exception("Erro de conexão SES project_id=%s", project_id)
        return jsonify({"erro": "Falha de comunicação com o Amazon SES.", "detalhe": str(exc)}), 503

    if resultado.get("skipped"):
        return (
            jsonify(
                {
                    "sucesso": True,
                    "mensagem": "Este roteiro já foi enviado recentemente para este e-mail.",
                    "ignorado": True,
                    "motivo": resultado.get("motivo"),
                }
            ),
            200,
        )

    return (
        jsonify(
            {
                "sucesso": True,
                "mensagem": "Roteiro enviado por e-mail com sucesso.",
                "project_id": project_id,
                "email": resultado.get("destinatario"),
                "message_id": resultado.get("message_id"),
            }
        ),
        200,
    )


# =====================================================================
# PUT /api/professor/livro
# Atualiza a relação do professor com o livro e o opt-in do ecossistema.
# =====================================================================
@app.route("/api/professor/livro", methods=["PUT"])
def atualizar_professor_livro():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    status_livro = data.get("status_livro")
    opt_in = bool(data.get("opt_in_ecossistema", False))
    logger.info("PUT /api/professor/livro - email=%s", email)

    if not email:
        return jsonify({"erro": "O campo 'email' é obrigatório."}), 400

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE professores
                       SET status_livro = %s, opt_in_ecossistema = %s
                   WHERE email = %s""",
                (status_livro, opt_in, email),
            )
            if cur.rowcount == 0:
                conn.rollback()
                logger.warning("Professor com email=%s não encontrado.", email)
                return jsonify({"erro": "Professor não encontrado."}), 404

        conn.commit()
        logger.info("Relação com o livro atualizada para email=%s", email)
        return (
            jsonify(
                {
                    "email": email,
                    "status_livro": status_livro,
                    "opt_in_ecossistema": opt_in,
                }
            ),
            200,
        )

    except Exception as exc:
        if conn:
            conn.rollback()
        logger.exception("Falha ao atualizar professor. ROLLBACK executado.")
        return jsonify({"erro": "Falha ao atualizar cadastro.", "detalhe": str(exc)}), 500
    finally:
        if conn:
            conn.close()


def iniciar_worker_ia():
    """Dispara o worker de IA (services/ai_worker.py) de forma assíncrona.

    O worker fica um nível acima da pasta backend, em /services. Usamos
    subprocess.Popen repassando o ambiente atual para que ele herde as
    variáveis (credenciais AWS, configuração de banco, etc.).
    """
    base_path = os.path.dirname(os.path.abspath(__file__))
    worker_path = os.path.join(os.path.dirname(base_path), "services", "ai_worker.py")

    if not os.path.exists(worker_path):
        logger.warning("Worker de IA não encontrado em: %s", worker_path)
        return None

    logger.info("Despertando o worker de IA: %s", worker_path)
    processo = subprocess.Popen(
        [sys.executable, worker_path],
        env=os.environ.copy(),
    )
    logger.info("Worker de IA iniciado (PID=%s).", processo.pid)
    return processo


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    spawn_internal_workers = os.environ.get("SPAWN_INTERNAL_WORKERS", "1") == "1"

    # Valida a conectividade inicial com o banco antes de subir o app.
    try:
        _conn = get_connection()
        _conn.close()
        logger.info("Conectividade com o banco de dados validada com sucesso.")
    except Exception as exc:
        logger.error("Não foi possível conectar ao banco de dados: %s", exc)

    # O reloader do Flask em modo debug executa este bloco duas vezes.
    # Só disparamos o worker se a flag estiver ativa e no processo principal (evita duplicação).
    if spawn_internal_workers:
        if not debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            iniciar_worker_ia()

    logger.info("=" * 60)
    logger.info("  Ecossistema do MAtivas DESPERTADO com sucesso!")
    logger.info("  API Flask   -> http://0.0.0.0:%s", port)
    if spawn_internal_workers:
        logger.info("  Worker de IA -> services/ai_worker.py (em background)")
    else:
        logger.info("  Worker de IA -> Desativado (Rodando como serviço isolado)")
    logger.info("=" * 60)

    app.run(host="0.0.0.0", port=port, debug=debug)
