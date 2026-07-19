import os
import boto3
import psycopg2
from dotenv import load_dotenv

# Carrega variáveis do .env local
load_dotenv()

print("--- DIAGNÓSTICO DE AMBIENTE LOCAL ---\n")

# 1. TESTE DE BANCO DE DADOS
print(f"1. Testando conexão com Banco de Dados ({os.getenv('DB_HOST')})...")
try:
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM ctdi_matu WHERE status_ia = 'PENDENTE'")
    pendentes = cur.fetchone()[0]
    print(f"   ✅ SUCESSO! Conectado. Há {pendentes} diagnósticos PENDENTES na fila.")
    conn.close()
except Exception as e:
    print(f"   ❌ FALHA NO BANCO: {e}")
    print("   -> DICA: Verifique se o Security Group do RDS na AWS permite o IP da sua casa na porta 5432.")

print("\n--------------------------------------------------\n")

# 2. TESTE DE IA (BEDROCK)
print("2. Testando credenciais AWS Bedrock...")
try:
    # Tenta criar o cliente usando as variáveis de ambiente ou ~/.aws/credentials
    bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name='us-east-2'  # Ajuste se sua região for outra
    )

    # Teste simples de invocação
    print("   -> Invocando Claude 3 Sonnet para teste simples...")
    body = '{"anthropic_version": "bedrock-2023-05-31", "max_tokens": 10, "messages": [{"role": "user", "content": "Oi"}]}'

    response = bedrock.invoke_model(
        modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        body=body
    )
    print("   ✅ SUCESSO! Bedrock respondeu.")
except Exception as e:
    print(f"   ❌ FALHA NA IA: {e}")
    print("   -> DICA: Localmente, você precisa definir AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY no .env.")

print("\n--- FIM DO DIAGNÓSTICO ---")