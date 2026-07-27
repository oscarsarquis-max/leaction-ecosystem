import { useEffect, useMemo, useRef, useState } from 'react'
import {
  listarCursos,
  listarDisciplinas,
  listarInstituicoes,
  listarPeriodos,
} from '../services/instituicoesService'

/**
 * Seletor opcional: instituição → período → curso → disciplina.
 * Só aparece se houver ao menos um caminho completo.
 * Com autoDefault, pré-seleciona quando há um único caminho (prioriza período em curso).
 */
export default function VinculoPedagogicoSelector({
  disciplinaId,
  onChange,
  autoDefault = true,
}) {
  const [loading, setLoading] = useState(true)
  const [available, setAvailable] = useState(false)
  const [instituicoes, setInstituicoes] = useState([])
  const [periodos, setPeriodos] = useState([])
  const [cursos, setCursos] = useState([])
  const [disciplinas, setDisciplinas] = useState([])
  const [instId, setInstId] = useState('')
  const [periodoId, setPeriodoId] = useState('')
  const [cursoId, setCursoId] = useState('')
  const [discId, setDiscId] = useState('')
  const [pathsByDisc, setPathsByDisc] = useState({})
  const didAutoRef = useRef(false)
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const data = await listarInstituicoes()
        const insts = Array.isArray(data?.instituicoes) ? data.instituicoes : []
        const map = {}
        let hasComplete = false

        for (const inst of insts) {
          let pers = []
          try {
            const pd = await listarPeriodos(inst.id)
            pers = Array.isArray(pd?.periodos) ? pd.periodos : Array.isArray(pd) ? pd : []
          } catch {
            continue
          }
          for (const per of pers) {
            let curs = []
            try {
              const cd = await listarCursos(per.id)
              curs = Array.isArray(cd?.cursos) ? cd.cursos : Array.isArray(cd) ? cd : []
            } catch {
              continue
            }
            for (const cur of curs) {
              let discs = []
              try {
                const dd = await listarDisciplinas(cur.id)
                discs = Array.isArray(dd?.disciplinas)
                  ? dd.disciplinas
                  : Array.isArray(dd)
                    ? dd
                    : []
              } catch {
                continue
              }
              if (discs.length) {
                hasComplete = true
                for (const d of discs) {
                  map[String(d.id)] = {
                    instituicao_id: String(inst.id),
                    instituicao_nome: inst.nome || inst.nome_fantasia || '',
                    periodo_letivo_id: String(per.id),
                    periodo_rotulo: per.rotulo || `${per.ano_letivo || ''}`.trim() || '',
                    em_curso: Boolean(per.em_curso),
                    curso_id: String(cur.id),
                    curso_nome: cur.nome || '',
                    disciplina_id: String(d.id),
                    disciplina_nome: d.nome || '',
                  }
                }
              }
            }
          }
        }

        if (cancelled) return
        setInstituicoes(insts)
        setPathsByDisc(map)
        setAvailable(hasComplete)
      } catch {
        if (!cancelled) {
          setAvailable(false)
          setInstituicoes([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  function applyPath(path) {
    if (!path) return
    setInstId(path.instituicao_id)
    setPeriodoId(path.periodo_letivo_id)
    setCursoId(path.curso_id)
    setDiscId(path.disciplina_id)
  }

  useEffect(() => {
    if (loading || !available) return
    const target = disciplinaId != null && disciplinaId !== '' ? String(disciplinaId) : ''
    if (!target || !pathsByDisc[target]) return
    applyPath(pathsByDisc[target])
  }, [disciplinaId, loading, available, pathsByDisc])

  // Default: NÃO pré-selecionar disciplina (desafio pode ficar sem vínculo e
  // ainda assim aparecer na trilha "Sem disciplina vinculada" do grafo).
  // autoDefault só preenche instituição/período/curso/disciplina se o pai
  // já trouxe disciplinaId (ex.: vindo da agenda).
  useEffect(() => {
    if (loading || !available || didAutoRef.current || !autoDefault) return
    if (disciplinaId == null || disciplinaId === '') return
    const target = String(disciplinaId)
    const path = pathsByDisc[target]
    if (!path) return
    didAutoRef.current = true
    applyPath(path)
  }, [loading, available, pathsByDisc, disciplinaId, autoDefault])

  useEffect(() => {
    if (!instId) {
      setPeriodos([])
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const pd = await listarPeriodos(instId)
        if (cancelled) return
        setPeriodos(Array.isArray(pd?.periodos) ? pd.periodos : Array.isArray(pd) ? pd : [])
      } catch {
        if (!cancelled) setPeriodos([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [instId])

  useEffect(() => {
    if (!periodoId) {
      setCursos([])
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const cd = await listarCursos(periodoId)
        if (cancelled) return
        setCursos(Array.isArray(cd?.cursos) ? cd.cursos : Array.isArray(cd) ? cd : [])
      } catch {
        if (!cancelled) setCursos([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [periodoId])

  useEffect(() => {
    if (!cursoId) {
      setDisciplinas([])
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const dd = await listarDisciplinas(cursoId)
        if (cancelled) return
        setDisciplinas(
          Array.isArray(dd?.disciplinas) ? dd.disciplinas : Array.isArray(dd) ? dd : [],
        )
      } catch {
        if (!cancelled) setDisciplinas([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [cursoId])

  const hint = useMemo(() => {
    if (!discId) {
      return 'Quando possível, vincule o desafio ao seu planejamento escolar.'
    }
    const p = pathsByDisc[discId]
    if (!p) return 'Vínculo ativo.'
    const parts = [p.instituicao_nome, p.curso_nome, p.disciplina_nome].filter(Boolean)
    return parts.length
      ? `Vinculado: ${parts.join(' · ')}`
      : 'Vínculo com o planejamento ativo.'
  }, [discId, pathsByDisc])

  if (loading || !available) return null

  function clearAll() {
    didAutoRef.current = true
    setInstId('')
    setPeriodoId('')
    setCursoId('')
    setDiscId('')
    onChange(null)
  }

  return (
    <fieldset className="rounded-xl border border-brand-100/80 bg-brand-50/30 px-3 py-3">
      <legend className="px-1 text-[11px] font-semibold uppercase tracking-wide text-bordo-soft">
        Planejamento escolar (opcional)
      </legend>
      <p className="mb-2 text-[11px] leading-relaxed text-bordo-soft">
        Não é obrigatório — mas, quando houver cadastro, preferimos vincular o desafio à
        instituição, curso e disciplina.
      </p>
      <div className="mt-1 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="field-label text-xs">Instituição</span>
          <select
            className="field-input mt-1 min-h-10 text-sm"
            value={instId}
            onChange={(e) => {
              const v = e.target.value
              didAutoRef.current = true
              setInstId(v)
              setPeriodoId('')
              setCursoId('')
              setDiscId('')
              onChange(null)
            }}
          >
            <option value="">—</option>
            {instituicoes.map((i) => (
              <option key={i.id} value={String(i.id)}>
                {i.nome || i.nome_fantasia || `Instituição ${i.id}`}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="field-label text-xs">Período letivo</span>
          <select
            className="field-input mt-1 min-h-10 text-sm"
            value={periodoId}
            disabled={!instId}
            onChange={(e) => {
              const v = e.target.value
              didAutoRef.current = true
              setPeriodoId(v)
              setCursoId('')
              setDiscId('')
              onChange(null)
            }}
          >
            <option value="">—</option>
            {periodos.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.em_curso ? '● ' : ''}
                {p.rotulo || `${p.ano_letivo || ''}`.trim() || `Período ${p.id}`}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="field-label text-xs">Curso</span>
          <select
            className="field-input mt-1 min-h-10 text-sm"
            value={cursoId}
            disabled={!periodoId}
            onChange={(e) => {
              const v = e.target.value
              didAutoRef.current = true
              setCursoId(v)
              setDiscId('')
              onChange(null)
            }}
          >
            <option value="">—</option>
            {cursos.map((c) => (
              <option key={c.id} value={String(c.id)}>
                {c.nome || `Curso ${c.id}`}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="field-label text-xs">Disciplina</span>
          <select
            className="field-input mt-1 min-h-10 text-sm"
            value={discId}
            disabled={!cursoId}
            onChange={(e) => {
              const v = e.target.value
              didAutoRef.current = true
              setDiscId(v)
              onChange(v ? Number(v) : null)
            }}
          >
            <option value="">—</option>
            {disciplinas.map((d) => (
              <option key={d.id} value={String(d.id)}>
                {d.nome || `Disciplina ${d.id}`}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] text-bordo-soft">{hint}</p>
        {(instId || discId) && (
          <button
            type="button"
            onClick={clearAll}
            className="text-[11px] font-semibold text-bordo-soft underline-offset-2 hover:underline"
          >
            Limpar vínculo
          </button>
        )}
      </div>
    </fieldset>
  )
}
