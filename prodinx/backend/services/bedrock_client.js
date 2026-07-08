const {
  BedrockRuntimeClient,
  InvokeModelCommand,
} = require("@aws-sdk/client-bedrock-runtime");

const BEDROCK_MODEL_ID =
  process.env.BEDROCK_MODEL_ID || "us.anthropic.claude-sonnet-4-20250514-v1:0";
const BEDROCK_REGION = process.env.BEDROCK_REGION || "us-east-1";

function getBedrockClient() {
  return new BedrockRuntimeClient({ region: BEDROCK_REGION });
}

function extrairJsonResposta(texto) {
  if (!texto) {
    throw new Error("Resposta vazia do modelo.");
  }

  const limpo = String(texto).trim();
  const cerca = limpo.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  const conteudo = cerca ? cerca[1].trim() : limpo;

  try {
    return JSON.parse(conteudo);
  } catch {
    const inicio = conteudo.indexOf("{");
    const fim = conteudo.lastIndexOf("}");
    if (inicio !== -1 && fim > inicio) {
      return JSON.parse(conteudo.slice(inicio, fim + 1));
    }
    throw new Error("Não foi possível interpretar o JSON retornado pelo modelo.");
  }
}

async function invocarClaude({
  system,
  userContent,
  maxTokens = 2048,
  temperature = 0.25,
}) {
  const client = getBedrockClient();
  const body = {
    anthropic_version: "bedrock-2023-05-31",
    max_tokens: maxTokens,
    temperature,
    messages: [{ role: "user", content: userContent }],
  };

  if (system) {
    body.system = system;
  }

  const response = await client.send(
    new InvokeModelCommand({
      modelId: BEDROCK_MODEL_ID,
      contentType: "application/json",
      accept: "application/json",
      body: JSON.stringify(body),
    })
  );

  const payload = JSON.parse(Buffer.from(response.body).toString("utf-8"));
  return String(payload.content?.[0]?.text || "").trim();
}

module.exports = {
  BEDROCK_MODEL_ID,
  BEDROCK_REGION,
  extrairJsonResposta,
  invocarClaude,
};
