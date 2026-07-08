"""Rotas da API para interação com o agente de IA e gestão do histórico."""

from flask import Blueprint, request, jsonify
from database.models import SessionLocal, Project, InteractionHistory
from services.innovation_agent import InnovationAgent

# Instância do Blueprint para registrar no app principal
ai_routes = Blueprint('ai_routes', __name__)

# Instância do agente de IA (AWS Bedrock)
agent = InnovationAgent()

@ai_routes.route('/methodologies', methods=['GET'])
def get_methodologies():
    """Retorna as metodologias disponíveis na base de prompts."""
    return jsonify(agent.list_methodologies())

@ai_routes.route('/agent/interact', methods=['POST'])
def interact():
    """Processa a interação do usuário, mantendo o contexto no banco de dados."""
    data = request.json
    
    if not data or 'user_input' not in data:
        return jsonify({"error": "O campo 'user_input' é obrigatório."}), 400

    methodology_id = data.get('methodology_id', 'design_thinking')
    current_step = data.get('current_step', 'empatia')
    user_input = data.get('user_input')
    project_id = data.get('project_id')

    session = SessionLocal()
    try:
        # 1. Recuperar ou Criar o Projeto
        if project_id:
            project = session.query(Project).filter(Project.id == project_id).first()
            if not project:
                return jsonify({"error": "Projeto não encontrado."}), 404
            
            # Opcional: Atualizar o passo atual se o usuário avançou no frontend
            if project.current_step != current_step:
                # Nota: como o modelo usa 'steps' na relação, aqui apenas marcamos logicamente.
                pass 
        else:
            # Se não houver project_id, cria uma nova sessão de inovação
            project = Project(nome=f"Sessão - {methodology_id.replace('_', ' ').title()}")
            session.add(project)
            session.commit()
            session.refresh(project)
            project_id = project.id

        # 2. Salvar a entrada do usuário no histórico
        user_msg = InteractionHistory(
            project_id=project_id, 
            role="user", 
            content=user_input
        )
        session.add(user_msg)
        session.commit()

        # 3. Recuperar histórico para montar o contexto (Memória da IA)
        # Limitamos às últimas 10 interações para manter o foco e economizar tokens do Claude
        history = session.query(InteractionHistory).filter(
            InteractionHistory.project_id == project_id
        ).order_by(InteractionHistory.timestamp.asc()).limit(10).all()

        context_lines = []
        for h in history[:-1]:  # Exclui a última mensagem pois a enviaremos separada
            remetente = "Usuário" if h.role == "user" else "IA (Facilitador)"
            context_lines.append(f"{remetente}: {h.content}")
        
        context_text = "\n".join(context_lines)

        # Prepara a entrada contextualizada para o LangChain
        if context_text:
            contextualized_input = (
                f"Aqui está o resumo da nossa conversa até agora:\n"
                f"{context_text}\n\n"
                f"Agora, responda a esta nova entrada do usuário:\n"
                f"Usuário: {user_input}"
            )
        else:
            contextualized_input = user_input

        # 4. Chamar a IA (AWS Bedrock)
        ai_response_text = agent.process_interaction(
            methodology_id, 
            current_step, 
            contextualized_input
        )

        # 5. Salvar a resposta da IA no banco de dados
        ai_msg = InteractionHistory(
            project_id=project_id, 
            role="agent", 
            content=ai_response_text
        )
        session.add(ai_msg)
        session.commit()

        # Retorna a resposta e o ID do projeto para o frontend continuar a sessão
        return jsonify({
            "project_id": project_id,
            "response": ai_response_text
        })

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500
    
    finally:
        session.close()
