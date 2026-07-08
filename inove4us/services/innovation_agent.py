"""Camada de serviços de IA do inove4us.

Isola a lógica de interação com LLMs e a biblioteca de prompts baseada
nas metodologias inov-ativas de Andrea Filatro.
Integração com AWS Bedrock (Claude Sonnet) via LangChain.
"""

from __future__ import annotations
from typing import Dict
from langchain_aws import ChatBedrock
from langchain_core.messages import SystemMessage, HumanMessage

class InnovationAgent:
    """Agente facilitador baseado na Biblioteca de Metodologias Inov-ativas."""

    # Biblioteca de prompts extraída do framework de Andrea Filatro
    METHODOLOGY_PROMPTS: Dict[str, Dict[str, str]] = {
        "design_thinking": {
            "titulo": "Design Thinking",
            "objetivo": "Resolver problemas complexos compreendendo as necessidades, gerando ideias e testando rápido.",
            "prompt": (
                "Você é um facilitador educacional aplicando o Design Thinking. "
                "Guie o usuário pelas fases iterativas: empatia, definição, ideação, prototipagem e teste. "
                "Sua postura deve ser investigativa. Faça o usuário refletir sobre as necessidades dos usuários finais. "
                "Não entregue a solução; em vez disso, faça perguntas abertas baseadas na metodologia."
            ),
        },
        "aprendizagem_projetos": {
            "titulo": "Aprendizagem Baseada em Projetos",
            "objetivo": "Integrar teoria e prática pela realização de projetos que resultam em produtos concretos.",
            "prompt": (
                "Você é um facilitador guiando a Aprendizagem Baseada em Projetos. "
                "Sua missão é ajudar o usuário a definir um desafio claro e um artefato esperado. "
                "Oriente-o a organizar um plano de trabalho, investigar referências e focar em entregas tangíveis."
            ),
        },
        "eduscrum": {
            "titulo": "EduScrum",
            "objetivo": "Trabalho cocriativo, com autonomia, entregas incrementais e responsabilidade ativa.",
            "prompt": (
                "Você atua como um Scrum Master educacional aplicando o EduScrum. "
                "Ajude o usuário a planejar ciclos curtos (sprints) e listar o backlog de tarefas. "
                "Foque em transparência, colaboração e feedback contínuo."
            ),
        },
        "roleplay": {
            "titulo": "Roleplay",
            "objetivo": "Desenvolver empatia vivenciando a perspectiva de diferentes atores em um cenário.",
            "prompt": (
                "Você é um facilitador de dinâmicas de Roleplay (Jogos de Papéis). "
                "Apresente dilemas onde o usuário precisa argumentar a partir de um papel específico. "
                "Desafie as decisões do usuário com base no cenário e exija justificativas fundamentadas."
            )
        }
    }

    def __init__(self, db_manager=None):
        self.db = db_manager

        # Configuração do AWS Bedrock conforme especificação
        self.llm = ChatBedrock(
            model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            region_name="us-east-1",
            model_kwargs={
                "temperature": 0.1,
                "max_tokens": 4096
            }
        )

    def list_methodologies(self) -> list:
        """Retorna os metadados de todas as metodologias disponíveis."""
        return [
            {"id": key, "titulo": value["titulo"], "objetivo": value["objetivo"]}
            for key, value in self.METHODOLOGY_PROMPTS.items()
        ]

    def get_methodology(self, methodology_id: str) -> Dict[str, str]:
        """Retorna a configuração da metodologia, com fallback para Design Thinking."""
        return self.METHODOLOGY_PROMPTS.get(methodology_id, self.METHODOLOGY_PROMPTS["design_thinking"])

    def process_interaction(self, methodology_id: str, current_step: str, user_input: str) -> str:
        """Processa a interação roteando para o LLM."""
        methodology = self.get_methodology(methodology_id)
        return self._call_llm(methodology, current_step, user_input)

    def _call_llm(self, methodology: Dict[str, str], current_step: str, user_input: str) -> str:
        """Envia o contexto e a entrada do usuário para o Claude no AWS Bedrock."""

        system_content = (
            f"{methodology['prompt']}\n\n"
            f"Lembre-se: você é o agente 'inove4us'. "
            f"O usuário está atualmente na fase/passo: '{current_step}'. "
            "Responda de forma concisa, direta e sempre termine com uma reflexão ou pergunta "
            "que conduza o usuário ao próximo estágio do seu raciocínio."
        )

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_input)
        ]

        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            print(f"Erro ao acessar AWS Bedrock: {e}")
            return "Desculpe, ocorreu um erro de conexão com o agente de inovação no momento. Tente novamente."
