# IA assistiva via Bedrock

Ciclo de origem: CURSOR-008.

Claude é acessado pelo Bedrock Runtime, operação `Converse`, através da porta `ModelGateway`. Região e modelo vêm de configuração (`BEDROCK_REGION` / `AWS_REGION`, `BEDROCK_MODEL_ID`). Credenciais usam a cadeia padrão da AWS. `.env.example` não declara access key.

A IA produz propostas estruturadas e citadas. Não calcula oficialmente, não publica, não aprova e não decide conformidade. Materialização cria somente novo `draft` após revisão humana.

O Guardrail do Bedrock é defesa adicional e **continua pendente de identificador**.
