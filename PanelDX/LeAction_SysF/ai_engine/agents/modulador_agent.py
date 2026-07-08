import os
import sys
import re
import io
import json
import psycopg2.extras
import requests
from langchain_aws import ChatBedrock

# Dependência padrão para leitura de fluxos de PDF em memória
try:
    import pypdf
except ImportError:
    pypdf = None  # Correção cirúrgica: atribuição limpa sem a palavra 'import'

from ai_engine.prompts.modulador_templates import obter_prompt_modulador


class LeActionModuladorAgent:
    def __init__(self, db_manager):
        self.db = db_manager
        self.llm = ChatBedrock(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
            model_kwargs={
                "temperature": 0.1,
                "max_tokens": 4096
            }
        )
        print("   [🤖 LLM] ChatBedrock ativado para o Modulador (Claude 3.5 Sonnet).", flush=True)

    def _extrair_texto_de_url_publica(self, url):
        """
        Engine inteligente que intercepta links públicos de visualização,
        converte em download direto e raspa o texto em memória.
        """
        if not url or not url.startswith("http"):
            return "[Aviso: Nenhum link de documento válido foi anexado.]"

        print(f"   [📥 DOWNLOADER] Processando extração da URL: {url}", flush=True)
        download_url = url

        # REFEITÓRIO DE URL: Traduz o link de visualização do Google Drive para link de download direto
        if "drive.google.com" in url:
            match = re.search(r"/file/d/([^/]+)", url)
            if match:
                file_id = match.group(1)
                download_url = f"https://docs.google.com/uc?export=download&id={file_id}"

        try:
            response = requests.get(download_url, timeout=15, allow_redirects=True)
            if response.status_code != 200:
                return f"[Aviso: Não foi possível baixar o arquivo. Status HTTP: {response.status_code}]"

            content_type = response.headers.get('Content-Type', '').lower()
            bytes_stream = io.BytesIO(response.content)

            # PARSER DE PDF
            if "pdf" in content_type or url.lower().endswith(".pdf") or b"%PDF-" in response.content[:10]:
                print("   [📄 PARSER] Identificado formato PDF. Iniciando extração de texto...", flush=True)

                # Trava de segurança: se o pypdf não foi importado no topo, avisa o Claude em vez de quebrar
                if pypdf is None:
                    return "[Aviso: O arquivo é um PDF, mas a biblioteca 'pypdf' não está instalada no ambiente AWS/Docker para realizar a raspagem de texto.]"

                texto_completo = []
                leitor = pypdf.PdfReader(bytes_stream)
                for num_pag, pagina in enumerate(leitor.pages):
                    texto_pag = pagina.extract_text()
                    if texto_pag:
                        texto_completo.append(texto_pag)

                resultado = "\n".join(texto_completo)
                return resultado if resultado.strip() else "[Aviso: O PDF está em branco ou contém apenas imagens escaneadas sem camada de texto/OCR.]"

            # PARSER DE TEXTO SIMPLES / MARKS
            elif "text" in content_type:
                return response.content.decode('utf-8', errors='ignore')

            else:
                return "[Aviso: Formato de arquivo não suportado nativamente pelo parser em memória. Enviado apenas para análise de metadados.]"

        except Exception as err:
            print(f"   ⚠️ [DOWNLOADER ERRO] Falha ao raspar documento: {err}", file=sys.stderr)
            return f"[Aviso: Falha técnica ao tentar acessar o link público da evidência: {str(err)}]"

    def processar_evidencia(self, conn, id_evid):
        print(f"   [🧠 AGENTE] Iniciando esteira de cognição para Evidência ID: {id_evid}", flush=True)

        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

                # --- PASSO 2: EXTRAÇÃO DO DOSSIÊ RELACIONAL ---
                query_contexto = """
                                 SELECT e.id_evid, \
                                        e.id_sprn, \
                                        e.url_evid, \
                                        e.componente_vinculado, \
                                        e.transcricao_audio, \
                                        s.id_bloc, \
                                        s.name_sprn, \
                                        s.desc_sprn, \
                                        s.exec_notes, \
                                        d.id_derv, \
                                        d.name_derv, \
                                        d.derv_comp, \
                                        d.derv_metr, \
                                        d.criteria_dod
                                 FROM public.ctdi_evidencias e
                                          INNER JOIN public.ctdi_sprn s ON e.id_sprn = s.id_sprn
                                          LEFT JOIN public.leaf_derv d ON s.id_bloc = d.id_bloc
                                 WHERE e.id_evid = %s; \
                                 """
                cur.execute(query_contexto, (id_evid,))
                rows = cur.fetchall()

                if not rows:
                    print(f"   ⚠️ [AGENTE] Evidência {id_evid} sem registros correspondentes no banco.", flush=True)
                    return False

                dossie = {
                    "id_evid": rows[0]["id_evid"],
                    "id_sprn": rows[0]["id_sprn"],
                    "url_evid": rows[0]["url_evid"],
                    "componente_vinculado": rows[0]["componente_vinculado"],
                    "transcricao_audio": rows[0]["transcricao_audio"] or "",
                    "name_sprn": rows[0]["name_sprn"],
                    "desc_sprn": rows[0]["desc_sprn"],
                    "exec_notes": rows[0]["exec_notes"] or "",
                    "id_bloc": rows[0]["id_bloc"],
                    "entregaveis_esperados": []
                }

                for row in rows:
                    if row["id_derv"]:
                        dossie["entregaveis_esperados"].append({
                            "id_derv": row["id_derv"],
                            "name_derv": row["name_derv"],
                            "derv_comp": row["derv_comp"],
                            "derv_metr": row["derv_metr"],
                            "criteria_dod": row["criteria_dod"]
                        })

                # --- DISPARO DA EXTRAÇÃO REAL ONLINE ---
                dossie["texto_documento_extraido"] = self._extrair_texto_de_url_publica(dossie["url_evid"])

                # --- PASSO 4: MONTAGEM DO PROMPT E ENVIO AO BEDROCK ---
                prompt_final = obter_prompt_modulador(dossie)

                print(f"   [🚀 BEDROCK] Enviando contexto denso (Dossiê + Documento) ao Claude Sonnet...", flush=True)
                resposta = self.llm.invoke(prompt_final)
                conteudo_bruto = resposta.content.strip()

                # --- PARSER SEGURO ---
                try:
                    if "[INICIO_JSON]" in conteudo_bruto:
                        json_puro = conteudo_bruto.split("[INICIO_JSON]")[1]
                    else:
                        json_puro = conteudo_bruto

                    if "[FIM_JSON]" in json_puro:
                        json_puro = json_puro.split("[FIM_JSON]")[0]

                    payload_validado = json.loads(json_puro.strip())

                except Exception as json_err:
                    print(f"   ❌ [PARSER ERRO] JSON corrompido: {json_err}", file=sys.stderr)
                    payload_validado = {
                        "status_validacao": "REVISÃO_NECESSÁRIA",
                        "feedback_conversacional": "O Modulador encontrou uma inconsistência estrutural no retorno dos indicadores. Por favor, reenvie a evidência.",
                        "error_log": str(json_err)
                    }

                # --- PASSO 3: PERSISTÊNCIA ---
                query_salvamento = """
                                   UPDATE public.ctdi_evidencias
                                   SET analise_ia = %s
                                   WHERE id_evid = %s; \
                                   """
                cur.execute(query_salvamento, (json.dumps(payload_validado, ensure_ascii=False), id_evid))
                print(f"   [💾 AGENTE] Auditoria registrada com sucesso na coluna analise_ia para o ID: {id_evid}",
                      flush=True)

            return True

        except Exception as e:
            print(f"   🚨 [AGENTE ERROR] Falha catastrófica: {str(e)}", file=sys.stderr)
            return False