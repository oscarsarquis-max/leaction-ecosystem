const TIPO_LABEL = {
  interrompida: 'Interrompida',
  substituicao: 'Substituição',
  trabalho_monitorado: 'Trabalho monitorado',
}

const TIPO_TONE = {
  interrompida: 'bg-amber-100 text-amber-900',
  substituicao: 'bg-sky-100 text-sky-900',
  trabalho_monitorado: 'bg-stone-200 text-stone-800',
}

export function formatDataBR(iso) {
  const p = String(iso || '').slice(0, 10).split('-')
  if (p.length !== 3 || !p[0] || p[0].length !== 4) return ''
  return `${p[2]}/${p[1]}/${p[0]}`
}

export function pickOcorrencia(item) {
  if (!item || typeof item !== 'object') return {}
  const mesa = item.mesa || {}
  const nested =
    typeof mesa.ocorrencia === 'object' && mesa.ocorrencia ? mesa.ocorrencia : {}
  const flat = typeof item.ocorrencia === 'object' && item.ocorrencia ? item.ocorrencia : {}
  const tipo = item.ocorrencia_tipo || nested.tipo || flat.tipo
  const resolucao =
    item.ocorrencia_resolucao || nested.resolucao || nested.status || flat.resolucao
  return {
    tipo,
    nota: item.ocorrencia_nota || nested.nota || flat.nota || '',
    resolucao,
    unida: Boolean(item.ocorrencia_unida || nested.unida || flat.unida),
    aguardando: Boolean(
      item.aguardando_continuacao || nested.aguardando_continuacao,
    ),
    juncaoDestinoData: item.juncao_destino_data || nested.juncao_destino_data,
    juncaoOrigemData: item.juncao_origem_data || nested.juncao_origem_data,
    continuacaoOrigemData:
      item.continuacao_origem_data || nested.continuacao_origem_data,
    continuacaoDestinoData:
      item.continuacao_destino_data || nested.continuacao_destino_data,
    vinculo: item.ocorrencia_vinculo || '',
  }
}

export function vinculoTexto(itemOrOcc) {
  const o =
    itemOrOcc && (itemOrOcc.tipo || itemOrOcc.resolucao || itemOrOcc.juncaoDestinoData)
      ? itemOrOcc
      : pickOcorrencia(itemOrOcc)
  if (o.vinculo) return o.vinculo
  const dest = formatDataBR(o.juncaoDestinoData)
  const orig = formatDataBR(o.juncaoOrigemData)
  const contDe = formatDataBR(o.continuacaoOrigemData)
  const contEm = formatDataBR(o.continuacaoDestinoData)
  if (o.resolucao === 'concluida_via_juncao' || dest) {
    return dest ? `Unida com a aula de ${dest}` : 'Unida com outra aula'
  }
  if (orig) return `Unida com a aula de ${orig}`
  if (contDe) return `Continuação de ${contDe}`
  if (o.resolucao === 'agendada_continuacao' || contEm) {
    return contEm ? `Continuação em ${contEm}` : 'Continuação agendada'
  }
  return ''
}

export function temOcorrenciaVisual(item) {
  const o = pickOcorrencia(item)
  return Boolean((o.tipo && TIPO_LABEL[o.tipo]) || o.unida || vinculoTexto(o))
}

export function OcorrenciaExpandida({ item, className = '' }) {
  const o = pickOcorrencia(item)
  const vinculo = vinculoTexto(o)
  const nota = String(o.nota || '').trim()
  const tipoLabel = TIPO_LABEL[o.tipo]
  if (!tipoLabel && !o.unida && !vinculo && !nota) return null
  return (
    <div
      className={[
        'rounded-lg border border-amber-200 bg-amber-50/80 px-3 py-2.5 text-sm text-amber-950',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <OcorrenciaBadges item={item} />
      </div>
      {vinculo ? <p className="mt-1.5 text-xs font-semibold">{vinculo}</p> : null}
      {nota ? (
        <p className="mt-1.5 whitespace-pre-wrap text-sm leading-relaxed">{nota}</p>
      ) : null}
    </div>
  )
}

export default function OcorrenciaBadges({ item, className = '' }) {
  const o = pickOcorrencia(item)
  const badges = []
  if (o.tipo && TIPO_LABEL[o.tipo]) {
    badges.push({
      key: 'tipo',
      label: TIPO_LABEL[o.tipo],
      tone: TIPO_TONE[o.tipo] || 'bg-slate-100 text-slate-800',
    })
  }
  if (o.unida || o.resolucao === 'concluida_via_juncao') {
    badges.push({
      key: 'unida',
      label: 'Unida',
      tone: 'bg-indigo-100 text-indigo-900',
    })
  } else if (o.continuacaoOrigemData || o.resolucao === 'agendada_continuacao') {
    badges.push({
      key: 'cont',
      label: 'Continuação',
      tone: 'bg-indigo-100 text-indigo-900',
    })
  }
  if (!badges.length) return null
  return (
    <span className={['inline-flex flex-wrap gap-1', className].filter(Boolean).join(' ')}>
      {badges.map((b) => (
        <span
          key={b.key}
          className={`rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase ${b.tone}`}
        >
          {b.label}
        </span>
      ))}
    </span>
  )
}
