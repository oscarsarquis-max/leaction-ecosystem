import os
import sys
import boto3
import logging
from opensearchpy import RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Importações atualizadas
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# --- AJUSTE DE PATH ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuração de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES DE AMBIENTE ---
REGION = os.environ.get("AWS_REGION", "us-east-2")
OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST")
S3_BUCKET = "leactionf-raw-documents-diagnosis-2025"
S3_FILE_KEY = "LeActionF.txt"
INDEX_NAME = "leactionf-index"

def get_aws_auth():
    credentials = boto3.Session().get_credentials()
    return AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        REGION,
        'es',
        session_token=credentials.token
    )

def carregar_texto_s3():
    logger.info(f"Baixando {S3_FILE_KEY} do bucket {S3_BUCKET}...")
    s3 = boto3.client('s3', region_name=REGION)
    response = s3.get_object(Bucket=S3_BUCKET, Key=S3_FILE_KEY)
    return response['Body'].read().decode('utf-8')

def split_hierarquico(texto):
    logger.info("Iniciando divisão hierárquica do documento...")
    separadores = ["\n# ", "\n## ", "\n### ", "\n#### ", "\n\n", "\n"]
    splitter = RecursiveCharacterTextSplitter(
        separators=separadores,
        chunk_size=1200,
        chunk_overlap=150,
        is_separator_regex=False
    )
    chunks = splitter.split_text(texto)
    docs = [Document(page_content=t, metadata={"source": S3_FILE_KEY}) for t in chunks]
    logger.info(f"Documento processado em {len(docs)} pedaços (chunks).")
    return docs

def executar_ingestao():
    try:
        if not OPENSEARCH_HOST:
            raise ValueError("A variável OPENSEARCH_HOST não foi definida.")

        conteudo = carregar_texto_s3()
        documentos = split_hierarquico(conteudo)

        # ARN completo para evitar erro de identificador inválido
        # model_arn = f"arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v1"
        model_id_v2 = "amazon.titan-embed-text-v2:0"

        # --- CORREÇÃO: CLIENTE BEDROCK EXPLÍCITO ---
        logger.info(f"Inicializando Bedrock Runtime em {model_id_v2}...")
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=REGION
        )

        embeddings = BedrockEmbeddings(
            client=bedrock_runtime,
            model_id=model_id_v2
        )
        # ------------------------------------------

        awsauth = get_aws_auth()
        host_limpo = OPENSEARCH_HOST.replace("https://", "").replace("http://", "")

        logger.info(f"Conectando ao OpenSearch e iniciando indexação: {host_limpo}")

        OpenSearchVectorSearch.from_documents(
            documents=documentos,
            embedding=embeddings,
            opensearch_url=f"https://{host_limpo}",
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            index_name=INDEX_NAME,
            engine="faiss",
            space_type="l2"
        )

        logger.info("✅ SUCESSO: O OpenSearch foi populado com o framework LeActionF!")

    except Exception as e:
        logger.error(f"❌ ERRO na ingestão: {str(e)}")
        raise e

if __name__ == "__main__":
    executar_ingestao()