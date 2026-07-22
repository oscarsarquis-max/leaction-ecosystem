import { jsPDF } from 'jspdf'

/**
 * Relatório PDF de histórico de auditoria (projeto / interação IA).
 */

function criarDoc() {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' })
  const margin = 48
  const larguraUtil = doc.internal.pageSize.getWidth() - margin * 2
  const alturaPagina = doc.internal.pageSize.getHeight()
  let y = margin

  const novaPaginaSeNecessario = (altura) => {
    if (y + altura > alturaPagina - margin) {
      doc.addPage()
      y = margin
    }
  }

  const escreverBloco = (
    texto,
    { size = 11, style = 'normal', cor = [33, 33, 33], espaco = 6 } = {},
  ) => {
    const safe = String(texto ?? '—')
    doc.setFont('helvetica', style)
    doc.setFontSize(size)
    doc.setTextColor(...cor)
    const linhas = doc.splitTextToSize(safe, larguraUtil)
    const alturaLinha = size * 1.35
    linhas.forEach((linha) => {
      novaPaginaSeNecessario(alturaLinha)
      doc.text(linha, margin, y)
      y += alturaLinha
    })
    y += espaco
  }

  return { doc, escreverBloco, getY: () => y }
}

function formatDiagnosticoTexto(item) {
  const partes = [item?.conteudo_desafio, item?.sintese, item?.opcoes_selecionadas].filter(
    Boolean,
  )
  return partes.join(' · ') || '—'
}

function cabecalhoProjeto(escreverBloco, item) {
  escreverBloco('Metodologias Inov-ativas — Relatório de Histórico', {
    size: 16,
    style: 'bold',
    cor: [79, 70, 229],
    espaco: 4,
  })
  escreverBloco(`Projeto #${item?.roteiro_id ?? '—'}`, { size: 12, style: 'bold', espaco: 2 })
  const curtido = Boolean(item?.curtido || item?.curtido_em)
  const curtidaTxt = curtido
    ? `Sim${item?.curtido_em ? ` (${new Date(item.curtido_em).toLocaleString('pt-BR')})` : ''}`
    : 'Não'

  escreverBloco(
    [
      item?.professor_nome && `Professor: ${item.professor_nome}`,
      item?.professor_email && `E-mail: ${item.professor_email}`,
      item?.metodologia_recomendada && `Metodologia: ${item.metodologia_recomendada}`,
      item?.status && `Status: ${item.status}`,
      `Curtida: ${curtidaTxt}`,
    ]
      .filter(Boolean)
      .join(' · ') || '—',
    { size: 10, espaco: 8 },
  )
  escreverBloco('Diagnóstico do projeto', { size: 12, style: 'bold', espaco: 2 })
  escreverBloco(formatDiagnosticoTexto(item), { size: 10, espaco: 10 })
  if (item?.justificativa) {
    escreverBloco('Justificativa', { size: 12, style: 'bold', espaco: 2 })
    escreverBloco(item.justificativa, { size: 10, espaco: 10 })
  }
}

function blocoInteracao(escreverBloco, interacao, index) {
  const data = interacao?.data_registro
    ? new Date(interacao.data_registro).toLocaleString('pt-BR')
    : null

  escreverBloco(
    `Interação ${index + 1}${interacao?.tipo_acao ? ` · ${interacao.tipo_acao}` : ''}`,
    { size: 13, style: 'bold', cor: [55, 65, 81], espaco: 4 },
  )
  escreverBloco(
    [
      interacao?.modelo_ia && `Modelo: ${interacao.modelo_ia}`,
      data && `Registro: ${data}`,
      (interacao?.tokens_prompt > 0 || interacao?.tokens_resposta > 0) &&
        `Tokens: ${interacao.tokens_prompt ?? 0} entrada / ${interacao.tokens_resposta ?? 0} saída`,
    ]
      .filter(Boolean)
      .join(' · ') || 'Metadados não informados',
    { size: 9, cor: [100, 116, 139], espaco: 8 },
  )

  escreverBloco('Pergunta do usuário / professor', { size: 11, style: 'bold', espaco: 2 })
  escreverBloco(interacao?.prompt_usuario || '—', { size: 10, espaco: 10 })

  escreverBloco('Resposta do agente (IA)', { size: 11, style: 'bold', espaco: 2 })
  escreverBloco(interacao?.resposta_ia || '—', { size: 10, espaco: 12 })
}

/**
 * PDF de uma única interação do histórico.
 */
export function baixarPdfHistoricoInteracao(item, interacao, index = 0) {
  const { doc, escreverBloco } = criarDoc()
  cabecalhoProjeto(escreverBloco, item)
  blocoInteracao(escreverBloco, interacao, index)
  escreverBloco(
    'Relatório gerado na Auditoria de Projetos · MAtivas.',
    { size: 8, style: 'italic', cor: [120, 120, 120], espaco: 0 },
  )
  doc.save(`mativas-historico-projeto-${item?.roteiro_id ?? 'x'}-interacao-${index + 1}.pdf`)
}

/**
 * PDF com o histórico completo (todas as interações) ou fallback (justificativa/passos).
 */
export function baixarPdfHistoricoCompleto(item, interacoes = []) {
  const { doc, escreverBloco } = criarDoc()
  cabecalhoProjeto(escreverBloco, item)

  if (!interacoes.length) {
    escreverBloco('Sem registros de interação IA neste projeto.', {
      size: 10,
      style: 'italic',
      espaco: 10,
    })
    if (item?.passos_json) {
      let passos = item.passos_json
      if (typeof passos === 'string') {
        try {
          passos = JSON.parse(passos)
        } catch {
          /* keep string */
        }
      }
      escreverBloco('Passos do roteiro', { size: 12, style: 'bold', espaco: 4 })
      escreverBloco(
        typeof passos === 'string' ? passos : JSON.stringify(passos, null, 2),
        { size: 9, espaco: 10 },
      )
    }
  } else {
    interacoes.forEach((interacao, index) => {
      blocoInteracao(escreverBloco, interacao, index)
    })
  }

  escreverBloco(
    'Relatório gerado na Auditoria de Projetos · MAtivas.',
    { size: 8, style: 'italic', cor: [120, 120, 120], espaco: 0 },
  )
  doc.save(`mativas-historico-projeto-${item?.roteiro_id ?? 'x'}.pdf`)
}
