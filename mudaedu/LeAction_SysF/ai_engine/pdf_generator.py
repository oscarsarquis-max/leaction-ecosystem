from fpdf import FPDF
import datetime
import os


class LeActionPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(40, 70, 140)
        self.cell(0, 10, 'LeActionF - Diagnóstico de Maturidade Estratégica', 0, 1, 'C')
        self.set_draw_color(200, 200, 200)
        self.line(10, 20, 200, 20)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        data_atual = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        self.cell(0, 10, f'Relatório Gerado em {data_atual} | Página {self.page_no()}', 0, 0, 'C')


def gerar_pdf_final(report_data, texto_ia):
    pdf = LeActionPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- TRATAMENTO DE SEGURANÇA PARA VALORES NULOS ---
    # Usamos .get() com valor padrão para evitar NoneType
    presente = report_data.get('pgen_presente') or 0.0
    futuro = report_data.get('pgen_futuro') or 0.0
    gap = report_data.get('pgen_gap') or 0.0

    nome_exibicao = report_data.get('nome_clie_text') or f"ID Cliente: {report_data.get('id_clie', 'N/A')}"
    email_exibicao = report_data.get('mail_clie_text') or "Não informado"
    id_matu = report_data.get('id_matu', 'S/N')

    # 1. Identificação
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Diagnóstico: {nome_exibicao}", 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"ID do Relatório: {id_matu}", 0, 1)
    pdf.cell(0, 6, f"E-mail: {email_exibicao}", 0, 1)
    pdf.ln(10)

    # 2. Resumo de Scores
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, ' 1. Panorama de Maturidade', 0, 1, 'L', fill=True)
    pdf.ln(2)
    pdf.set_font('Arial', '', 11)

    # Conversão segura para float
    pdf.cell(0, 8, f"- Score Geral Presente: {float(presente):.2f}", 0, 1)
    pdf.cell(0, 8, f"- Score Geral Futuro: {float(futuro):.2f}", 0, 1)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, f"- Gap de Transformação: {float(gap):.2f}", 0, 1)
    pdf.ln(5)

    # 3. Movimento Principal
    mov = report_data.get('movimento_principal') or {}
    if mov:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f"Movimento: {mov.get('nome', 'N/A')}", 0, 1)
        pdf.set_font('Arial', 'I', 10)
        desc = mov.get('estagio_descricao') or 'Descrição não disponível.'
        pdf.multi_cell(0, 6, str(desc).encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(10)

    # 4. O DIAGNÓSTICO DA IA
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(220, 230, 241)
    pdf.cell(0, 10, ' 2. Análise Consultiva LeActionF (IA)', 0, 1, 'L', fill=True)
    pdf.ln(4)
    pdf.set_font('Arial', '', 11)

    texto_seguro = str(texto_ia).encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, texto_seguro)

    # 5. Próximos Passos
    suggestions = report_data.get('suggestions')
    if suggestions and isinstance(suggestions, list):
        pdf.add_page()
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, ' 3. Prioridades de Implementação (Roadmap)', 0, 1, 'L', fill=True)
        pdf.ln(5)

        for sugg in suggestions[:5]:
            pdf.set_font('Arial', 'B', 10)
            pdf.set_text_color(40, 70, 140)
            dom_nome = sugg.get('dominio_nome', 'Domínio')
            gap_val = sugg.get('gap_dom') or 0.0
            pdf.cell(0, 8, f"> {dom_nome} | Gap: {float(gap_val):.2f}", 0, 1)

            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', '', 9)
            blocos_list = sugg.get('blocos_sugeridos', [])
            blocos = ", ".join([str(b.get('nome', '')) for b in blocos_list])
            pdf.multi_cell(0, 5, f"Entregáveis sugeridos: {blocos}")
            pdf.ln(4)

    # Caminho do arquivo (Ajustado para Windows se necessário, ou mantendo /tmp para Linux/Fargate)
    filename = f"diagnostico_{id_matu}.pdf"
    output_path = os.path.join(os.getcwd(), filename)  # Salva na pasta atual do projeto

    pdf.output(output_path)
    return output_path