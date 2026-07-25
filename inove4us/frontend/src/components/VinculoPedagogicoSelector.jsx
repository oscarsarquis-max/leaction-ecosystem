import { useEffect, useMemo, useState } from 'react'
import {
  listarCursos,
  listarDisciplinas,
  listarInstituicoes,
  listarPeriodos,
} from '../services/instituicoesService'

/**
 * Seletor opcional e discreto: instituição → período → curso → disciplina.
 * Só renderiza se o professor tiver ao menos um caminho completo (Etapas 1–2).
 */
export default function VinculoPedagogicoSelector({ disciplinaId, onChange }) {
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
                    periodo_letivo_id: String(per.id),
                    curso_id: String(cur.id),
                    disciplina_id: String(d.id),
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

  useEffect(() => {
    if (loading || !available) return
    const target = disciplinaId != null && disciplinaId !== '' ? String(disciplinaId) : ''
    if (!target || !pathsByDisc[target]) return
    const p = pathsByDisc[target]
    setInstId(p.instituicao_id)
    setPeriodoId(p.periodo_letivo_id)
    setCursoId(p.curso_id)
    setDiscId(p.disciplina_id)
  }, [disciplinaId, loading, available, pathsByDisc])

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
    if (!discId) return null
    const p = pathsByDisc[discId]
    return p ? 'Vínculo pedagógico opcional ativo.' : null
  }, [discId, pathsByDisc])

  if (loading || !available) return null

  function clearAll() {
    setInstId('')
    setPeriodoId('')
    setCursoId('')
    setDiscId('')
    onChange(null)
  }

  return (
    <fieldset className="rounded-xl border border-brand-100/80 bg-brand-50/30 px-3 py-3">
      <legend className="px-1 text-[11px] font-semibold uppercase tracking-wide text-bordo-soft">
        Vínculo pedagógico (opcional)
      </legend>
      <div className="mt-1 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="field-label text-xs">Instituição</span>
          <select
            className="field-input mt-1 min-h-10 text-sm"
            value={instId}
            onChange={(e) => {
              const v = e.target.value
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
              setPeriodoId(v)
              setCursoId('')
              setDiscId('')
              onChange(null)
            }}
          >
            <option value="">—</option>
            {periodos.map((p) => (
              <option key={p.id} value={String(p.id)}>
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
        {hint ? <p className="text-[11px] text-bordo-soft">{hint}</p> : <span />}
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
