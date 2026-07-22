"""
MAtivas - Worker assíncrono de IA
=================================================================
Consome tarefas da tabela `roteiros` (status = 'Pendente'), invoca o
Amazon Bedrock (Claude via LangChain) para gerar o roteiro de aulas a
partir do desafio vinculado, persiste o resultado em `passos_json`,
atualiza o status para 'Concluido' e registra a interação em
`historico_interacoes_ia`.

Execução:
    cd services
    python ai_worker.py

Requer credenciais AWS configuradas no ambiente (AWS_ACCESS_KEY_ID,
AWS_SECRET_ACCESS_KEY / perfil) com acesso ao Amazon Bedrock.
"""

import os
import re
import json
import time
import logging
import sys

import psycopg2
from psycopg2.extras import RealDictCursor, Json

import boto3
import urllib3
from langchain_aws import ChatBedrock
from langchain_core.messages import SystemMessage, HumanMessage

from guardrails import build_guardrails_prompt

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from biblioteca_passos import (
    formatar_passos_para_prompt,
    obter_passos_biblioteca,
    passos_canonicos_para_roteiro,
)

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mativas.ai_worker")

# ---------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "dbname": os.environ.get("DB_NAME", "MAtivas"),
    "user": os.environ.get("DB_USER") or os.environ.get("DB_USERNAME") or "postgres",
    "password": os.environ.get("DB_PASSWORD") or os.environ.get("DB_PASS") or "Cmgv6190!@",
    # Espelha o backend: disable no local, require/verify-full na AWS.
    "sslmode": os.environ.get("DB_SSLMODE", "disable"),
}

MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
AWS_REGION = "us-east-1"
INTERVALO_POLLING = 5  # segundos

# O prompt do sistema é montado em tempo de execução injetando a base de
# conhecimento (tabela `problema_mativa`) no marcador {base_conhecimento}.
# As chaves literais do JSON de exemplo são duplicadas ({{ }}) por causa do
# str.format().
SYSTEM_PROMPT_TEMPLATE = (
    "Você é um especialista em Metodologias Inov-ativas na Educação, com base "
    "exclusiva na obra de Andrea Filatro.\n\n"
    "{guardrails}"
    "Use a BASE DE CONHECIMENTO abaixo (Ground Truth) como ÚNICA fonte de "
    "verdade. Ela lista as metodologias disponíveis e suas características.\n\n"
    "=== BASE DE CONHECIMENTO (JSON) ===\n"
    "{base_conhecimento}\n"
    "=== FIM DA BASE DE CONHECIMENTO ===\n\n"
    "Siga OBRIGATORIAMENTE as duas fases a seguir.\n\n"
    "FASE 1 — DIAGNÓSTICO:\n"
    "1. Leia com atenção o desafio relatado pelo professor.\n"
    "2. Compare o relato com cada metodologia da base de conhecimento.\n"
    "3. Escolha UMA única metodologia, baseando-se ESTRITAMENTE no cruzamento "
    "do relato com os campos 'problemas_combinados' e "
    "'observacao_automatizacao'. NÃO invente metodologias fora da base: o valor "
    "retornado em \"metodologia\" deve ser exatamente igual ao campo "
    "'metodologia' do registro mais aderente.\n\n"
    "FASE 2 — PLANEJAMENTO:\n"
    "1. Elabore os passos do roteiro para a metodologia escolhida.\n"
    "2. A linguagem, os exemplos e as dinâmicas DEVEM respeitar o "
    "'publico_preferencial' e a 'modalidade_preferencial' indicados para a "
    "metodologia escolhida na base de conhecimento.\n"
    "3. O desafio relatado pelo professor orienta a ESCOLHA da metodologia, mas "
    "NÃO deve se tornar o objeto de aprendizagem nem o tema central da atividade. "
    "Proponha um problema ou situação pedagógica AMPLO, para que o professor "
    "possa aplicar o roteiro com o conteúdo/tema que desejar.\n"
    "4. Evite repetir literalmente o desafio do professor como 'problema da "
    "atividade'. Use formulações genéricas e transferíveis.\n\n"
    "FASE 3 — JUSTIFICATIVA:\n"
    "Gere uma justificativa no formato: \"A [metodologia] faz parte das [grupo] e é "
    "indicada quando [situação pedagógica]\", usando o grupo da metodologia escolhida "
    "e a frase de 'problemas_combinados' mais próxima do relato do professor.\n\n"
    "FASE 4 — PASSO A PASSO:\n"
    "1. Se houver BIBLIOTECA DE PASSOS no prompt: copie LITERALMENTE cada "
    "\"imperativo\" em \"titulo\" e cada \"descricao_base\" em \"descricao\" — "
    "sem resumir, adaptar, omitir frases ou reescrever. Apenas estime \"tempo\".\n"
    "2. Se NÃO houver biblioteca: elabore de 5 a 8 passos com \"titulo\" em "
    "imperativo e \"descricao\" alinhada à obra de Andrea Filatro.\n"
    "3. Inclua \"tempo\" estimado por passo.\n\n"
    "FORMATO DE SAÍDA (CONTRATO OBRIGATÓRIO):\n"
    "Responda ESTRITAMENTE em JSON válido, sem texto antes ou depois, sem "
    "blocos de código markdown. A estrutura deve ser EXATAMENTE:\n"
    "{{\n"
    '  "metodologia": "<nome exato da metodologia escolhida na base>",\n'
    '  "justificativa": "<A [metodologia] faz parte das [grupo] e é indicada quando ...>",\n'
    '  "passos": [\n'
    '    {{"titulo": "<imperativo canônico ou inventado>", "descricao": "<texto literal da biblioteca ou elaborado>", "tempo": "<ex: 10 min>"}}\n'
    "  ]\n"
    "}}\n\n"
    "O array \"passos\" deve conter todos os passos da biblioteca da metodologia, "
    "na mesma ordem, com texto idêntico. Se não houver biblioteca, elabore de 5 a 8 passos."
)


# Prompt para quando a metodologia JÁ FOI escolhida no diagnóstico rápido
# (lock-in). A IA não reescolhe; com biblioteca, só estima tempos (textos são
# impostos no pós-processamento a partir da biblioteca canônica).
SYSTEM_PROMPT_PLANEJAMENTO_TEMPLATE = (
    "Você é um especialista em Metodologias Inov-ativas na Educação, com base "
    "exclusiva na obra de Andrea Filatro.\n\n"
    "{guardrails}"
    "A metodologia JÁ FOI ESCOLHIDA para este desafio: \"{metodologia}\". "
    "NÃO escolha nem sugira outra metodologia — trabalhe SOMENTE com esta.\n\n"
    "Use a BASE DE CONHECIMENTO abaixo para localizar a metodologia escolhida "
    "e respeitar o 'publico_preferencial' e a 'modalidade_preferencial' "
    "indicados para ela.\n\n"
    "=== BASE DE CONHECIMENTO (JSON) ===\n"
    "{base_conhecimento}\n"
    "=== FIM DA BASE DE CONHECIMENTO ===\n\n"
    "{biblioteca_bloco}"
    "Elabore o PASSO A PASSO do roteiro de aula para a metodologia "
    "\"{metodologia}\".\n\n"
    "REGRAS DO PASSO A PASSO:\n"
    "1. Se houver BIBLIOTECA DE PASSOS acima: copie LITERALMENTE cada "
    "\"imperativo\" em \"titulo\" e cada \"descricao_base\" em \"descricao\" — "
    "proibido resumir, parafrasear, omitir trechos ou reordenar.\n"
    "2. Sua única liberdade com a biblioteca é estimar \"tempo\" por passo.\n"
    "3. Se NÃO houver biblioteca: elabore de 5 a 8 passos alinhados à obra.\n"
    "4. NÃO invente passos extras nem omita passos da biblioteca.\n\n"
    "REGRA PEDAGÓGICA: o desafio relatado orienta a metodologia, mas NÃO deve "
    "virar o tema/objeto da atividade. Não repita literalmente o desafio como "
    "problema da atividade.\n\n"
    "FORMATO DE SAÍDA (CONTRATO OBRIGATÓRIO):\n"
    "Responda ESTRITAMENTE em JSON válido, sem texto antes ou depois, sem "
    "blocos de código markdown. A estrutura deve ser EXATAMENTE:\n"
    "{{\n"
    '  "passos": [\n'
    '    {{"titulo": "<texto literal do imperativo>", "descricao": "<texto literal da descricao_base>", "tempo": "<ex: 10 min>"}}\n'
    "  ]\n"
    "}}\n\n"
    "{instrucao_quantidade_passos}"
)


# ---------------------------------------------------------------------
# Gerenciador de conexões
# ---------------------------------------------------------------------
class DatabaseManager:
    """Encapsula a abertura de conexões com o PostgreSQL."""

    def __init__(self, config=None):
        self.config = config or DB_CONFIG

    def get_connection(self):
        return psycopg2.connect(**self.config)


# ---------------------------------------------------------------------
# Processador de IA
# ---------------------------------------------------------------------
class LeActionAIProcessor:
    def __init__(self, db_manager):
        self.db = db_manager
        # Cache em memória da base de conhecimento (problema_mativa). A tabela
        # muda raramente, então carregamos uma vez e reaproveitamos.
        self._base_conhecimento_texto = None
        self._base_conhecimento_qtd = 0

        # Contingência de SSL: desativa a validação de certificado no
        # ambiente de desenvolvimento local (Cursor). O bypass é feito no
        # cliente nativo do boto3, repassado ao LangChain.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name="us-east-1",
            verify=False,
        )

        self.llm = ChatBedrock(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
            model_kwargs={"temperature": 0.1, "max_tokens": 4096},
            client=bedrock_client,
        )

    # ----- Base de conhecimento (Ground Truth) -----------------------
    @staticmethod
    def formatar_base_conhecimento(registros):
        """Converte as linhas de problema_mativa em um JSON estruturado
        pronto para ser injetado no prompt do sistema."""
        base = []
        for r in registros:
            base.append(
                {
                    "metodologia": r.get("metodologia"),
                    "grupo": r.get("grupo"),
                    "problemas_combinados": r.get("problemas_combinados"),
                    "observacao_automatizacao": r.get("observacao_automatizacao"),
                    "publico_preferencial": r.get("publico_preferencial"),
                    "publico_complementar": r.get("publico_complementar"),
                    "modalidade_preferencial": r.get("modalidade_preferencial"),
                    "modalidades_alternativas": r.get("modalidades_alternativas"),
                }
            )
        return json.dumps(base, ensure_ascii=False, indent=2)

    def get_base_conhecimento(self):
        """Retorna a base de conhecimento formatada, carregando-a do banco
        na primeira chamada e mantendo em cache nas seguintes."""
        if self._base_conhecimento_texto is None:
            try:
                registros = buscar_base_conhecimento(self.db)
                self._base_conhecimento_qtd = len(registros)
                self._base_conhecimento_texto = self.formatar_base_conhecimento(registros)
                logger.info(
                    "Base de conhecimento carregada: %d metodologia(s) de problema_mativa.",
                    self._base_conhecimento_qtd,
                )
            except Exception:
                logger.exception(
                    "Falha ao carregar a base de conhecimento (problema_mativa)."
                )
                # Fallback seguro: prompt segue funcionando sem Ground Truth.
                self._base_conhecimento_texto = "[]"
        return self._base_conhecimento_texto

    # ----- Montagem do prompt do usuário -----------------------------
    @staticmethod
    def montar_prompt_usuario(desafio):
        partes = []
        if desafio.get("conteudo_desafio"):
            partes.append(f"Desafio relatado: {desafio['conteudo_desafio']}")
        if desafio.get("opcoes_selecionadas"):
            partes.append(f"Dificuldades apontadas: {desafio['opcoes_selecionadas']}")
        if desafio.get("nivel_ensino"):
            partes.append(f"Nível de ensino: {desafio['nivel_ensino']}")
        if desafio.get("formato_aula"):
            partes.append(f"Formato da aula: {desafio['formato_aula']}")
        if desafio.get("qtd_participantes"):
            partes.append(f"Quantidade de participantes: {desafio['qtd_participantes']}")
        if desafio.get("sintese"):
            partes.append(f"Síntese: {desafio['sintese']}")
        if not partes:
            partes.append("Desafio genérico de engajamento e participação dos alunos.")
        return "\n".join(partes)

    # ----- Extração robusta do JSON da resposta ----------------------
    @staticmethod
    def extrair_json(texto):
        try:
            return json.loads(texto)
        except (json.JSONDecodeError, TypeError):
            pass
        # tenta localizar o primeiro objeto JSON dentro do texto
        match = re.search(r"\{.*\}", texto or "", re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("Resposta da IA não contém JSON válido.")

    @staticmethod
    def montar_bloco_biblioteca(metodologia: str) -> tuple[str, str, list | None]:
        """Retorna (bloco_prompt, instrucao_qtd, passos_canonicos)."""
        canonicos = obter_passos_biblioteca(metodologia)
        if not canonicos:
            bloco = (
                "=== BIBLIOTECA DE PASSOS ===\n"
                "Não há passos canônicos cadastrados para esta metodologia.\n"
                "Elabore de 5 a 8 passos com \"titulo\" em imperativo e "
                "\"descricao\" adaptada ao contexto.\n"
                "=== FIM DA BIBLIOTECA DE PASSOS ===\n\n"
            )
            instrucao = (
                'O array "passos" deve conter de 5 a 8 passos, com "titulo" em '
                "imperativo e descrições adaptadas ao contexto informado."
            )
            return bloco, instrucao, None

        qtd = len(canonicos)
        bloco = (
            "=== BIBLIOTECA DE PASSOS (FONTE DE VERDADE — copie titulo E descricao "
            "LITERALMENTE; não resuma) ===\n"
            f"{formatar_passos_para_prompt(canonicos)}\n"
            "=== FIM DA BIBLIOTECA DE PASSOS ===\n\n"
        )
        instrucao = (
            f'O array "passos" deve conter EXATAMENTE {qtd} passos, na mesma ordem '
            "da biblioteca, com titulo=imperativo e descricao=descricao_base "
            "caractere a caractere (apenas \"tempo\" pode ser estimado)."
        )
        return bloco, instrucao, canonicos

    # ----- Invocação do modelo ---------------------------------------
    def gerar_roteiro(self, desafio):
        prompt_usuario = self.montar_prompt_usuario(desafio)

        # Lock-in: se o diagnóstico já escolheu a metodologia, a IA apenas
        # elabora os passos; a metodologia e a justificativa são mantidas.
        metodologia_fixada = (desafio.get("metodologia_recomendada") or "").strip()
        justificativa_fixada = (desafio.get("justificativa") or "").strip()

        guardrails = build_guardrails_prompt()
        biblioteca_bloco = ""
        instrucao_qtd = ""
        passos_canonicos = None

        if metodologia_fixada:
            biblioteca_bloco, instrucao_qtd, passos_canonicos = self.montar_bloco_biblioteca(
                metodologia_fixada
            )
            prompt_sistema = SYSTEM_PROMPT_PLANEJAMENTO_TEMPLATE.format(
                guardrails=guardrails,
                base_conhecimento=self.get_base_conhecimento(),
                metodologia=metodologia_fixada,
                biblioteca_bloco=biblioteca_bloco,
                instrucao_quantidade_passos=instrucao_qtd,
            )
        else:
            prompt_sistema = SYSTEM_PROMPT_TEMPLATE.format(
                guardrails=guardrails,
                base_conhecimento=self.get_base_conhecimento(),
            )

        mensagens = [
            SystemMessage(content=prompt_sistema),
            HumanMessage(content=prompt_usuario),
        ]

        resposta = self.llm.invoke(mensagens)
        conteudo = resposta.content if hasattr(resposta, "content") else str(resposta)

        dados = self.extrair_json(conteudo)
        passos = dados.get("passos", [])

        if metodologia_fixada:
            metodologia = metodologia_fixada
            justificativa = justificativa_fixada or (dados.get("justificativa") or "").strip()
        else:
            metodologia = dados.get("metodologia", "Aprendizagem Colaborativa")
            justificativa = (dados.get("justificativa") or "").strip()
            _, _, passos_canonicos = self.montar_bloco_biblioteca(metodologia)

        # Pós-processamento obrigatório: com biblioteca, título+descrição literais.
        # Cobre também nomes com sufixo (ex.: "... (PBL)") via obter_passos_biblioteca.
        if not passos_canonicos:
            passos_canonicos = obter_passos_biblioteca(metodologia)
        if passos_canonicos:
            passos = passos_canonicos_para_roteiro(passos_canonicos, passos)

        usage = getattr(resposta, "usage_metadata", None) or {}
        tokens_prompt = usage.get("input_tokens", 0) or 0
        tokens_resposta = usage.get("output_tokens", 0) or 0

        return {
            "metodologia": metodologia,
            "justificativa": justificativa,
            "passos": passos,
            "prompt_sistema": prompt_sistema,
            "prompt_usuario": prompt_usuario,
            "conteudo_bruto": conteudo,
            "tokens_prompt": tokens_prompt,
            "tokens_resposta": tokens_resposta,
        }


# ---------------------------------------------------------------------
# Reserva de roteiros e envio de e-mail (evita duplicidade)
# ---------------------------------------------------------------------
def _reservar_roteiro(db, roteiro_id) -> bool:
    """Marca o roteiro como Processando de forma atômica."""
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE roteiros
                      SET status = 'Processando',
                          processando_desde = CURRENT_TIMESTAMP
                    WHERE id = %s AND status = 'Pendente'
                RETURNING id""",
                (roteiro_id,),
            )
            reservado = cur.fetchone() is not None
        conn.commit()
        return reservado
    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Falha ao reservar roteiro id=%s.", roteiro_id)
        return False
    finally:
        if conn:
            conn.close()


def recuperar_roteiros_travados(db) -> None:
    """Devolve roteiros presos em Processando para a fila após timeout."""
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE roteiros
                      SET status = 'Pendente',
                          processando_desde = NULL
                    WHERE status = 'Processando'
                      AND processando_desde IS NOT NULL
                      AND processando_desde < CURRENT_TIMESTAMP - INTERVAL '20 minutes'"""
            )
            if cur.rowcount:
                logger.warning(
                    "%d roteiro(s) em Processando há mais de 20 min voltaram para Pendente.",
                    cur.rowcount,
                )
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Falha ao recuperar roteiros travados.")
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------
# Processamento de um único roteiro pendente (transação isolada)
# ---------------------------------------------------------------------
def processar_roteiro(processor, db, registro):
    roteiro_id = registro["roteiro_id"]
    professor_id = registro.get("professor_id")

    if not _reservar_roteiro(db, roteiro_id):
        logger.info("Roteiro id=%s já reservado por outro worker; ignorando.", roteiro_id)
        return

    logger.info("Processando roteiro pendente id=%s ...", roteiro_id)

    conn = None
    try:
        resultado = processor.gerar_roteiro(registro)

        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE roteiros
                       SET passos_json = %s,
                           metodologia_recomendada = %s,
                           justificativa = %s,
                           status = 'Concluido'
                   WHERE id = %s AND status = 'Processando'""",
                (
                    Json(resultado["passos"]),
                    resultado["metodologia"],
                    resultado["justificativa"],
                    roteiro_id,
                ),
            )
            cur.execute(
                """INSERT INTO historico_interacoes_ia
                       (professor_id, tipo_acao, prompt_sistema, prompt_usuario,
                        resposta_ia, modelo_ia, tokens_prompt, tokens_resposta)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    professor_id,
                    "gerar_roteiro",
                    resultado["prompt_sistema"],
                    resultado["prompt_usuario"],
                    resultado["conteudo_bruto"],
                    MODEL_ID,
                    resultado["tokens_prompt"],
                    resultado["tokens_resposta"],
                ),
            )
        conn.commit()
        logger.info("Roteiro id=%s concluído com sucesso.", roteiro_id)

        try:
            from email_service import send_roteiro_email

            desafio_txt = registro.get("conteudo_desafio") or registro.get("sintese") or ""
            if registro.get("opcoes_selecionadas"):
                desafio_txt = f"{desafio_txt} ({registro['opcoes_selecionadas']})".strip()

            email_prof = (registro.get("professor_email") or "").strip()
            if email_prof:
                roteiro_content = {
                    "nome": registro.get("professor_nome"),
                    "metodologia": resultado["metodologia"],
                    "justificativa": resultado["justificativa"],
                    "passos": resultado["passos"],
                    "contexto": {
                        "desafio": desafio_txt.strip(),
                        "nivel": registro.get("nivel_ensino"),
                        "formato": registro.get("formato_aula"),
                        "participantes": registro.get("qtd_participantes"),
                    },
                }
                resultado_email = send_roteiro_email(
                    email_prof,
                    roteiro_content,
                    roteiro_id,
                    modo="automatico",
                )
                if resultado_email.get("skipped"):
                    logger.info(
                        "Envio automático ignorado para roteiro id=%s (%s).",
                        roteiro_id,
                        resultado_email.get("motivo"),
                    )
                else:
                    logger.info("E-mail do roteiro id=%s enviado para %s.", roteiro_id, email_prof)
            else:
                logger.warning(
                    "Roteiro id=%s sem e-mail do professor; envio automático ignorado.",
                    roteiro_id,
                )
        except Exception:
            logger.exception("Falha ao enviar e-mail do roteiro id=%s.", roteiro_id)

    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Falha ao processar roteiro id=%s. Marcando como 'Erro'.", roteiro_id)
        _marcar_erro(db, roteiro_id)
    finally:
        if conn:
            conn.close()


def _marcar_erro(db, roteiro_id):
    """Marca o roteiro como 'Erro' para evitar reprocessamento infinito."""
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE roteiros SET status = 'Erro' WHERE id = %s", (roteiro_id,)
            )
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Não foi possível marcar o roteiro id=%s como 'Erro'.", roteiro_id)
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------
# Base de conhecimento (Ground Truth) - tabela problema_mativa
# ---------------------------------------------------------------------
def buscar_base_conhecimento(db):
    """Retorna todos os registros da tabela problema_mativa."""
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT id,
                          metodologia,
                          grupo,
                          problemas_combinados,
                          observacao_automatizacao,
                          publico_preferencial,
                          publico_complementar,
                          modalidade_preferencial,
                          modalidades_alternativas
                     FROM problema_mativa
                 ORDER BY id ASC"""
            )
            return cur.fetchall()
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------
# Busca de tarefas pendentes
# ---------------------------------------------------------------------
def buscar_pendentes(db):
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT r.id              AS roteiro_id,
                          r.metodologia_recomendada,
                          r.justificativa,
                          d.professor_id    AS professor_id,
                          p.nome            AS professor_nome,
                          p.email           AS professor_email,
                          d.conteudo_desafio,
                          d.opcoes_selecionadas,
                          d.nivel_ensino,
                          d.formato_aula,
                          d.qtd_participantes,
                          d.sintese
                     FROM roteiros r
                     JOIN desafios d ON d.id = r.desafio_id
                     JOIN professores p ON p.id = d.professor_id
                    WHERE r.status = 'Pendente'
                 ORDER BY r.id ASC"""
            )
            return cur.fetchall()
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------
def main():
    logger.info("Iniciando AI Worker (modelo=%s, região=%s)", MODEL_ID, AWS_REGION)
    db = DatabaseManager()
    processor = LeActionAIProcessor(db)
    # Pré-aquece o cache da base de conhecimento (Ground Truth) no startup.
    processor.get_base_conhecimento()

    while True:
        try:
            recuperar_roteiros_travados(db)
            pendentes = buscar_pendentes(db)
            if pendentes:
                logger.info("%d roteiro(s) pendente(s) encontrado(s).", len(pendentes))
            for registro in pendentes:
                processar_roteiro(processor, db, registro)
        except Exception:
            logger.exception("Erro inesperado no ciclo do worker.")

        time.sleep(INTERVALO_POLLING)


if __name__ == "__main__":
    main()
