from flask import Blueprint, request, jsonify, render_template, redirect, session
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import json
import re
import sys
import boto3
import os
from datetime import datetime, date
from botocore.config import Config

from sprint_governance import (
    STAT_EM_ANALISE,
    STAT_PLANEJADA_BACKLOG,
    STAT_EM_ANDAMENTO,
    STAT_CONCLUIDA,
    canonicalizar_status_dnd,
    status_em_analise,
)
from sprint_squad import (
    atualizar_nome_squad_pos_sprint,
    criar_squad_vazia_para_sprint,
    format_nome_squad,
    resolver_ou_criar_projeto_cliente,
)

# 🎯 Sobe dois níveis e encontra a pasta real do Frontend no Windows
views_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'LeAction_Sys_FE', 'views'))

inovador_bp = Blueprint(
    'inovador',
    __name__,
    template_folder=views_path
)

# Modelo Bedrock central (o Claude 3.5 Sonnet 20240620 foi descontinuado).
# Mesmo inference profile dos workers; sobrescrevível por env.
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")


def _bedrock_ssl_verify_enabled():
    return os.environ.get("BEDROCK_SSL_VERIFY", "1").strip().lower() not in ("0", "false", "no")


def _get_bedrock_runtime_client():
    verify = _bedrock_ssl_verify_enabled()
    if not verify:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=BEDROCK_REGION,
        verify=verify,
        config=Config(connect_timeout=8, read_timeout=45, retries={"max_attempts": 1}),
    )


def _extrair_json_resposta_mesa(texto):
    if texto is None:
        raise ValueError("Resposta vazia do modelo.")
    limpo = texto.strip()
    cerca = re.match(r"^```(?:json)?\s*(.*?)\s*```$", limpo, re.DOTALL | re.IGNORECASE)
    if cerca:
        limpo = cerca.group(1).strip()
    try:
        return json.loads(limpo)
    except json.JSONDecodeError:
        inicio = limpo.find("{")
        fim = limpo.rfind("}")
        if inicio != -1 and fim != -1 and fim > inicio:
            return json.loads(limpo[inicio:fim + 1])
        raise


def _fallback_rascunho_mesa_organizacional(gap_context, notas_texto, direcionador):
    gap = gap_context or {}
    direc = direcionador or {}
    nome_direc = (direc.get("nome") or "Direcionador Estratégico").strip()
    nome_gap = (gap.get("nome") or "Lacuna prioritária de maturidade").strip()
    dominio = (gap.get("dominio") or "Organização").strip()
    gap_val = gap.get("gap", "—")
    contexto_nota = ""
    if notas_texto:
        contexto_nota = " ".join(str(n).strip() for n in notas_texto if n).strip()[:280]
    return {
        "nome_acao": f"Iniciativa alinhada a {nome_direc}"[:90],
        "justificativa_pedagogica": (
            f"A lacuna Δ {gap_val} no domínio {dominio} limita a execução da transformação digital. "
            f"A iniciativa está ancorada no direcionador «{nome_direc}». "
            f"{contexto_nota or 'Prioridade derivada do Relatório de Maturidade CTDI.'}"
        ),
        "impacto_negocio": (
            f"Maturidade digital e resultados vinculados ao direcionador «{nome_direc}» em {dominio}."
        ),
        "hipotese_estrategica": (
            f"Se executarmos ações alinhadas a {nome_direc} para tratar {nome_gap}, "
            f"reduziremos a lacuna em até 90 dias."
        ),
        "pilares": {
            "contencao": (
                f"Estancar o agravamento da lacuna em {nome_gap}, sob a diretriz {nome_direc}."
            ),
            "implementacao": (
                f"Executar plano tático com responsáveis e marcos semanais, fiel ao direcionador {nome_direc}."
            ),
            "prevencao": "Instituir ritos de governança e indicadores para evitar recorrência da lacuna.",
            "sustentacao": "Monitorar métricas de maturidade e retroalimentar o framework CTDI mensalmente.",
        },
    }


def get_db_connection():
    # Lazy import para quebrar a dependência circular com o app.py
    from app import DB_CONFIG
    return psycopg2.connect(**DB_CONFIG)


def limpar_objeto(obj):
    """Auxiliar para converter objetos datetime/date do Postgres em strings aceitas pelo jsonify"""
    if isinstance(obj, list):
        return [limpar_objeto(item) for item in obj]
    if isinstance(obj, dict):
        return {k: limpar_objeto(v) for k, v in obj.items()}
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj


# =========================================================================
# 🧭 NAVEGAÇÃO / VIEWS EJS (CONSUMO DINÂMICO INTEGRADO WITH EXPRESS)
# =========================================================================

@inovador_bp.route('/', methods=['GET'])
def dashboard_inovador():
    """Renderiza a view principal absorvendo o cliente vindo do barramento Node.js"""
    token = request.args.get('token')

    # 🎯 1. Captura o id_clie despachado pelo Node.js na URL (?id_clie=VALOR)
    id_clie_param = request.args.get('id_clie')

    if id_clie_param:
        # Se veio na URL, salva na sessão do Flask para fixar o contexto do usuário
        session['id_clie'] = int(id_clie_param)

    # 2. Recupera da sessão ou adota o 999 se estiver acessando de forma avulsa
    id_clie = session.get('id_clie')
    if not id_clie:
        id_clie = 999

    # 🛡️ BLINDAGEM DE SANDBOX: Garante a existência do cliente 999 na tabela pai (ctdi_clie)
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
                       INSERT INTO public.ctdi_clie (id_clie, docu_clie, nome_clie, mail_clie, has_active_project)
                       VALUES (999, '00000000000', 'Mestre de Testes Sandbox 999', 'sandbox999@leaction.com.br', false)
                       ON CONFLICT (id_clie) DO NOTHING;
                       """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Alerta: Não foi possível auto-injetar o cliente 999 ({e}). Buscando alternativa real...")

        # CONTINGÊNCIA: Se o banco rejeitar o 999, pegamos o primeiro cliente real da sua base
        try:
            cursor.execute("SELECT id_clie FROM public.ctdi_clie LIMIT 1;")
            cliente_existente = cursor.fetchone()
            if cliente_existente:
                id_clie = cliente_existente['id_clie']
                print(f"🔄 Sandbox redirecionado para o cliente real de ID: {id_clie}")
        except Exception as inner_e:
            print(f"❌ Erro crítico ao buscar cliente alternativo: {inner_e}")
    finally:
        cursor.close()
        conn.close()

    return render_template('inovador_dashboard.ejs', token=token, id_clie=id_clie)


@inovador_bp.route('/inovador/logout', methods=['GET', 'POST'])
@inovador_bp.route('/logout', methods=['GET', 'POST'])
def logout_inovador_local():
    """Limpa a sessão do Flask e redireciona diretamente para o PanelDX na porta 3000"""
    session.clear()
    return redirect('http://localhost:3000/logout')


# =========================================================================
# 📅 FRENTE 1: AGENDA, ROTINAS & POST-ITS (CRUD COMPLETO COM ROTAS DUPLAS)
# =========================================================================

@inovador_bp.route('/inovador/api/rotinas', methods=['GET'])
@inovador_bp.route('/api/rotinas', methods=['GET'])
def listar_rotinas():
    id_clie = request.args.get('id_clie')
    if not id_clie:
        return jsonify({"status": "error", "message": "id_clie é obrigatório"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = "SELECT id_rotina, id_clie, titulo_atividade, data_atividade FROM public.inov_agenda_rotina WHERE id_clie = %s ORDER BY id_rotina DESC;"
        cursor.execute(query, (id_clie,))
        rotinas = cursor.fetchall()
        return jsonify({"status": "success", "data": limpar_objeto(rotinas)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/rotinas', methods=['POST'])
@inovador_bp.route('/api/rotinas', methods=['POST'])
def criar_rotina():
    data = request.json or {}
    id_clie = data.get('id_clie')
    titulo = data.get('titulo_atividade')

    if not id_clie or not titulo:
        return jsonify({"status": "error", "message": "id_clie e titulo_atividade são obrigatórios"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = "INSERT INTO public.inov_agenda_rotina (id_clie, titulo_atividade) VALUES (%s, %s) RETURNING *;"
        cursor.execute(query, (id_clie, titulo))
        nova_rotina = cursor.fetchone()
        conn.commit()
        return jsonify({"status": "success", "data": limpar_objeto(nova_rotina)}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/rotinas', methods=['PUT'])
@inovador_bp.route('/api/rotinas', methods=['PUT'])
def atualizar_rotina():
    data = request.json or {}
    id_rotina = data.get('id_rotina')
    novo_titulo = data.get('titulo_atividade')

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("UPDATE public.inov_agenda_rotina SET titulo_atividade = %s WHERE id_rotina = %s RETURNING *;",
                       (novo_titulo, id_rotina))
        atualizado = cursor.fetchone()
        conn.commit()
        return jsonify({"status": "success", "data": limpar_objeto(atualizado)}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/rotinas', methods=['DELETE'])
@inovador_bp.route('/api/rotinas', methods=['DELETE'])
def deletar_rotina():
    id_rotina = request.args.get('id_rotina')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM public.inov_agenda_notas WHERE id_rotina = %s AND status_nota = 'Pendente';",
                       (id_rotina,))
        cursor.execute("DELETE FROM public.inov_agenda_rotina WHERE id_rotina = %s;", (id_rotina,))
        conn.commit()
        return jsonify({"status": "success", "message": "Rotina eliminada."}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/notas', methods=['GET'])
@inovador_bp.route('/api/notas', methods=['GET'])
def listar_notas():
    id_clie = request.args.get('id_clie')
    if not id_clie:
        return jsonify({"status": "error", "message": "id_clie é obrigatório"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = """
                SELECT n.id_nota, \
                       n.id_clie, \
                       n.id_rotina, \
                       n.conteudo_bruto, \
                       n.tipo_observacao, \
                       n.status_nota,
                       r.titulo_atividade as aula_contexto
                FROM public.inov_agenda_notas n
                         LEFT JOIN public.inov_agenda_rotina r ON n.id_rotina = r.id_rotina
                WHERE n.id_clie = %s \
                ORDER BY n.id_nota DESC; \
                """
        cursor.execute(query, (id_clie,))
        return jsonify({"status": "success", "data": limpar_objeto(cursor.fetchall())}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/notas', methods=['POST'])
@inovador_bp.route('/api/notas', methods=['POST'])
def criar_nota():
    data = request.json or {}
    id_clie = data.get('id_clie')
    id_rotina = data.get('id_rotina')
    conteudo = data.get('conteudo_bruto')

    conteudo_lower = conteudo.lower()
    tipo_obs = 'Gargalo_Digital'
    if any(w in conteudo_lower for w in
           ['aluno', 'turma', 'atenção', 'disperso', 'sala', 'conversando', 'comportamento']):
        tipo_obs = 'Comportamento_Aluno'
    elif any(w in conteudo_lower for w in
             ['ideia', 'criar', 'aplicar', 'projeto', 'insight', 'metodologia', 'dinâmica']):
        tipo_obs = 'Insight_Pedagogico'

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = "INSERT INTO public.inov_agenda_notas (id_clie, id_rotina, conteudo_bruto, tipo_observacao, status_nota) VALUES (%s, %s, %s, %s, 'Pendente') RETURNING *;"
        cursor.execute(query, (id_clie, id_rotina, conteudo, tipo_obs))
        nova_nota = cursor.fetchone()
        conn.commit()
        return jsonify({"status": "success", "data": limpar_objeto(nova_nota)}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/notas', methods=['PUT'])
@inovador_bp.route('/api/notas', methods=['PUT'])
def atualizar_nota():
    data = request.json or {}
    id_nota = data.get('id_nota')
    novo_conteudo = data.get('conteudo_bruto')

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            "UPDATE public.inov_agenda_notas SET conteudo_bruto = %s WHERE id_nota = %s AND status_nota = 'Pendente' RETURNING *;",
            (novo_conteudo, id_nota))
        atualizado = cursor.fetchone()
        conn.commit()
        return jsonify({"status": "success", "data": limpar_objeto(atualizado)}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/notas', methods=['DELETE'])
@inovador_bp.route('/api/notas', methods=['DELETE'])
def deletar_nota():
    id_nota = request.args.get('id_nota')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM public.inov_agenda_notas WHERE id_nota = %s AND status_nota = 'Pendente';",
                       (id_nota,))
        conn.commit()
        return jsonify({"status": "success", "message": "Post-it removido."}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


def _mesa_org_rotina_titulo(id_matu):
    return f"Mesa Org · Matu #{id_matu}"


def _mesa_org_serializar_nota(row):
    if not row:
        return None
    conteudo_raw = row.get("conteudo_bruto") or ""
    contexto = row.get("tipo_observacao") or "Ideação livre"
    origem_gap = None
    origem = "mesa_org"
    is_alerta = False
    hipotese_negocio = None
    subtasks = None
    status_anomalia = None
    dominio_associado = None
    bloco_associado = None
    codigo_evento_padrao = None
    dimensao_fixada = None
    id_item_backlog = None
    texto = conteudo_raw
    try:
        parsed = json.loads(conteudo_raw)
        if isinstance(parsed, dict) and parsed.get("v") == 1:
            texto = parsed.get("texto") or ""
            contexto = parsed.get("contexto") or contexto
            origem_gap = parsed.get("origem_gap")
            meta = parsed.get("meta") or {}
            if meta.get("origem"):
                origem = meta.get("origem")
            if meta.get("is_alerta"):
                is_alerta = True
            hipotese_negocio = meta.get("hipotese_negocio")
            subtasks = meta.get("subtasks")
            status_anomalia = meta.get("status_anomalia")
            dominio_associado = meta.get("dominio_associado")
            bloco_associado = meta.get("bloco_associado")
            codigo_evento_padrao = meta.get("codigo_evento_padrao")
            dimensao_fixada = meta.get("dimensao_fixada")
            id_item_backlog = meta.get("id_item_backlog")
    except (TypeError, json.JSONDecodeError):
        pass
    if row.get("tipo_observacao") == "Telemetria_BaseMobile":
        origem = "telemetria"
        is_alerta = True
    if origem == "telemetria" and not hipotese_negocio and texto:
        match = re.match(
            r"\[ALERTA TELEMETRIA[^\]]*\]\s*(.+?)(?:\n\nDomínio:|\Z)",
            texto,
            re.DOTALL,
        )
        if match:
            hipotese_negocio = match.group(1).strip()
    return {
        "id_nota": row.get("id_nota"),
        "conteudo": texto,
        "contexto": contexto,
        "status": row.get("status_nota") or "Pendente",
        "origem_gap": origem_gap,
        "origem": origem,
        "is_alerta": is_alerta,
        "hipotese_negocio": hipotese_negocio,
        "subtasks": subtasks or [],
        "status_anomalia": status_anomalia,
        "dominio_associado": dominio_associado,
        "bloco_associado": bloco_associado,
        "codigo_evento_padrao": codigo_evento_padrao,
        "dimensao_fixada": dimensao_fixada,
        "id_item_backlog": id_item_backlog,
        "created_at": row.get("created_at"),
    }


def _mesa_org_get_or_create_rotina(cursor, id_clie, id_matu):
    titulo = _mesa_org_rotina_titulo(id_matu)
    cursor.execute(
        "SELECT id_rotina FROM public.inov_agenda_rotina WHERE id_clie = %s AND titulo_atividade = %s LIMIT 1;",
        (id_clie, titulo),
    )
    row = cursor.fetchone()
    if row:
        return row["id_rotina"]
    cursor.execute(
        "INSERT INTO public.inov_agenda_rotina (id_clie, titulo_atividade) VALUES (%s, %s) RETURNING id_rotina;",
        (id_clie, titulo),
    )
    return cursor.fetchone()["id_rotina"]


def _mesa_org_status_rotulo(notas_pendentes: int, alertas_esim: int, status_ia: str | None, has_active: bool) -> str:
    if (notas_pendentes or 0) > 0 or (alertas_esim or 0) > 0:
        return "ativa"
    status = (status_ia or "").strip().upper()
    if has_active or status == "AVALIACAO OK" or "CONCLU" in status:
        return "disponivel"
    return "em_setup"


@inovador_bp.route('/inovador/api/admin/mesas-inovacao', methods=['GET'])
@inovador_bp.route('/api/admin/mesas-inovacao', methods=['GET'])
def listar_mesas_inovacao_admin():
    """Lista mesas organizacionais ativas — uma linha por cliente (matu mais recente)."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            """
            WITH latest_matu AS (
                SELECT DISTINCT ON (m.id_clie)
                    m.id_matu,
                    m.id_clie,
                    m.status_ia
                FROM public.ctdi_matu m
                ORDER BY m.id_clie, m.id_matu DESC
            ),
            mesa_stats AS (
                SELECT
                    n.id_clie,
                    COUNT(*) FILTER (
                        WHERE n.status_nota = 'Pendente'
                          AND n.tipo_observacao IN (
                              'Mesa_Organizacional', 'Telemetria_eSIM', 'Telemetria_BaseMobile'
                          )
                    ) AS notas_pendentes,
                    COUNT(*) AS notas_total,
                    MAX(n.created_at) AS ultima_nota_em
                FROM public.inov_agenda_notas n
                GROUP BY n.id_clie
            ),
            esim_stats AS (
                SELECT id_clie, COUNT(*) AS alertas_pendentes
                FROM public.esim_mesa_backlog
                WHERE status = 'pendente'
                GROUP BY id_clie
            )
            SELECT
                lm.id_matu,
                lm.id_clie,
                c.nome_clie,
                c.mail_clie,
                COALESCE(c.has_active_project, false) AS has_active_project,
                lm.status_ia,
                COALESCE(ms.notas_pendentes, 0) AS notas_pendentes,
                COALESCE(ms.notas_total, 0) AS notas_total,
                COALESCE(es.alertas_pendentes, 0) AS alertas_esim,
                ms.ultima_nota_em,
                r.id_rotina AS id_rotina_mesa
            FROM latest_matu lm
            JOIN public.ctdi_clie c ON c.id_clie = lm.id_clie
            LEFT JOIN mesa_stats ms ON ms.id_clie = lm.id_clie
            LEFT JOIN esim_stats es ON es.id_clie = lm.id_clie
            LEFT JOIN public.inov_agenda_rotina r
                ON r.id_clie = lm.id_clie
               AND r.titulo_atividade = CONCAT('Mesa Org · Matu #', lm.id_matu::text)
            WHERE NOT (
                COALESCE(UPPER(TRIM(lm.status_ia)), 'AGUARDANDO CONTEXTO') = 'AGUARDANDO CONTEXTO'
                AND COALESCE(ms.notas_total, 0) = 0
                AND COALESCE(es.alertas_pendentes, 0) = 0
                AND r.id_rotina IS NULL
            )
            ORDER BY
                (COALESCE(ms.notas_pendentes, 0) + COALESCE(es.alertas_pendentes, 0)) DESC,
                c.nome_clie ASC;
            """
        )
        rows = []
        for row in cursor.fetchall():
            item = dict(row)
            item["status_mesa"] = _mesa_org_status_rotulo(
                item.get("notas_pendentes"),
                item.get("alertas_esim"),
                item.get("status_ia"),
                bool(item.get("has_active_project")),
            )
            if item.get("ultima_nota_em"):
                item["ultima_nota_em"] = item["ultima_nota_em"].isoformat()
            rows.append(limpar_objeto(item))
        return jsonify({"status": "success", "data": rows}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/mesa-org/notas', methods=['GET'])
@inovador_bp.route('/api/mesa-org/notas', methods=['GET'])
def listar_notas_mesa_org():
    id_clie = request.args.get('id_clie')
    id_matu = request.args.get('id_matu')
    if not id_clie or not id_matu:
        return jsonify({"status": "error", "message": "id_clie e id_matu são obrigatórios"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        id_rotina = _mesa_org_get_or_create_rotina(cursor, id_clie, id_matu)
        conn.commit()
        cursor.execute(
            """
            SELECT id_nota, conteudo_bruto, tipo_observacao, status_nota, created_at
            FROM public.inov_agenda_notas
            WHERE id_clie = %s AND id_rotina = %s
            ORDER BY id_nota ASC;
            """,
            (id_clie, id_rotina),
        )
        notas = [_mesa_org_serializar_nota(r) for r in cursor.fetchall()]
        return jsonify({"status": "success", "data": limpar_objeto(notas)}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/mesa-org/notas', methods=['POST'])
@inovador_bp.route('/api/mesa-org/notas', methods=['POST'])
def criar_nota_mesa_org():
    data = request.json or {}
    id_clie = data.get('id_clie')
    id_matu = data.get('id_matu')
    conteudo = (data.get('conteudo') or '').strip()
    contexto = (data.get('contexto') or 'Ideação livre').strip()
    origem_gap = data.get('origem_gap')

    if not id_clie or not id_matu or not conteudo:
        return jsonify({"status": "error", "message": "id_clie, id_matu e conteudo são obrigatórios"}), 400

    payload_json = json.dumps({
        "v": 1,
        "texto": conteudo,
        "contexto": contexto,
        "origem_gap": origem_gap,
    }, ensure_ascii=False)

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        id_rotina = _mesa_org_get_or_create_rotina(cursor, id_clie, id_matu)
        cursor.execute(
            """
            INSERT INTO public.inov_agenda_notas
                (id_clie, id_rotina, conteudo_bruto, tipo_observacao, status_nota)
            VALUES (%s, %s, %s, %s, 'Pendente')
            RETURNING id_nota, conteudo_bruto, tipo_observacao, status_nota, created_at;
            """,
            (id_clie, id_rotina, payload_json, 'Mesa_Organizacional'),
        )
        nova = cursor.fetchone()
        conn.commit()
        return jsonify({"status": "success", "data": limpar_objeto(_mesa_org_serializar_nota(nova))}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/mesa-org/notas', methods=['DELETE'])
@inovador_bp.route('/api/mesa-org/notas', methods=['DELETE'])
def deletar_nota_mesa_org():
    id_nota = request.args.get('id_nota')
    if not id_nota:
        return jsonify({"status": "error", "message": "id_nota é obrigatório"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            DELETE FROM public.inov_agenda_notas
            WHERE id_nota = %s AND status_nota = 'Pendente' AND tipo_observacao = 'Mesa_Organizacional';
            """,
            (id_nota,),
        )
        conn.commit()
        return jsonify({"status": "success", "message": "Post-it removido."}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/mesa-org/notas/incubar', methods=['POST'])
@inovador_bp.route('/api/mesa-org/notas/incubar', methods=['POST'])
def incubar_notas_mesa_org():
    data = request.json or {}
    ids_notas = data.get('ids_notas') or []
    if not ids_notas:
        return jsonify({"status": "error", "message": "ids_notas é obrigatório"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE public.inov_agenda_notas
            SET status_nota = 'Incubada'
            WHERE id_nota = ANY(%s)
              AND tipo_observacao IN ('Mesa_Organizacional', 'Telemetria_BaseMobile')
              AND status_nota = 'Pendente';
            """,
            (ids_notas,),
        )
        try:
            from integrations.esim.repository import esim_marcar_backlog_consumido_por_notas as marcar_backlog_consumido_por_notas

            marcar_backlog_consumido_por_notas(cursor, [int(i) for i in ids_notas if str(i).isdigit()])
        except Exception as backlog_err:
            print(f"⚠️ [BaseMobile] Falha ao consumir backlog na incubação: {backlog_err}", file=sys.stderr)
        conn.commit()
        return jsonify({"status": "success", "message": "Post-its incubados."}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# =========================================================================
# 🚀 FRENTE 2: AÇÃO (MESA DE LAPIDAÇÃO CO-AUTORA ANTI-REPETIÇÃO)
# =========================================================================

@inovador_bp.route('/inovador/api/acoes', methods=['GET'])
@inovador_bp.route('/api/acoes', methods=['GET'])
def obtener_acao_por_nota():
    id_nota = request.args.get('id_nota')
    if not id_nota: return jsonify({"status": "error", "message": "id_nota é obrigatório"}), 400
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Removido o a.subtask do SELECT
        query = """
                SELECT a.id_acao, a.bloco_leaction, a.nome_acao, a.justificativa_pedagogica,
                       a.impacto_negocio, a.composicao_estruturada, a.id_prob, 
                       a.rotas_metodologicas,
                       (SELECT json_agg(json_build_object('pilar_subtask', s.pilar_subtask, 'desc_subtask', s.desc_subtask)) 
                        FROM public.inov_subtasks s WHERE s.id_acao = a.id_acao) as subtasks_list,
                       p.grupo_prob, p.categoria_prob, p.desc_prob, p.razoes_prob, p.solucoes_prob,
                       (SELECT STRING_AGG(v.id_matu::text, ', ') FROM public.inov_acoes_escolas_vinculo v WHERE v.id_acao = a.id_acao) as codigos_escolas_ref
                FROM public.inov_acoes a
                         JOIN public.inov_acao_notas_mapping m ON a.id_acao = m.id_acao
                         LEFT JOIN public.ctdi_problemas_referencia p ON a.id_prob = p.id_prob
                WHERE m.id_nota = %s LIMIT 1;
                """
        cursor.execute(query, (id_nota,))
        res = cursor.fetchone()
        return jsonify({"status": "success", "data": limpar_objeto(res) if res else None}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/acoes/gerar-preview', methods=['POST'])
@inovador_bp.route('/api/acoes/gerar-preview', methods=['POST'])
def gerar_preview_ia():
    data = request.json or {}
    tipo_mesa = (data.get('tipo_mesa') or 'pedagogica').strip().lower()
    bloco = data.get('bloco_leaction')
    ids_notas = data.get('ids_notas', [])
    id_prob_cmu = data.get('id_prob_cmu')
    notas_texto = data.get('notas_texto', [])
    gap_context = data.get('gap_context') or {}
    gaps_maturidade = data.get('gaps_maturidade') or []
    direcionador = data.get('direcionador_estrategico') or {}
    id_direc = data.get('id_direc') or direcionador.get('id_direc')

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    contexto_cmu = ""
    contexto_dores = ""
    try:
        if tipo_mesa == 'organizacional':
            # Mesa de Inovação Organizacional — sem referencial pedagógico CMU
            linhas_gap = []
            if gap_context:
                linhas_gap.append(
                    f"- GAP PRIORITÁRIO: {gap_context.get('nome', '')} "
                    f"(Domínio: {gap_context.get('dominio', '')}, Lacuna Δ: {gap_context.get('gap', '')})"
                )
                if gap_context.get('desc'):
                    linhas_gap.append(f"  Descrição: {gap_context.get('desc')}")
            for g in gaps_maturidade[:5]:
                linhas_gap.append(
                    f"- {g.get('nome', 'Bloco')}: lacuna {g.get('gap', '')} · {g.get('dominio', '')}"
                )
            contexto_gaps = "\n".join(linhas_gap) if linhas_gap else "Sem gaps detalhados."
            contexto_dores = "\n".join([f"- {n}" for n in notas_texto if n])
            if not direcionador.get('nome') and id_direc:
                try:
                    cursor.execute(
                        "SELECT nome_direc, desc_direc, slug_catalogo FROM public.ctdi_okr_direcionadores WHERE id_direc = %s;",
                        (int(id_direc),) if str(id_direc).isdigit() else (id_direc,)
                    )
                    row_direc = cursor.fetchone()
                    if row_direc:
                        direcionador = {
                            "id_direc": id_direc,
                            "nome": row_direc.get("nome_direc"),
                            "desc": row_direc.get("desc_direc") or "",
                            "slug": row_direc.get("slug_catalogo") or "",
                        }
                except (TypeError, ValueError):
                    pass

            contexto_direc = ""
            if direcionador:
                contexto_direc = f"""
        DIRECIONADOR ESTRATÉGICO OBRIGATÓRIO (toda a inovação deve servir a esta diretriz):
        - Nome: {direcionador.get('nome', '')}
        - Descrição: {direcionador.get('desc', '')}
        - Slug: {direcionador.get('slug', '')}
        """
            if not contexto_dores.strip() and ids_notas:
                cursor.execute(
                    "SELECT conteudo_bruto FROM public.inov_agenda_notas WHERE id_nota = ANY(%s);",
                    (ids_notas,)
                )
                notas_recuperadas = cursor.fetchall()
                contexto_dores = "\n".join([f"- {n['conteudo_bruto']}" for n in notas_recuperadas])

            # TODO: Ajustar System Prompt do Consultor LeAction para contexto organizacional completo.
            system_prompt = f"""
        Você é o Consultor LeAction — arquiteto de transformação organizacional sênior,
        especialista no Framework de Maturidade CTDI (PanelDX).
        Sua missão é transformar lacunas de maturidade digital em uma iniciativa executiva concreta,
        estritamente alinhada ao DIRECIONADOR ESTRATÉGICO escolhido pelo gestor.

        REGRAS INEGOCIÁVEIS:
        1. IDIOMA: Escreva EXCLUSIVAMENTE em Português do Brasil (pt-BR), com linguagem executiva e estratégica.
        2. DIRECIONADOR: Toda proposta deve servir ao direcionador estratégico indicado — é a bússola da inovação.
        3. CONTEXTO: Baseie-se nos gaps de maturidade e nas notas de ideação. Proibido contexto pedagógico de sala de aula.
        4. BLOCO CTDI: NÃO selecione nem invente bloco metodológico aqui — o acoplamento ocorre no Kanban (Planejar Sprint).
        5. ESTRUTURA OBRIGATÓRIA — exatamente 4 PILARES fixos:
           - "contencao": Contenção imediata do risco ou lacuna organizacional.
           - "implementacao": Implementação da solução no contexto da organização.
           - "prevencao": Prevenção de recorrência da lacuna.
           - "sustentacao": Sustentação e métricas de sucesso ao longo do tempo.

        {contexto_direc}

        GAPS DE MATURIDADE (Top prioritários):
        {contexto_gaps}

        Retorne ESTRITAMENTE um JSON limpo (sem markdown), nesta forma exata:
        {{
            "nome_acao": "Título curto e executivo focado na lacuna e no direcionador",
            "justificativa_pedagogica": "Análise estratégica alinhada ao direcionador e ao framework de maturidade",
            "impacto_negocio": "Métrica financeira, operacional ou de maturidade diretamente afetada",
            "hipotese_estrategica": "Hipótese testável no formato Se X então Y em Z semanas",
            "pilares": {{
                "contencao": "Descrição prática da contenção",
                "implementacao": "Descrição prática da implementação",
                "prevencao": "Descrição prática da prevenção",
                "sustentacao": "Descrição prática da sustentação"
            }}
        }}
        """
            user_content = (
                f"NOTAS DE IDEAÇÃO ORGANIZACIONAL:\n{contexto_dores}"
            )
        else:
            if id_prob_cmu:
                cursor.execute("""
                               SELECT grupo_prob, categoria_prob, desc_prob, razoes_prob, solucoes_prob
                               FROM public.ctdi_problemas_referencia
                               WHERE id_prob = %s;
                               """, (id_prob_cmu,))
                cmu = cursor.fetchone()
                if cmu:
                    contexto_cmu = f"""
                    [REFERENCIAL CIENTÍFICO CMU SELECCIONADO]:
                    - Grupo/Categoria: {cmu['grupo_prob']} / {cmu['categoria_prob']}
                    - Sintoma Mapeado: {cmu['desc_prob']}
                    - Causa Provável (Razão): {cmu['razoes_prob']}
                    - Estratégia de Contenção Recomendada: {cmu['solucoes_prob']}
                    """

            cursor.execute("SELECT conteudo_bruto FROM public.inov_agenda_notas WHERE id_nota = ANY(%s);", (ids_notas,))
            notas_recuperadas = cursor.fetchall()
            contexto_dores = "\n".join([f"- {n['conteudo_bruto']}" for n in notas_recuperadas])

            system_prompt = f"""
        Você é um Designer Instrucional Sênior especialista na metodologia educacional LeActionF.
        Sua missão é transformar as dores reais de sala de aula em uma proposta de inovação pedagógica concreta e aplicável.

        REGRAS INEGOCIÁVEIS:
        1. IDIOMA: Escreva EXCLUSIVAMENTE em Português do Brasil (pt-BR), com linguagem executiva, clara e educacional.
           É TERMINANTEMENTE PROIBIDO usar termos ou jargões em inglês (ex.: "retention", "engagement", "learner",
           "journey", "insight", "feedback", "deadline"). Sempre use o equivalente em português (retenção/permanência
           dos alunos, engajamento, estudante, jornada, percepção, devolutiva, prazo).
        2. CONTEXTO: Baseie-se ESTRITAMENTE nas notas de campo enviadas. Proibido repetir clichês ou texto genérico.
           Cada frase deve fazer sentido para o problema específico relatado.
        3. ESTRUTURA OBRIGATÓRIA — exatamente 4 PILARES fixos (nunca chame de "item"). Para cada pilar, escreva uma
           descrição prática, específica e acionável para ESTE problema:
           - "contencao": Contenção do problema — o que fazer imediatamente para estancar o impacto da dor relatada.
           - "implementacao": Implementação da solução — como aplicar a solução pedagógica na prática, passo a passo.
           - "prevencao": Prevenção de recorrência — o que estruturar para que o problema não volte a acontecer.
           - "sustentacao": Sustentação — como manter o resultado vivo e medir o sucesso ao longo do tempo.

        {contexto_cmu} -- Se preenchido, use como base reguladora científica para enriquecer os pilares.

        Retorne ESTRITAMENTE um JSON limpo (sem markdown, sem comentários), nesta forma exata:
        {{
            "nome_acao": "Título curto, inédito e hiper-focado no problema (em português)",
            "justificativa_pedagogica": "Análise crítica de por que esse gargalo prejudica a aprendizagem e como superá-lo",
            "impacto_negocio": "Métrica educacional, financeira ou operacional diretamente afetada por estas dores",
            "pilares": {{
                "contencao": "Descrição prática da contenção do problema",
                "implementacao": "Descrição prática da implementação da solução",
                "prevencao": "Descrição prática da prevenção de recorrência",
                "sustentacao": "Descrição prática da sustentação"
            }}
        }}
        """
            user_content = f"BLOCO DO FRAMEWORK: {bloco}\n\nDORES REAIS DO DIÁRIO DE BORDO:\n{contexto_dores}"

        bedrock = _get_bedrock_runtime_client()
        body_request = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "temperature": 0.6,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}]
        })

        resposta_ia = None
        usou_fallback = False
        try:
            response = bedrock.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                contentType='application/json',
                accept='application/json',
                body=body_request,
            )
            texto_ia = json.loads(response.get('body').read())['content'][0]['text'].strip()
            resposta_ia = _extrair_json_resposta_mesa(texto_ia)
        except Exception as aws_err:
            print(f"❌ Falha ao gerar/parsear resposta do Bedrock: {aws_err}", file=sys.stderr)
            if tipo_mesa == 'organizacional':
                resposta_ia = _fallback_rascunho_mesa_organizacional(
                    gap_context, notas_texto, direcionador
                )
                usou_fallback = True
            else:
                return jsonify({
                    "status": "error",
                    "message": "Não foi possível gerar a inovação agora. Tente novamente em instantes."
                }), 502

        # Garante que os 4 pilares fixos existam (sem inventar conteúdo: apenas chaves presentes)
        pilares = resposta_ia.get("pilares") or {}
        resposta_ia["pilares"] = {
            "contencao": pilares.get("contencao", ""),
            "implementacao": pilares.get("implementacao", ""),
            "prevencao": pilares.get("prevencao", ""),
            "sustentacao": pilares.get("sustentacao", "")
        }

        payload = {"status": "success", "rascunho": resposta_ia}
        if usou_fallback:
            payload["fallback"] = True
            payload["message"] = "Rascunho gerado localmente — IA remota indisponível no momento."
        return jsonify(payload), 200
    except Exception as e:
        print(f"❌ ERRO IA: {e}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/acoes/salvar', methods=['POST'])
@inovador_bp.route('/api/acoes/salvar', methods=['POST'])
def salvar_acao_final():
    data = request.json or {}
    id_acao_existente = data.get('id_acao')
    id_clie = data.get('id_clie')
    bloco = data.get('bloco_leaction')
    ids_notas = data.get('ids_notas', [])
    nome_acao = data.get('nome_acao')
    justificativa = data.get('justificativa_pedagogica')
    impacto = data.get('impacto_negocio')
    composicao = data.get('composicao_estruturada')
    codigos_ref_raw = data.get('codigos_escolas_ref', '')
    id_prob = data.get('id_prob')
    rotas_metodologicas = data.get('rotas_metodologicas', [])

    subtasks_list = data.get('subtasks_list', [])

    if not id_clie or not nome_acao:
        return jsonify({"status": "error", "message": "id_clie e nome_acao são obrigatórios"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        vincular_escolas = []
        if isinstance(codigos_ref_raw, str) and codigos_ref_raw.strip():
            vincular_escolas = [int(x.strip()) for x in codigos_ref_raw.split(',') if x.strip().isdigit()]
        elif isinstance(codigos_ref_raw, list):
            vincular_escolas = [int(x) for x in codigos_ref_raw if str(x).isdigit()]

        if id_acao_existente:
            id_acao = int(id_acao_existente)
            # Removido o subtask = %s do UPDATE
            query_update = """
                           UPDATE public.inov_acoes
                           SET nome_acao                = %s,
                               justificativa_pedagogica = %s,
                               impacto_negocio          = %s,
                               composicao_estruturada   = %s,
                               id_prob                  = %s,
                               rotas_metodologicas      = %s
                           WHERE id_acao = %s;
                           """
            cursor.execute(query_update,
                           (nome_acao, justificativa, impacto, Json(composicao), id_prob, Json(rotas_metodologicas),
                            id_acao))

            cursor.execute("SELECT id_matu FROM public.inov_acoes_escolas_vinculo WHERE id_acao = %s;", (id_acao,))
            escolas_ja_vacinadas = [r['id_matu'] for r in cursor.fetchall()]
            novos_vinculos = [id_m for id_m in vincular_escolas if id_m not in escolas_ja_vacinadas]

            if novos_vinculos:
                query_vinculo = "INSERT INTO public.inov_acoes_escolas_vinculo (id_acao, id_matu) VALUES (%s, %s);"
                for id_matu_alvo in novos_vinculos:
                    cursor.execute(query_vinculo, (id_acao, id_matu_alvo))

        else:
            # Removido o subtask do INSERT
            query_insert = """
                           INSERT INTO public.inov_acoes (id_clie, bloco_leaction, nome_acao, justificativa_pedagogica,
                                                          impacto_negocio, composicao_estruturada, id_prob,
                                                          rotas_metodologicas)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                           RETURNING id_acao;
                           """
            cursor.execute(query_insert, (id_clie, bloco, nome_acao, justificativa, impacto, Json(composicao), id_prob,
                                          Json(rotas_metodologicas)))
            id_acao = cursor.fetchone()['id_acao']

            if vincular_escolas:
                query_vinculo = "INSERT INTO public.inov_acoes_escolas_vinculo (id_acao, id_matu) VALUES (%s, %s);"
                for id_matu_alvo in vincular_escolas:
                    cursor.execute(query_vinculo, (id_acao, id_matu_alvo))

            if ids_notas:
                query_map = "INSERT INTO public.inov_acao_notas_mapping (id_acao, id_nota) VALUES (%s, %s);"
                for id_nota in ids_notas:
                    cursor.execute(query_map, (id_acao, id_nota))
                cursor.execute("UPDATE public.inov_agenda_notas SET status_nota = 'Incubada' WHERE id_nota = ANY(%s);",
                               (ids_notas,))

        cursor.execute("DELETE FROM public.inov_subtasks WHERE id_acao = %s;", (id_acao,))
        if subtasks_list:
            query_st = "INSERT INTO public.inov_subtasks (id_acao, pilar_subtask, desc_subtask) VALUES (%s, %s, %s);"
            for st in subtasks_list:
                cursor.execute(query_st, (id_acao, st.get('pilar_subtask'), st.get('desc_subtask')))

        session.pop('cmu_selecionado', None)
        conn.commit()
        return jsonify({"status": "success", "id_acao": id_acao,
                        "message": "Sprint pedagógica e Subtasks incubadas com sucesso!"}), 201

    except Exception as e:
        conn.rollback()
        print(f"❌ ERRO UPSERT MULTI-VÍNCULO/SUBTASKS: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/experimentos', methods=['POST'])
@inovador_bp.route('/api/experimentos', methods=['POST'])
def salvar_experimento():
    data = request.json or {}
    id_acao = data.get('id_acao')
    hipo_espex = data.get('hipo_espex')
    desc_espex = data.get('desc_espex')
    result_espex = data.get('result_espex')

    if not id_acao or not hipo_espex or not desc_espex or not result_espex:
        return jsonify({"status": "error", "message": "Campos obrigatórios ausentes"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = """
                INSERT INTO public.espex_acao (id_acao, hipo_espex, desc_espex, result_espex)
                VALUES (%s, %s, %s, %s) \
                RETURNING *; \
                """
        cursor.execute(query, (id_acao, hipo_espex, desc_espex, result_espex))
        novo_espex = cursor.fetchone()
        conn.commit()
        return jsonify({"status": "success", "data": novo_espex}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/experimentos', methods=['GET'])
@inovador_bp.route('/api/experimentos', methods=['GET'])
def listar_experimentos():
    id_acao = request.args.get('id_acao')
    if not id_acao:
        return jsonify({"status": "error", "message": "id_acao é obrigatório"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = """
                SELECT id_espex, hipo_espex, desc_espex, result_espex
                FROM public.espex_acao
                WHERE id_acao = %s
                ORDER BY id_espex ASC; \
                """
        cursor.execute(query, (id_acao,))
        experimentos = cursor.fetchall()
        return jsonify({"status": "success", "data": experimentos}), 200
    except Exception as e:
        print(f"❌ ERRO CRÍTICO GET EXPERIMENTOS: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/cmu/buscar', methods=['GET'])
@inovador_bp.route('/api/cmu/buscar', methods=['GET'])
def buscar_problemas_cmu():
    termo = request.args.get('q', '').strip()
    if len(termo) < 2:
        return jsonify({"status": "success", "data": []}), 200

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = """
                SELECT id_prob, grupo_prob, categoria_prob, desc_prob, razoes_prob, solucoes_prob
                FROM public.ctdi_problemas_referencia
                WHERE categoria_prob ILIKE %s \
                   OR desc_prob ILIKE %s \
                   OR razoes_prob ILIKE %s
                ORDER BY categoria_prob ASC, id_prob ASC
                LIMIT 5; \
                """
        like_param = f"%{termo}%"
        cursor.execute(query, (like_param, like_param, like_param))
        resultados = cursor.fetchall()
        return jsonify({"status": "success", "data": resultados}), 200
    except Exception as e:
        print(f"❌ ERRO BUSCA COMBINADA CMU: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/cmu/sessao', methods=['GET', 'POST', 'DELETE'])
@inovador_bp.route('/api/cmu/sessao', methods=['GET', 'POST', 'DELETE'])
def gerenciar_cmu_sessao():
    if request.method == 'POST':
        data = request.json or {}
        session['cmu_selecionado'] = data.get('cmu')
        return jsonify({"status": "success", "message": "Retido"}), 200
    elif request.method == 'DELETE':
        session.pop('cmu_selecionado', None)
        return jsonify({"status": "success", "message": "Expurgado"}), 200
    else:
        return jsonify({"status": "success", "data": session.get('cmu_selecionado')}), 200


# =========================================================================
# 🌟 NOVO: ENDPOINTS DE PESQUISA INTELIGENTE DE METODOLOGIAS ATIVAS
# =========================================================================

@inovador_bp.route('/inovador/api/metodologias/buscar', methods=['GET'])
@inovador_bp.route('/api/metodologias/buscar', methods=['GET'])
def buscar_metodologias_ativas():
    """Realiza busca preditiva filtrando as categorias metodológicas da primeira tabela"""
    termo = request.args.get('q', '').strip()
    if len(termo) < 2:
        return jsonify({"status": "success", "data": []}), 200

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = """
                SELECT id_meta, cate_metodo, foco_plan, abor_teorica, prop_pratico
                FROM public.inov_metod_ativas
                WHERE cate_metodo ILIKE %s \
                   OR prop_pratico ILIKE %s
                ORDER BY id_meta ASC \
                LIMIT 5; \
                """
        like_param = f"%{termo}%"
        cursor.execute(query, (like_param, like_param))
        return jsonify({"status": "success", "data": cursor.fetchall()}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/metodologias/praticas', methods=['GET'])
@inovador_bp.route('/api/metodologias/praticas', methods=['GET'])
def buscar_praticas_por_meta():
    """Traz todas as práticas detalhadas de uma determinada categoria metodológica selecionada"""
    id_meta = request.args.get('id_meta')
    if not id_meta:
        return jsonify({"status": "error", "message": "id_meta é obrigatório"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = """
                SELECT id_prat, id_meta, estra_pratica, meca_func, recursos_impacto
                FROM public.metodo_ativas_praticas
                WHERE id_meta = %s
                ORDER BY id_prat ASC; \
                """
        cursor.execute(query, (id_meta,))
        return jsonify({"status": "success", "data": cursor.fetchall()}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/experimentos', methods=['PUT'])
@inovador_bp.route('/api/experimentos', methods=['PUT'])
def atualizar_experimento():
    data = request.json or {}
    id_espex = data.get('id_espex')
    hipo = data.get('hipo_espex')
    desc = data.get('desc_espex')
    result = data.get('result_espex')

    if not id_espex: return jsonify({"status": "error", "message": "id_espex ausente"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            UPDATE public.espex_acao
            SET hipo_espex = %s, desc_espex = %s, result_espex = %s
            WHERE id_espex = %s RETURNING *;
        """, (hipo, desc, result, id_espex))
        upd = cursor.fetchone()
        conn.commit()
        return jsonify({"status": "success", "data": upd}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# =========================================================================
# 🔗 FRENTE 3: PONTE MESA DX -> KANBAN (IMPORTAÇÃO DO JSON UNIVERSAL 1.0.0)
# =========================================================================

@inovador_bp.route('/inovador/api/sprints/importar', methods=['POST'])
@inovador_bp.route('/api/sprints/importar', methods=['POST'])
def importar_sprint_inovacao():
    """Lê o payload Universal 1.0.0 exportado pela Mesa de Inovação e cria a Sprint
    no Kanban com status 'em analise'. O id_bloc entra como 0 (não acoplado); o bloco
    metodológico será definido depois, na etapa 'Planejar Sprint'.

    Nota técnica: o backlog NÃO é gravado em ctdi_okr_atividades neste momento porque
    aquela tabela exige id_kr NOT NULL (FK -> ctdi_okr_krs). O array bruto do JSON é
    preservado em ctdi_sprn.metrics_scores (jsonb) para conversão limpa no planejamento.
    """
    data = request.json or {}
    id_clie = data.get('id_clie')
    payload = data.get('payload_sprint', {})

    sprint_data = payload.get('sprint_exportada')
    if not sprint_data:
        return jsonify({"success": False, "error": "JSON inválido ou não originado da Mesa de Inovação"}), 400

    nome_sprint = sprint_data.get('nome_sprint', 'Sprint de Inovação DX')
    desc_sprint = sprint_data.get('meta_da_sprint', 'Objetivo não detalhado.')
    backlog_itens = sprint_data.get('backlog_itens', []) or []
    metadados = payload.get('metadados') or {}
    direcionador = (
        metadados.get('direcionador_estrategico')
        or sprint_data.get('direcionador_estrategico')
        or {}
    )
    bloco_origem = metadados.get('bloco_origem')

    origem_label = (metadados.get('origem') or 'Mesa de Inovação - MudaEdu').strip()
    metrics_payload = {
        "backlog_dx": backlog_itens,
        "schema_versao": metadados.get('schema_versao', '1.0.0'),
        "id_clie": id_clie,
        "id_origem_mesa": sprint_data.get('id_origem_mesa'),
        "duracao_semanas": sprint_data.get('duracao_sugerida_semanas', 2),
        "origem": origem_label,
        "tipo_mesa": metadados.get('tipo_mesa'),
        "id_direc": metadados.get('id_direc') or direcionador.get('id_direc'),
        "direcionador_estrategico": direcionador,
        "bloco_origem": bloco_origem,
    }

    if not id_clie:
        return jsonify({"success": False, "error": "id_clie é obrigatório."}), 400

    try:
        id_clie_int = int(id_clie)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "id_clie inválido."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        id_proj = resolver_ou_criar_projeto_cliente(cursor, id_clie_int)
        id_squad = criar_squad_vazia_para_sprint(
            cursor, id_proj=id_proj, nome_sprint=nome_sprint
        )

        cursor.execute(
            """
            INSERT INTO public.ctdi_sprn
                (id_bloc, id_squad, name_sprn, desc_sprn, stat_sprn, url_kanban, metrics_scores)
            VALUES (0, %s, %s, %s, %s, 'IMPORTACAO_JSON_DX', %s)
            RETURNING id_sprn;
            """,
            (id_squad, nome_sprint, desc_sprint, STAT_EM_ANALISE, Json(metrics_payload))
        )
        id_sprn_nova = cursor.fetchone()['id_sprn']
        atualizar_nome_squad_pos_sprint(cursor, id_squad, nome_sprint, id_sprn_nova)

        conn.commit()
        return jsonify({
            "success": True,
            "status": "success",
            "id_sprn": id_sprn_nova,
            "id_squad": id_squad,
            "nome_squad": format_nome_squad(nome_sprint, id_sprn_nova),
            "itens_importados": len(backlog_itens)
        }), 201

    except Exception as e:
        conn.rollback()
        print(f"❌ ERRO IMPORTAÇÃO DX: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


def _extrair_backlog_dx_da_sprint(metrics_scores, exec_notes):
    """Lê o backlog estruturado do jsonb metrics_scores; faz fallback legado em exec_notes."""
    ms = metrics_scores or {}
    if isinstance(ms, str):
        try:
            ms = json.loads(ms)
        except (json.JSONDecodeError, TypeError):
            ms = {}

    backlog = ms.get('backlog_dx') or []
    if backlog:
        return backlog, ms

    if not exec_notes:
        return [], ms

    itens_legado = []
    bloco_atual = None
    for linha in exec_notes.splitlines():
        texto = linha.strip()
        if not texto:
            continue
        if texto.startswith('▸'):
            bloco_atual = {
                'titulo': texto.lstrip('▸').strip(),
                'descricao': '',
                'subtasks': []
            }
            itens_legado.append(bloco_atual)
        elif texto.startswith('•') and bloco_atual is not None:
            bloco_atual.setdefault('subtasks', []).append(
                {'subtask_title': texto.lstrip('•').strip()}
            )
        elif bloco_atual is not None and not texto.startswith('•'):
            bloco_atual['descricao'] = (
                f"{bloco_atual['descricao']}\n{texto}".strip()
                if bloco_atual.get('descricao') else texto
            )

    return itens_legado, ms


@inovador_bp.route('/inovador/api/squads/cliente', methods=['GET'])
@inovador_bp.route('/api/squads/cliente', methods=['GET'])
def listar_squads_por_cliente():
    """Squads do projeto ativo do cliente — usado no modal de Planejamento DX."""
    id_clie = request.args.get('id_clie')
    if not id_clie:
        return jsonify({"status": "error", "message": "id_clie é obrigatório"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            """
            SELECT q.id_squad, q.nome_squad, p.id_proj
            FROM public.ctdi_squads q
                     JOIN public.ctdi_projetos p ON q.id_proj = p.id_proj
            WHERE p.id_clie = %s
              AND p.status = 'ATIVO'
            ORDER BY q.nome_squad ASC;
            """,
            (id_clie,)
        )
        squads = cursor.fetchall()
        return jsonify({"status": "success", "data": limpar_objeto(squads)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/blocos/buscar', methods=['GET'])
@inovador_bp.route('/api/blocos/buscar', methods=['GET'])
def buscar_blocos_metodologicos():
    """Busca contextual nos 105 blocos do framework (leaf_bloc) por nome ou descrição."""
    termo = (request.args.get('q') or '').strip()
    if len(termo) < 3:
        return jsonify({"status": "success", "data": []}), 200

    like = f"%{termo}%"
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            """
            SELECT id_bloc, name_bloc, desc_bloc
            FROM public.leaf_bloc
            WHERE name_bloc ILIKE %s OR desc_bloc ILIKE %s
            ORDER BY name_bloc ASC
            LIMIT 10;
            """,
            (like, like)
        )
        blocos = cursor.fetchall()
        return jsonify({"status": "success", "data": limpar_objeto(blocos)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/sprints/planejar-dx', methods=['PUT'])
@inovador_bp.route('/api/sprints/planejar-dx', methods=['PUT'])
def planejar_sprint_dx():
    """Acopla metodologicamente uma Sprint DX importada e converte o backlog em atividades OKR.

    O id_squad pode ser o literal 'NEW' — neste caso uma Task Force dedicada é criada
    em ctdi_squads vinculada ao projeto ativo do cliente.
    """
    data = request.json or {}
    id_sprn = data.get('id_sprn')
    id_bloc = data.get('id_bloc')
    id_squad = data.get('id_squad')
    id_kr = data.get('id_kr')
    dtini_sprn = data.get('dtini_sprn')
    id_matu = data.get('id_matu')
    id_clie = data.get('id_clie')

    if not all([id_sprn, id_bloc, id_squad, id_kr, dtini_sprn]):
        return jsonify({
            "success": False,
            "error": "Campos obrigatórios: id_sprn, id_bloc, id_squad, id_kr, dtini_sprn"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            """
            SELECT id_sprn, name_sprn, stat_sprn, metrics_scores, exec_notes, url_kanban
            FROM public.ctdi_sprn
            WHERE id_sprn = %s;
            """,
            (id_sprn,)
        )
        sprint_atual = cursor.fetchone()
        if not sprint_atual:
            return jsonify({"success": False, "error": "Sprint não encontrada."}), 404

        stat_atual = (sprint_atual.get('stat_sprn') or '').lower().strip()
        if not status_em_analise(stat_atual):
            return jsonify({
                "success": False,
                "error": f"Sprint não está em análise (status atual: {sprint_atual.get('stat_sprn')})."
            }), 400

        backlog_itens, metrics_atual = _extrair_backlog_dx_da_sprint(
            sprint_atual.get('metrics_scores'),
            sprint_atual.get('exec_notes')
        )

        # --- CRIAÇÃO SOB DEMANDA DE SQUAD DEDICADA (Task Force DX) ---
        if str(id_squad).upper().strip() == 'NEW':
            id_clie_squad = id_clie or metrics_atual.get('id_clie')
            if not id_clie_squad:
                return jsonify({
                    "success": False,
                    "error": "Não foi possível identificar o cliente para criar a Squad dedicada."
                }), 400

            id_proj_novo = resolver_ou_criar_projeto_cliente(cursor, int(id_clie_squad))
            id_squad = criar_squad_vazia_para_sprint(
                cursor,
                id_proj=id_proj_novo,
                nome_sprint=sprint_atual.get('name_sprn') or 'Inovação',
                id_sprn=int(id_sprn),
            )

        id_itera = None
        if id_matu:
            cursor.execute(
                """
                SELECT i.id_itera
                FROM public.ctdi_main m
                         JOIN public.ctdi_itera i ON m.id_ctdi = i.id_ctdi
                WHERE m.id_matu = %s
                ORDER BY i.id_phase ASC NULLS LAST, i.id_itera ASC
                LIMIT 1;
                """,
                (id_matu,)
            )
            row_itera = cursor.fetchone()
            if row_itera:
                id_itera = row_itera['id_itera']

        duracao = metrics_atual.get('duracao_semanas', 2)
        try:
            duracao = int(duracao)
        except (TypeError, ValueError):
            duracao = 2

        dx_objetivo_id = None
        if id_kr:
            cursor.execute(
                """
                SELECT o.dx_objetivo_id
                FROM public.ctdi_okr_krs k
                JOIN public.ctdi_okr_objetivos_dt o ON o.id_obj_dt = k.id_obj_dt
                WHERE k.id_kr = %s
                LIMIT 1
                """,
                (id_kr,),
            )
            row_dx = cursor.fetchone()
            if row_dx and row_dx.get('dx_objetivo_id'):
                dx_objetivo_id = row_dx['dx_objetivo_id']

        cursor.execute(
            """
            UPDATE public.ctdi_sprn
            SET id_bloc     = %s,
                id_squad    = %s,
                id_itera    = COALESCE(%s, id_itera),
                dtini_sprn  = %s::date,
                dtend_sprn  = (%s::date + make_interval(weeks => %s)),
                stat_sprn   = %s,
                week_sprn   = %s,
                metrics_scores = %s,
                objetivo_id = COALESCE(%s, objetivo_id)
            WHERE id_sprn = %s
            RETURNING id_sprn, name_sprn, stat_sprn;
            """,
            (
                id_bloc,
                id_squad,
                id_itera,
                dtini_sprn,
                dtini_sprn,
                duracao,
                STAT_PLANEJADA_BACKLOG,
                duracao,
                Json({
                    **metrics_atual,
                    "backlog_dx": [],
                    "planejado_em": datetime.now().isoformat(),
                    "id_kr_acoplado": id_kr,
                    "id_bloc_acoplado": id_bloc,
                    "id_squad_acoplado": id_squad,
                    "dx_objetivo_id": dx_objetivo_id,
                }),
                dx_objetivo_id,
                id_sprn
            )
        )
        sprint_planejada = cursor.fetchone()

        atividades_criadas = 0
        if backlog_itens:
            query_ativ = """
                INSERT INTO public.ctdi_okr_atividades
                    (id_sprn, id_kr, dx_kr_id, nome_ativ, desc_ativ, status_ativ, data_planejamento)
                SELECT %s, %s, k.dx_kr_id, %s, %s, 'A Fazer', %s::date
                FROM public.ctdi_okr_krs k
                WHERE k.id_kr = %s AND k.dx_kr_id IS NOT NULL;
            """
            for item in backlog_itens:
                titulo_fase = item.get('titulo', 'Fase Operacional')
                desc_fase = item.get('descricao', '')
                subtasks = item.get('subtasks', []) or []

                notas_subtasks = ""
                if subtasks:
                    notas_subtasks = "\n\nSubtasks Planejadas:\n" + "\n".join(
                        [f"• {st.get('subtask_title', '')}" for st in subtasks if st.get('subtask_title')]
                    )

                texto_final_atividade = f"{desc_fase}{notas_subtasks}".strip()
                cursor.execute(
                    query_ativ,
                    (id_sprn, id_kr, titulo_fase, texto_final_atividade or None, dtini_sprn, id_kr)
                )
                atividades_criadas += 1

        conn.commit()
        return jsonify({
            "success": True,
            "status": "success",
            "id_sprn": sprint_planejada['id_sprn'],
            "nome_sprint": sprint_planejada['name_sprn'],
            "stat_sprn": sprint_planejada['stat_sprn'],
            "atividades_criadas": atividades_criadas
        }), 200

    except Exception as e:
        conn.rollback()
        print(f"❌ ERRO PLANEJAMENTO DX: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


def _bloco_key_from_origem(origem):
    if not origem or not isinstance(origem, dict):
        return None
    return str(origem.get('id_bloc') or origem.get('nome') or '').strip() or None


@inovador_bp.route('/inovador/api/sprints/blocos-pipeline', methods=['GET'])
@inovador_bp.route('/api/sprints/blocos-pipeline', methods=['GET'])
def listar_blocos_pipeline_relatorio():
    """Chaves de blocos do relatório que já estão na Mesa/Kanban (fora do backlog)."""
    id_clie = request.args.get('id_clie')
    if not id_clie:
        return jsonify({"keys": []}), 200

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        try:
            cursor.execute(
                """
                SELECT id_sprn, name_sprn, desc_sprn, metrics_scores, stat_sprn, url_kanban, tags
                FROM public.ctdi_sprn
                WHERE (metrics_scores ->> 'id_clie')::int = %s
                  AND (
                        metrics_scores ? 'bloco_origem'
                        OR url_kanban = 'IMPORTACAO_JSON_DX'
                      )
                  AND LOWER(TRIM(COALESCE(stat_sprn, ''))) NOT IN ('cancelada', 'concluida', 'concluido')
                ORDER BY id_sprn DESC;
                """,
                (id_clie,)
            )
        except Exception:
            conn.rollback()
            cursor.execute(
                """
                ALTER TABLE public.ctdi_sprn
                    ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}';
                """
            )
            conn.commit()
            cursor.execute(
                """
                SELECT id_sprn, name_sprn, desc_sprn, metrics_scores, stat_sprn, url_kanban, tags
                FROM public.ctdi_sprn
                WHERE (metrics_scores ->> 'id_clie')::int = %s
                  AND (
                        metrics_scores ? 'bloco_origem'
                        OR url_kanban = 'IMPORTACAO_JSON_DX'
                      )
                  AND LOWER(TRIM(COALESCE(stat_sprn, ''))) NOT IN ('cancelada', 'concluida', 'concluido')
                ORDER BY id_sprn DESC;
                """,
                (id_clie,)
            )
        rows = cursor.fetchall()
        keys = []
        items = []
        for row in rows:
            metrics = row.get('metrics_scores') or {}
            if isinstance(metrics, str):
                try:
                    metrics = json.loads(metrics)
                except Exception:
                    metrics = {}
            key = _bloco_key_from_origem(metrics.get('bloco_origem'))
            if not key:
                bo = metrics.get('bloco_origem') or {}
                key = str(bo.get('nome') or row.get('name_sprn') or '').strip() or None
            if not key and row.get('url_kanban') == 'IMPORTACAO_JSON_DX':
                key = str(row.get('name_sprn') or '').strip() or None
            if key:
                keys.append(key)
                raw_tags = row.get('tags') or []
                if isinstance(raw_tags, str):
                    try:
                        raw_tags = json.loads(raw_tags)
                    except Exception:
                        raw_tags = []
                tags = [str(t).strip() for t in (raw_tags or []) if str(t).strip()]
                items.append({
                    "block_key": key,
                    "id_sprn": row.get('id_sprn'),
                    "stat_sprn": row.get('stat_sprn'),
                    "nome": row.get('name_sprn'),
                    "desc": row.get('desc_sprn'),
                    "tipo_mesa": metrics.get('tipo_mesa'),
                    "bloco_nome": (metrics.get('bloco_origem') or {}).get('nome'),
                    "tags": tags,
                })
        dedup = {}
        for item in items:
            dedup[item['block_key']] = item
        items = list(dedup.values())
        return jsonify({"keys": list(dict.fromkeys(keys)), "items": items}), 200
    except Exception as e:
        print(f"❌ ERRO blocos-pipeline: {e}")
        return jsonify({"keys": [], "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@inovador_bp.route('/inovador/api/sprints/devolver-relatorio', methods=['POST'])
@inovador_bp.route('/api/sprints/devolver-relatorio', methods=['POST'])
def devolver_sprint_relatorio():
    """Remove sprint do Kanban Planejada/Inovação e devolve o bloco ao backlog do relatório."""
    data = request.json or {}
    id_sprn = data.get('id_sprn')
    if not id_sprn:
        return jsonify({"success": False, "error": "id_sprn é obrigatório"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            """
            SELECT id_sprn, stat_sprn, metrics_scores
            FROM public.ctdi_sprn
            WHERE id_sprn = %s;
            """,
            (id_sprn,)
        )
        sprint = cursor.fetchone()
        if not sprint:
            return jsonify({"success": False, "error": "Sprint não encontrada."}), 404

        stat = (sprint.get('stat_sprn') or '').lower().strip().replace('_', ' ')
        permitidos = {
            'em analise', 'em_analise',
            STAT_PLANEJADA_BACKLOG, 'planejada', 'planejado',
            'pendente', 'agendada', 'agendado',
        }
        if stat not in permitidos:
            return jsonify({
                "success": False,
                "error": f"Não é possível devolver sprint com status '{sprint.get('stat_sprn')}'."
            }), 400

        metrics = sprint.get('metrics_scores') or {}
        if isinstance(metrics, str):
            try:
                metrics = json.loads(metrics)
            except Exception:
                metrics = {}
        bloco_key = _bloco_key_from_origem(metrics.get('bloco_origem'))

        cursor.execute(
            "DELETE FROM public.ctdi_sprn WHERE id_sprn = %s;",
            (id_sprn,)
        )
        conn.commit()
        return jsonify({
            "success": True,
            "bloco_key": bloco_key,
            "message": "Sprint removida. O bloco voltou ao backlog do relatório."
        }), 200
    except Exception as e:
        conn.rollback()
        print(f"❌ ERRO devolver-relatorio: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# Status canônicos no Drag & Drop (Backlog / Em Andamento / Concluída).
# 'em_analise' é excluído — exige Modal de Planejamento.
_STATUS_DND_PERMITIDOS = frozenset({
    STAT_PLANEJADA_BACKLOG,
    STAT_EM_ANDAMENTO,
    STAT_CONCLUIDA,
})


@inovador_bp.route('/inovador/api/sprints/status-dnd', methods=['PUT'])
@inovador_bp.route('/api/sprints/status-dnd', methods=['PUT'])
def atualizar_status_sprint_dnd():
    """Atualização rápida de status via Drag & Drop entre Backlog / Em Andamento / Concluída."""
    data = request.json or {}
    id_sprn = data.get('id_sprn')
    novo_status = canonicalizar_status_dnd(data.get('status'))

    if not id_sprn:
        return jsonify({"success": False, "error": "id_sprn é obrigatório"}), 400

    if novo_status not in _STATUS_DND_PERMITIDOS:
        return jsonify({
            "success": False,
            "error": f"Status inválido para Drag & Drop: '{data.get('status')}'."
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            "SELECT stat_sprn FROM public.ctdi_sprn WHERE id_sprn = %s;",
            (id_sprn,)
        )
        atual = cursor.fetchone()
        if not atual:
            return jsonify({"success": False, "error": "Sprint não encontrada."}), 404

        stat_origem = (atual.get('stat_sprn') or '').lower().strip()
        if status_em_analise(stat_origem):
            return jsonify({
                "success": False,
                "error": "Sprints em análise devem ser acopladas via Modal de Planejamento."
            }), 409

        cursor.execute(
            """
            UPDATE public.ctdi_sprn
            SET stat_sprn = %s,
                dtini_sprn = CASE WHEN %s = %s THEN COALESCE(dtini_sprn, CURRENT_DATE)
                                  ELSE dtini_sprn END,
                dtend_sprn = CASE WHEN %s = %s THEN COALESCE(dtend_sprn, CURRENT_DATE)
                                  ELSE dtend_sprn END
            WHERE id_sprn = %s
            RETURNING id_sprn, stat_sprn, dtini_sprn, dtend_sprn;
            """,
            (
                novo_status,
                novo_status, STAT_EM_ANDAMENTO,
                novo_status, STAT_CONCLUIDA,
                id_sprn,
            )
        )
        atualizada = cursor.fetchone()
        conn.commit()
        return jsonify({
            "success": True,
            "status": "success",
            "id_sprn": atualizada['id_sprn'],
            "stat_sprn": atualizada['stat_sprn'],
            "dtini_sprn": limpar_objeto(atualizada.get('dtini_sprn')),
            "dtend_sprn": limpar_objeto(atualizada.get('dtend_sprn'))
        }), 200

    except Exception as e:
        conn.rollback()
        print(f"❌ ERRO STATUS DND: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


def register_paneldx_public_api_routes(flask_app):
    """Expõe rotas /api/* no app Flask principal.

    Em produção o ALB envia /api/* direto ao backend; pontes do Node não são atingidas.
    """
    rotas = [
        ('/api/mesa-inovacao/notas', 'mesa_inovacao_notas_get', listar_notas_mesa_org, ['GET']),
        ('/api/mesa-inovacao/notas', 'mesa_inovacao_notas_post', criar_nota_mesa_org, ['POST']),
        ('/api/mesa-inovacao/notas', 'mesa_inovacao_notas_delete', deletar_nota_mesa_org, ['DELETE']),
        ('/api/mesa-inovacao/notas/incubar', 'mesa_inovacao_notas_incubar', incubar_notas_mesa_org, ['POST']),
        ('/api/mesa-inovacao/gerar-preview', 'mesa_inovacao_gerar_preview', gerar_preview_ia, ['POST']),
        ('/api/admin/mesas-inovacao', 'admin_mesas_inovacao_list', listar_mesas_inovacao_admin, ['GET']),
        ('/api/sprints/importar', 'paneldx_sprints_importar', importar_sprint_inovacao, ['POST']),
        ('/api/sprints/planejar-dx', 'paneldx_sprints_planejar_dx', planejar_sprint_dx, ['PUT']),
        ('/api/sprints/blocos-pipeline', 'paneldx_sprints_blocos_pipeline', listar_blocos_pipeline_relatorio, ['GET']),
        ('/api/sprints/devolver-relatorio', 'paneldx_sprints_devolver_relatorio', devolver_sprint_relatorio, ['POST']),
        ('/api/sprints/status-dnd', 'paneldx_sprints_status_dnd', atualizar_status_sprint_dnd, ['PUT']),
        ('/api/squads/cliente', 'paneldx_squads_cliente', listar_squads_por_cliente, ['GET']),
        ('/api/blocos/buscar', 'paneldx_blocos_buscar', buscar_blocos_metodologicos, ['GET']),
    ]
    for path, endpoint, view_func, methods in rotas:
        flask_app.add_url_rule(path, endpoint=endpoint, view_func=view_func, methods=methods)