import os
import traceback
import psycopg2.extras
from langchain_aws import ChatBedrock
from ai_engine.s3_helper import upload_to_s3
from ai_engine.pdf_generator import gerar_pdf_final
from datetime import datetime


class LeActionAIProcessor:
    def __init__(self, db_manager):
        self.db = db_manager
        self.llm = ChatBedrock(
            # Parâmetros originais preservados conforme diretriz
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
            model_kwargs={
                "temperature": 0.1,
                "max_tokens": 4096
            }
        )

    def extrair_diretrizes_contexto(self, maturity):
        diretrizes = []

        # 1. Dados Geográficos e de Porte
        sede = maturity.get('localizacao_sede') or "Não informada"
        alunos = maturity.get('qtd_alunos') or 0
        e_rede = maturity.get('rede_ensino') in [True, 1, 'true', 'True']

        # 2. Segmento de Ensino (Foco Brasil - BNCC/PNED)
        tipo = maturity.get('tipo_ensino') or "K12"

        if tipo == 'K12':
            diretrizes.append("- SEGMENTO: Educação Básica (K12). Foco em BNCC, PNED e segurança digital para menores.")
        elif tipo == 'Superior':
            diretrizes.append(
                "- SEGMENTO: Ensino Superior. Foco em LMS robusto, retenção de alunos e preparação para o mercado.")
        elif tipo == 'Tecnico':
            diretrizes.append(
                "- SEGMENTO: Ensino Técnico/Profissionalizante. Foco em laboratórios virtuais e simulações práticas.")
        elif tipo == 'Idiomas/Cursos Livres':
            diretrizes.append(
                "- SEGMENTO: Idiomas/Cursos Livres. Foco em experiência do cliente (UX) e conversão digital.")
        elif tipo == 'Educação Corporativa':
            diretrizes.append(
                "- SEGMENTO: Educação Corporativa. Foco em microlearning e desenvolvimento de competências (SKAs).")

        # Consolidação do Perfil
        diretrizes.append(f"- LOCALIZAÇÃO (SEDE): {sede}")
        diretrizes.append(f"- PORTE: {alunos} alunos.")
        diretrizes.append(f"- ESTRUTURA: {'Unidade de Rede' if e_rede else 'Unidade Independente'}")

        return "\n".join(diretrizes)

    def obter_rubricas(self, cur, id_matu):
        """
        Recupera as rubricas do PRESENTE, os Vetores Estratégicos dos domínios
        e os insights da Bússola para todos os 9 domínios.
        """
        try:
            query = """
                    SELECT q.id_ques,
                           q.desc_ques,
                           rub.label_rubr,
                           rub.desc_rubr,
                           d.name_doma,
                           d.vetor_estrategico,
                           b.insight_chave
                    FROM ctdi_surv s
                             JOIN ctdi_quest q ON s.id_ques = q.id_ques
                             JOIN public.leaf_doma d ON q.id_doma = d.id_doma
                             JOIN ctdi_rubricas rub ON (s.id_ques = rub.id_ques AND s.grad_ques = rub.grad_rubr)
                             LEFT JOIN ctdi_bussola b ON q.id_ques = b.id_ques
                    WHERE s.id_matu = %s
                      AND q.prefu_ques = 'P'
                    ORDER BY q.id_doma, q.id_ques;
                    """
            cur.execute(query, (id_matu,))
            respostas = cur.fetchall()

            if not respostas:
                return "Rubricas estratégicas não encontradas."

            output = "\n--- STATUS QUALITATIVO DOS 9 DOMÍNIOS (BÚSSOLA) ---\n"
            for r in respostas:
                output += f"DOMÍNIO: {r['name_doma']} | VETOR: {r['vetor_estrategico']}\n"
                output += f"STATUS ATUAL: {r['label_rubr']} - {r['desc_rubr']}\n"
                if r['insight_chave']:
                    output += f"INSIGHT LEACTION (BÚSSOLA): {r['insight_chave']}\n"
                else:
                    output += "INSIGHT LEACTION (BÚSSOLA): Analisar gap técnico conforme vetor.\n"
                output += "-" * 30 + "\n"

            return output

        except Exception as e:
            print(f"❌ [ERRO] Falha ao obter_rubricas: {e}")
            return "Erro técnico ao recuperar detalhes das respostas."

    def obter_entregaveis_roadmap(self, cur, lista_dominios):
        """Busca os nomes dos blocos que comporão as sprints para evitar invenções da IA."""
        try:
            query = """
                    SELECT b.name_bloc, d.name_doma, CAST(dim.id_dime AS INTEGER) as dime_num
                    FROM leaf_bloc b
                             JOIN leaf_doma d ON b.id_doma = d.id_doma
                             JOIN leaf_dime dim ON b.id_dime = dim.id_dime
                    WHERE b.id_doma::text = ANY (%s)
                    ORDER BY dime_num ASC, array_position(%s, b.id_doma::text), b.id_bloc ASC
                    LIMIT 9;
                    """
            cur.execute(query, (lista_dominios, lista_dominios))
            blocos = cur.fetchall()

            output = "\n--- BACKLOG DE ENTREGAS REAIS (9 SPRINTS) ---\n"
            for i, b in enumerate(blocos):
                output += f"Sprint {i + 1}: {b['name_bloc']} (Domínio: {b['name_doma']})\n"
            return output
        except Exception as e:
            return f"Erro ao mapear blocos: {e}"

    def processar_diagnostico(self, conn, id_matu):
        try:
            agora = datetime.now()
            timestamp_geracao = agora.strftime('%d/%m/%Y %H:%M:%S')
            print(f"--- [ID {id_matu}] Iniciando Diagnóstico Estratégico em {timestamp_geracao}...",
                  flush=True)

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # 1. Busca dados da Maturidade e Cliente
                cur.execute("""
                            SELECT m.*,
                                   c.nome_clie,
                                   c.mail_clie,
                                   c.localizacao_sede,
                                   c.qtd_alunos,
                                   c.qtd_colaboradores,
                                   c.rede_ensino,
                                   c.tipo_ensino,
                                   c.clima_organizacional
                            FROM ctdi_matu m
                                     JOIN ctdi_clie c ON m.id_clie = c.id_clie
                            WHERE m.id_matu = %s
                            """, (id_matu,))
                maturity = cur.fetchone()

                if not maturity:
                    print(f"--- [ERRO] Registro id_matu {id_matu} não encontrado.")
                    return False

                # 2. Mapeamento para PDF e Variáveis de Score
                maturity['nome_clie_text'] = maturity.get('nome_clie')
                maturity['mail_clie_text'] = maturity.get('mail_clie') or "Não informado"
                maturity['pgen_presente'] = float(maturity.get('pgen_pres') or 0.0)
                maturity['pgen_futuro'] = float(maturity.get('pgen_fut') or 0.0)
                maturity['pgen_gap'] = float(maturity.get('pgen_gap') or 0.0)

                # Detalhamento literal de Gaps para avaliação da IA
                pdom_gap = maturity.get('pdom_gap') or {}
                detalhamento_gaps = "\n".join([f"- Domínio {d}: Gap de {v}%" for d, v in pdom_gap.items()])

                # 3. Lógica de Priorização
                pdom_sect_gap = maturity.get('pdom_sect_gap') or {}
                fila_1 = sorted([(d, float(v)) for d, v in pdom_sect_gap.items() if float(v) > 0], key=lambda x: x[1],
                                reverse=True)
                dom_prior_setor = [d[0] for d in fila_1]
                fila_2 = sorted(
                    [(d, float(v)) for d, v in pdom_gap.items() if d not in dom_prior_setor and float(v) > 0],
                    key=lambda x: x[1], reverse=True)
                lista_final_prioridade = dom_prior_setor + [d[0] for d in fila_2]

                # 4. Extração de Contexto e Dados Reais do Framework
                contexto_raw = self.extrair_diretrizes_contexto(maturity)
                rubricas_vivas = self.obter_rubricas(cur, id_matu)
                entregaveis_reais = self.obter_entregaveis_roadmap(cur, lista_final_prioridade)

            # 5. Instruções de Especialista
            instrucoes_contexto = f"""
            --- PROTOCOLO DE CONTEÚDO (COBERTURA TOTAL BRASIL) ---
            - TIMESTAMP: Relatório Gerado em {timestamp_geracao}. Exiba na Síntese Executiva.
            - CLIMA: Utilize o relato "{maturity.get('clima_organizacional') or 'Não informado'}" para embasar a síntese.
            - SEÇÃO 1 (SINTESE): Resumo estratégico e Gap Global.
            - SEÇÃO 2 (DOMÍNIOS): Você DEVE analisar NOMINALMENTE os 9 domínios. Use obrigatoriamente o campo 'INSIGHT LEACTION (BÚSSOLA)' para cada um.
            - SEÇÃO 3 (ROADMAP): Use apenas as 9 sprints reais: {entregaveis_reais}. Divida em 3 Ondas.
            - SEÇÃO 4 (REGIONAL): Localização {maturity.get('localizacao_sede')}. Detalhe desafios de conectividade e cultura mobile-first da região.
            - SEÇÃO 5 (PASSOS): Ações práticas de 90 dias preparatórias.
            - REGRAS: SEM recomendações prioritárias fora das seções. SEM sinalizadores [INICIO/FIM] no texto final.
            """

            # 6. Montagem do Prompt Qualificado
            prompt = f"""
            Você é um Consultor Sênior da LeAction. Gere o diagnóstico em Português (Brasil).
            Evite duplicidade. Garanta que todos os 9 domínios sejam tratados com densidade.

            --- DADOS DO SISTEMA ---
            Gerado em: {timestamp_geracao}
            Perfil: {contexto_raw}
            Gaps: {detalhamento_gaps}
            Bússola (9 Domínios): {rubricas_vivas}
            Clima: {maturity.get('clima_organizacional')}
            Entregáveis Reais: {entregaveis_reais}

            {instrucoes_contexto}

            --- TAREFA E FORMATAÇÃO ---
            Utilize as tags exatamente como indicado e preencha o conteúdo:

            [INICIO_VISAO_EXECUTIVA]
            ## Síntese Executiva
            Relatório Gerado em {timestamp_geracao}
            (Analise o Gap Global de {maturity['pgen_gap']:.2f} e o clima organizacional.)
            [FIM_VISAO_EXECUTIVA]

            [INICIO_ANALISE_DOMINIOS]
            ## Diagnóstico dos Domínios
            (Análise técnica INDIVIDUAL dos 9 domínios baseando-se nos Insights da Bússola. Não pule nenhum domínio.)
            [FIM_ANALISE_DOMINIOS]

            [INICIO_ROADMAP_ESTRATEGICO]
            ## Roadmap Estratégico (Ondas 1 a 3)
            (Distribua as 9 sprints reais do Backlog nas 3 ondas.)
            [FIM_ROADMAP_ESTRATEGICO]

            [INICIO_ANALISE_REGIONAL]
            ## Análise Geográfica & Regional
            (Analise o impacto socioeconômico da localização {maturity.get('localizacao_sede')}. Foco em conectividade e hub regional.)
            [FIM_ANALISE_REGIONAL]

            [INICIO_PROXIMOS_PASSOS]
            ## Próximos Passos (90 Dias)
            (Ações práticas para habilitar as Ondas 1, 2 e 3)
            [FIM_PROXIMOS_PASSOS]

            SAÍDA: Markdown profissional em PT-BR. Encerre com ###FIM_TEXTO###.
            """

            # 7. Invocação e Persistência
            resposta = self.llm.invoke(prompt)
            texto_markdown = resposta.content.split("###FIM_TEXTO###")[0].strip()

            path_pdf = gerar_pdf_final(maturity, texto_markdown)
            url_s3 = upload_to_s3(path_pdf, id_matu, maturity.get('id_surv', 0))

            with conn.cursor() as cur:
                cur.execute("""
                            UPDATE ctdi_matu
                            SET txt_diagnostico_ia = %s,
                                url_pdf_ia         = %s,
                                status_ia          = 'CONCLUIDO',
                                dt_fim_ia          = %s
                            WHERE id_matu = %s
                            """, (texto_markdown, url_s3, agora, id_matu))

                self.expandir_roadmap_exaustivo(cur, id_matu, lista_final_prioridade)
                conn.commit()

            if os.path.exists(path_pdf): os.remove(path_pdf)
            return True

        except Exception:
            traceback.print_exc()
            return False

    def expandir_roadmap_exaustivo(self, cur, id_matu, lista_dominios):
        print(f"⚙️ [REPARO CRÍTICO] Forçando Hierarquia por Dimensão (1 a 5)...")

        # 1. CTDI_MAIN
        cur.execute("SELECT id_ctdi FROM ctdi_main WHERE id_matu = %s LIMIT 1", (id_matu,))
        res = cur.fetchone()
        id_ctdi = res[0] if res else None

        if not id_ctdi:
            cur.execute(
                "INSERT INTO ctdi_main (id_matu, id_dime, name_ctdi, stat_ctdi) VALUES (%s, 1, 'Plano de Transformação Digital', 'ativo') RETURNING id_ctdi",
                (id_matu,))
            id_ctdi = cur.fetchone()[0]

        # 2. Limpeza total para evitar "fantasmia" de dados antigos
        cur.execute("DELETE FROM ctdi_itera WHERE id_ctdi = %s", (id_ctdi,))

        # 3. Query com Cast de Inteiro para id_dime
        query_blocos = """
                       SELECT b.id_bloc, b.name_bloc, d.name_doma, CAST(dim.id_dime AS INTEGER) as dime_num
                       FROM leaf_bloc b
                                JOIN leaf_doma d ON b.id_doma = d.id_doma
                                JOIN leaf_dime dim ON b.id_dime = dim.id_dime
                       WHERE b.id_doma::text = ANY (%s)
                       ORDER BY dime_num ASC, \
                                array_position(%s, b.id_doma::text), \
                                b.id_bloc ASC \
                       """
        cur.execute(query_blocos, (lista_dominios, lista_dominios))
        backlog_reorganizado = cur.fetchall()

        if not backlog_reorganizado:
            return

        # 4. Distribuição em Ondas (3 sprints por onda)
        ondas = [backlog_reorganizado[i:i + 3] for i in range(0, len(backlog_reorganizado), 3)]

        for idx, blocos in enumerate(ondas):
            fase = idx + 1
            status_itera = 'ativa' if fase == 1 else 'planejada'

            cur.execute(
                "INSERT INTO ctdi_itera (id_ctdi, id_phase, name_itera, stat_itera) VALUES (%s, %s, %s, %s) RETURNING id_itera",
                (id_ctdi, fase, f"Onda {fase}", status_itera))
            id_itera = cur.fetchone()[0]

            for s_idx, row in enumerate(blocos):
                id_b, nome_b, nome_doma, id_dim = row
                status_sprn = 'ativa' if fase == 1 else 'planejada'

                # 1. Nome único da Squad
                nome_squad_auto = f"CTDI-{id_ctdi} | Squad {nome_b}"

                # 2. Inserção na ctdi_squads
                cur.execute("""
                            INSERT INTO ctdi_squads (nome_squad, id_proj)
                            VALUES (%s, (SELECT id_proj FROM ctdi_projetos WHERE id_ctdi = %s))
                            RETURNING id_squad
                            """, (nome_squad_auto, id_ctdi))

                id_squad_novo = cur.fetchone()[0]

                # 3. Inserção na ctdi_sprn (ADICIONADO RETURNING id_sprn)
                cur.execute("""
                            INSERT INTO ctdi_sprn (id_itera, id_bloc, name_sprn, stat_sprn, ordr_sprn, id_squad)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            RETURNING id_sprn
                            """, (id_itera, id_b, f"[DIM {id_dim}] {nome_b}", status_sprn,
                                  s_idx + 1, id_squad_novo))

                # Agora o fetchone vai funcionar e você terá o ID para a URL do Kanban
                id_sprn = cur.fetchone()[0]

                # 4. Atualização da URL do Kanban
                url_k = f"https://leaction.sys/kanban/{id_sprn}"
                cur.execute("UPDATE ctdi_sprn SET url_kanban = %s WHERE id_sprn = %s", (url_k, id_sprn))

