from flask import Blueprint, request, jsonify, render_template, redirect, session
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import json
import boto3
import os
from datetime import datetime, date

# 🎯 Sobe dois níveis e encontra a pasta real do Frontend no Windows
views_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'LeAction_Sys_FE', 'views'))

inovador_bp = Blueprint(
    'inovador',
    __name__,
    template_folder=views_path
)


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
    bloco = data.get('bloco_leaction')
    ids_notas = data.get('ids_notas', [])
    id_prob_cmu = data.get('id_prob_cmu')

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    contexto_cmu = ""
    try:
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
        Você é um Designer Instrucional Sênior sob a metodologia LeActionF. Crie uma proposta 100% sob medida para as dores coletadas.
        PROIBIDO REPETIR textos prontos ou usar clichês genéricos. Cada campo deve focar estritamente nas notas de campo enviadas.

        {contexto_cmu} -- Se preenchido, use como base reguladora científica para enriquecer os pilares.

        Retorne estritamente um JSON limpo, sem tags markdown ou comentários:
        {{
            "nome_acao": "Título curto, inédito e hiper-focado no problema",
            "justificativa_pedagogica": "Análise crítica do porquê esse gargalo sabota a aprendizagem e como superá-lo",
            "impacto_negocio": "Métrica financeira ou operacional direta afetada por estas dores específicas",
            "pilares": {{
                "item_1": "Ação imediata contextualizada para sanar a primeira dor",
                "item_2": "Estratégia prática de engajamento baseada no relato",
                "item_3": "Mecanismo de acompanhamento ou métrica de sucesso específica",
                "item_4": "Entrega formativa final ou plano de sustentação"
            }}
        }}
        """

        bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
        body_request = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "temperature": 0.6,
            "system": system_prompt,
            "messages": [{"role": "user",
                          "content": f"BLOCO DO FRAMEWORK: {bloco}\n\nDORES REAIS DO DIÁRIO DE BORDO:\n{contexto_dores}"}]
        })

        try:
            response = bedrock.invoke_model(modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
                                            contentType='application/json', accept='application/json',
                                            body=body_request)
            resposta_ia = json.loads(json.loads(response.get('body').read())['content'][0]['text'].strip())
        except Exception as aws_err:
            print(f"⚠️ Usando Fallback Dinâmico Local: {aws_err}")
            resposta_ia = {
                "nome_acao": f"Redesenho Estratégico: Intervenção em {notas_recuperadas[0]['conteudo_bruto'][:25]}...",
                "justificativa_pedagogica": f"Garantir a fluidez instrucional atacando as barreiras reais mapeadas. Referência teórica aplicada.",
                "impacto_negocio": f"Blindagem do engajamento em sala e retention de alunos para mitigar as dores coletadas.",
                "pilares": {
                    "item_1": f"Contenção focada no gargalo de '{notas_recuperadas[0]['conteudo_bruto'][:25]}...'",
                    "item_2": "Implementação de dinâmica instrucional ativa baseada em evidências",
                    "item_3": "Mapeamento preventivo de recorrência na trilha",
                    "item_4": "Rito de sustentação ativa do aprendizado"
                }
            }

        return jsonify({"status": "success", "rascunho": resposta_ia}), 200
    except Exception as e:
        print(f"❌ ERRO IA: {e}")
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