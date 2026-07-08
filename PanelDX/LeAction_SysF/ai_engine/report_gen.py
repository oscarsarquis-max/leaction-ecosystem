import os
import sys
import boto3
import json
import logging
from requests_aws4auth import AWS4Auth
from opensearchpy import RequestsHttpConnection
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_community.embeddings import BedrockEmbeddings
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate

# --- AJUSTE DE PATH PARA IMPORTAR O DATABASE.PY DA PASTA PAI ---
# Isso garante que funcione no PyCharm e no ambiente de pastas do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from database import LeactionCRUD
except ImportError:
    # Fallback para o ambiente Docker onde os arquivos estarão lado a lado
    from database import LeactionCRUD

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES AWS ---
REGION = "us-east-2"
OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST")
INDEX_NAME = "leactionf-index"


def get_aws_auth():
    """Autenticação SigV4 para acesso seguro aos serviços AWS."""
    credentials = boto3.Session().get_credentials()
    return AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        REGION, 'es',
        session_token=credentials.token
    )


def buscar_contexto_rag(blocos_criticos):
    """Busca no OpenSearch a teoria do LeActionF para os blocos com maior gap."""
    logger.info(f"RAG: Buscando teoria para os blocos: {blocos_criticos}")

    embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", region_name=REGION)
    host_limpo = OPENSEARCH_HOST.replace("https://", "").replace("http://", "")

    vector_db = OpenSearchVectorSearch(
        opensearch_url=f"https://{host_limpo}",
        index_name=INDEX_NAME,
        embedding_function=embeddings,
        http_auth=get_aws_auth(),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    # Query focada nos blocos que precisam de atenção
    query = f"Explicação técnica e importância estratégica dos blocos: {', '.join(blocos_criticos)}"
    docs = vector_db.similarity_search(query, k=3)

    return "\n\n".join([d.page_content for d in docs])


def gerar_texto_ia(dados_cliente, contexto_framework):
    """Interage com o Claude 3 no Bedrock para redigir o diagnóstico final."""

    llm = ChatBedrock(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        region_name=REGION,
        model_kwargs={"temperature": 0.5, "max_tokens": 1500}
    )

    prompt_template = ChatPromptTemplate.from_template("""
    Você é um consultor sênior de estratégia empresarial especialista no Framework LeActionF.
    Seu objetivo é redigir um diagnóstico executivo baseado em dados reais de maturidade.

    CONTEXTO TEÓRICO DO FRAMEWORK (RAG):
    {contexto}

    DADOS DO CLIENTE (NOTAS AS-IS E BENCHMARK DO SETOR):
    {dados}

    DIRETRIZES DE REDAÇÃO:
    1. Escreva EXATAMENTE 2 parágrafos.
    2. Parágrafo 1: Analise o desempenho do cliente frente ao benchmark do setor. Seja direto.
    3. Parágrafo 2: Justifique por que os blocos priorizados são fundamentais para o crescimento, usando a teoria fornecida.
    4. Tom de voz: Profissional, técnico e propositivo.
    5. Finalize com uma seção chamada 'SUGESTÃO DE SPRINTS' com 3 itens curtos.

    RESPOSTA EM PORTUGUÊS:
    """)

    corrente = prompt_template | llm
    resposta = corrente.invoke({
        "contexto": contexto_framework,
        "dados": json.dumps(dados_cliente, indent=2, ensure_ascii=False)
    })

    return resposta.content


def executar_fluxo_diagnostico(id_matu):
    """Função mestre que integra Banco de Dados, Vetores e LLM."""
    try:
        # 1. Instancia o seu CRUD e busca dados do Aurora
        db_manager = LeactionCRUD()
        logger.info(f"Iniciando processo para ID: {id_matu}")

        # Chama o método que criamos no database.py
        dados_diagnostico = db_manager.buscar_dados_para_ia(id_matu)

        if not dados_diagnostico:
            return "Aviso: Não foram encontrados dados de diagnóstico para este ID."

        # 2. Extrai nomes dos blocos para alimentar o RAG
        blocos_para_busca = [item['blc_nome'] for item in dados_diagnostico]

        # 3. Busca Contexto no OpenSearch
        contexto_teorico = buscar_contexto_rag(blocos_para_busca)

        # 4. Gera o Relatório Final
        relatorio_texto = gerar_texto_ia(dados_diagnostico, contexto_teorico)

        return relatorio_texto

    except Exception as e:
        logger.error(f"Erro crítico no fluxo de IA: {str(e)}")
        return f"Desculpe, ocorreu um erro ao gerar o diagnóstico: {str(e)}"

if __name__ == "__main__":
    # Teste rápido de execução (Apenas para validação interna)
    # resultado = executar_fluxo_diagnostico(1)
    # print(resultado)
    pass