"""Rotas da matriz estratégica canônica OKR."""



from __future__ import annotations



from flask import Blueprint, jsonify, request



from estrategia_matriz import (

    NIVEL_IMPLEMENTACAO_LABELS,

    atualizar_kr_cliente,

    atualizar_objetivo_cliente,

    carregar_arvore_matriz_okr,

    carregar_detalhe_objetivo_cliente,

    carregar_cascata_okr_atividade,
    carregar_krs_para_sprint,

    carregar_painel_okr_cliente,

    carregar_resumo_okr_cliente,

    derivar_nivel_implementacao,

    label_nivel,

    resolver_hierarquia_objetivo,

)



estrategia_bp = Blueprint("estrategia", __name__)





def register_estrategia_routes(app):

    app.register_blueprint(estrategia_bp)





def _get_conn():

    from app import get_db_conn

    return get_db_conn()





@estrategia_bp.route("/api/estrategia/matriz-okr", methods=["GET"])

def get_matriz_okr():

    try:

        conn = _get_conn()

        arvore = carregar_arvore_matriz_okr(conn)

        return jsonify({"data": arvore, "total_direcionadores": len(arvore)}), 200

    except Exception as e:

        return jsonify({"error": str(e)}), 500





@estrategia_bp.route("/api/estrategia/resumo-okr", methods=["GET"])

def get_resumo_okr_cliente():

    """Painel OKR agrupado por direcionador + linhas planas para tabela."""

    id_clie = request.args.get("id_clie")

    if not id_clie:

        return jsonify({"error": "id_clie obrigatório."}), 400

    try:

        conn = _get_conn()

        painel = carregar_painel_okr_cliente(conn, int(id_clie))

        return jsonify({

            "success": True,

            "direcionadores": painel["direcionadores"],

            "rows": painel["rows"],

            "stats": painel["stats"],

            "total": len(painel["rows"]),

        }), 200

    except Exception as e:

        return jsonify({"error": str(e)}), 500





@estrategia_bp.route("/api/estrategia/objetivo-cliente/<int:id_obj_dt>", methods=["GET"])

def get_objetivo_cliente_detalhe(id_obj_dt: int):

    try:

        conn = _get_conn()

        data = carregar_detalhe_objetivo_cliente(conn, id_obj_dt)

        if not data:

            return jsonify({"error": "Objetivo não encontrado."}), 404

        return jsonify({"success": True, "data": data}), 200

    except Exception as e:

        return jsonify({"error": str(e)}), 500





@estrategia_bp.route("/api/estrategia/objetivo-cliente/<int:id_obj_dt>", methods=["PATCH", "PUT"])

def patch_objetivo_cliente(id_obj_dt: int):

    """Persiste apenas metas de KRs — progresso/nível são calculados pelas atividades."""

    body = request.json or {}

    krs_payload = body.get("krs") or []

    try:

        conn = _get_conn()

        if not atualizar_objetivo_cliente(conn, id_obj_dt):

            return jsonify({"error": "Objetivo não encontrado."}), 404



        for item in krs_payload:

            id_kr = item.get("id_kr")

            if not id_kr:

                continue

            atualizar_kr_cliente(

                conn,

                int(id_kr),

                meta_cliente=item.get("meta_cliente"),

                nome_kr=item.get("nome_kr") or item.get("descricao"),

                desc_kr=item.get("desc_kr") or item.get("descricao"),

                ativo=item.get("ativo"),

            )



        detalhe = carregar_detalhe_objetivo_cliente(conn, id_obj_dt)

        row = None

        if detalhe and detalhe.get("id_clie"):

            for r in carregar_resumo_okr_cliente(conn, detalhe["id_clie"]):

                if r["id_obj_dt"] == id_obj_dt:

                    row = r

                    break

        nivel = derivar_nivel_implementacao(detalhe.get("progresso_pct", 0) if detalhe else 0)

        return jsonify({

            "success": True,

            "nivel_implementacao": nivel,

            "nivel_label": label_nivel(nivel),

            "row": row,

            "data": detalhe,

        }), 200

    except Exception as e:

        return jsonify({"error": str(e)}), 500





@estrategia_bp.route("/api/estrategia/kr-cliente/<int:id_kr>", methods=["PATCH", "PUT"])

def patch_kr_cliente(id_kr: int):

    body = request.json or {}

    try:

        conn = _get_conn()

        ok = atualizar_kr_cliente(

            conn,

            id_kr,

            meta_cliente=body.get("meta_cliente"),

            valor_alvo=body.get("valor_alvo"),

            valor_atual=body.get("valor_atual"),

            nome_kr=body.get("nome_kr") or body.get("descricao"),

            desc_kr=body.get("desc_kr") or body.get("descricao"),

            kpi_nome=body.get("kpi_nome"),

            ativo=body.get("ativo"),

        )

        if not ok:

            return jsonify({"error": "Nada para atualizar ou KR não encontrado."}), 400

        return jsonify({"success": True, "id_kr": id_kr}), 200

    except Exception as e:

        return jsonify({"error": str(e)}), 500





@estrategia_bp.route("/api/estrategia/krs-por-sprint", methods=["GET"])

def get_krs_por_sprint():

    id_sprn = request.args.get("id_sprn")

    id_clie = request.args.get("id_clie")

    if not id_sprn or not id_clie:

        return jsonify({"error": "id_sprn e id_clie são obrigatórios."}), 400

    try:

        conn = _get_conn()

        krs = carregar_krs_para_sprint(conn, int(id_sprn), int(id_clie))

        return jsonify({"success": True, "krs": krs, "total": len(krs)}), 200

    except Exception as e:

        return jsonify({"error": str(e)}), 500





@estrategia_bp.route("/api/estrategia/cascata-okr-atividade", methods=["GET"])

def get_cascata_okr_atividade():

    id_sprn = request.args.get("id_sprn")

    id_clie = request.args.get("id_clie")

    if not id_clie:

        return jsonify({"error": "id_clie é obrigatório."}), 400

    try:

        conn = _get_conn()

        id_sprn_int = int(id_sprn) if id_sprn else None

        cascata = carregar_cascata_okr_atividade(conn, int(id_clie), id_sprn_int)

        return jsonify({"success": True, "direcionadores": cascata, "total": len(cascata)}), 200

    except Exception as e:

        return jsonify({"error": str(e)}), 500





@estrategia_bp.route("/api/estrategia/niveis-implementacao", methods=["GET"])

def get_niveis_implementacao():

    return jsonify({

        "niveis": [

            {"value": k, "label": v} for k, v in NIVEL_IMPLEMENTACAO_LABELS.items()

        ],

        "computed": True,

        "hint": "Nível derivado automaticamente do progresso das atividades de sprint.",

    }), 200





@estrategia_bp.route("/api/estrategia/objetivo/<int:objetivo_id>", methods=["GET"])

def get_objetivo_hierarquia(objetivo_id: int):

    try:

        conn = _get_conn()

        data = resolver_hierarquia_objetivo(conn, objetivo_id)

        if not data:

            return jsonify({"error": "Objetivo não encontrado."}), 404

        return jsonify(data), 200

    except Exception as e:

        return jsonify({"error": str(e)}), 500

