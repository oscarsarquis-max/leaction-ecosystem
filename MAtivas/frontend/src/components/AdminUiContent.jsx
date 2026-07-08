import { useCallback, useEffect, useState } from 'react'
import { ChevronDown, ChevronRight, Loader2, Save } from 'lucide-react'
import { listarConteudoUi, salvarConteudoUi } from '../services/adminApi.js'
import { useUiContent } from '../contexts/UiContentContext.jsx'
import { BRAND_LOGO_DEFAULT, BRAND_LOGO_FALLBACK } from '../config/brand.js'
import { UI_SECTIONS, itensDaSecao } from '../data/uiContentSections.js'

function previewLogoUrl(rascunhoUrl) {
  const url = (rascunhoUrl || '').trim()
  if (url) return url
  return BRAND_LOGO_DEFAULT
}

function CampoTexto({ item, valor, onChange, onSalvar, salvando }) {
  return (
    <div className={`rounded-lg border p-4 ${item.key.startsWith('brand.') && item.key !== 'brand.aria_label' ? 'border-slate-100 bg-slate-50' : 'border-slate-200'}`}>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-mono text-xs text-slate-500">{item.key}</p>
          {item.label && <p className="text-sm font-medium text-slate-800">{item.label}</p>}
        </div>
        <button
          type="button"
          onClick={onSalvar}
          disabled={salvando}
          className="inline-flex items-center gap-1 rounded-lg bg-brand-primary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
        >
          {salvando ? <Loader2 size={14} className="spin" /> : <Save size={14} />}
          Salvar
        </button>
      </div>
      <textarea
        rows={item.key.includes('subtitulo') || item.key.includes('privacidade') ? 3 : 2}
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/30"
      />
    </div>
  )
}

function CampoImagem({ item, valor, onChange, onSalvar, salvando, previewSrc }) {
  const srcPreview = previewSrc || (valor || '').trim()

  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-mono text-xs text-slate-500">{item.key}</p>
          {item.label && <p className="text-sm font-medium text-slate-800">{item.label}</p>}
        </div>
        <button
          type="button"
          onClick={onSalvar}
          disabled={salvando}
          className="inline-flex items-center gap-1 rounded-lg bg-brand-primary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
        >
          {salvando ? <Loader2 size={14} className="spin" /> : <Save size={14} />}
          Salvar
        </button>
      </div>
      <input
        type="url"
        placeholder="https://... (vazio = arquivo local ou imagem padrão)"
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/30"
      />
      {item.key === 'assets.logo' && (
        <p className="mt-2 text-xs text-slate-500">
          Arquivo local: <code className="rounded bg-slate-100 px-1">frontend/public/brand/logo.png</code>
        </p>
      )}
      {srcPreview && (
        <img
          src={srcPreview}
          alt={item.label || item.key}
          className="mt-3 max-h-20 rounded-md border border-slate-200 object-contain bg-white p-1"
          onError={(e) => {
            if (item.key === 'assets.logo' && e.currentTarget.src !== BRAND_LOGO_FALLBACK) {
              e.currentTarget.src = BRAND_LOGO_FALLBACK
            }
          }}
        />
      )}
    </div>
  )
}

function SecaoConteudo({
  secao,
  itens,
  rascunhos,
  setRascunhos,
  salvandoKey,
  onSalvar,
}) {
  const [aberta, setAberta] = useState(secao.defaultOpen !== false)
  const itensSecao = itensDaSecao(secao, itens)

  if (!itensSecao.length) return null

  return (
    <div className={secao.muted ? 'rounded-xl border border-dashed border-slate-200' : ''}>
      <button
        type="button"
        onClick={() => setAberta((v) => !v)}
        className="flex w-full items-start gap-2 rounded-t-xl px-1 py-2 text-left"
      >
        {aberta ? (
          <ChevronDown size={18} className="mt-0.5 shrink-0 text-slate-500" />
        ) : (
          <ChevronRight size={18} className="mt-0.5 shrink-0 text-slate-500" />
        )}
        <span>
          <span className="block text-sm font-semibold text-slate-900">{secao.title}</span>
          {secao.description && (
            <span className="mt-1 block text-xs leading-relaxed text-slate-500">
              {secao.description}
            </span>
          )}
        </span>
      </button>

      {aberta && (
        <div className="space-y-4 pb-2 pl-7">
          {itensSecao.map((item) =>
            item.type === 'image_url' ? (
              <CampoImagem
                key={item.key}
                item={item}
                valor={rascunhos[item.key] ?? ''}
                onChange={(v) => setRascunhos((prev) => ({ ...prev, [item.key]: v }))}
                onSalvar={() => onSalvar(item)}
                salvando={salvandoKey === item.key}
                previewSrc={
                  item.key === 'assets.logo'
                    ? previewLogoUrl(rascunhos[item.key])
                    : (rascunhos[item.key] || '').trim() || undefined
                }
              />
            ) : (
              <CampoTexto
                key={item.key}
                item={item}
                valor={rascunhos[item.key] ?? ''}
                onChange={(v) => setRascunhos((prev) => ({ ...prev, [item.key]: v }))}
                onSalvar={() => onSalvar(item)}
                salvando={salvandoKey === item.key}
              />
            ),
          )}
        </div>
      )}
    </div>
  )
}

function AdminUiContent() {
  const { recarregar } = useUiContent()
  const [itens, setItens] = useState([])
  const [rascunhos, setRascunhos] = useState({})
  const [carregando, setCarregando] = useState(true)
  const [salvandoKey, setSalvandoKey] = useState(null)
  const [erro, setErro] = useState('')
  const [sucesso, setSucesso] = useState('')

  const carregar = useCallback(async () => {
    setCarregando(true)
    setErro('')
    try {
      const dados = await listarConteudoUi()
      setItens(dados)
      const mapa = {}
      dados.forEach((item) => {
        mapa[item.key] = item.value
      })
      setRascunhos(mapa)
    } catch {
      setErro('Não foi possível carregar o conteúdo da interface.')
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  const handleSalvar = async (item) => {
    setSalvandoKey(item.key)
    setErro('')
    setSucesso('')
    try {
      await salvarConteudoUi({
        key: item.key,
        value: rascunhos[item.key] ?? '',
        type: item.type,
        label: item.label,
      })
      setSucesso(`"${item.label || item.key}" atualizado. A interface recarrega em até 30 segundos.`)
      await carregar()
      await recarregar()
      window.setTimeout(() => setSucesso(''), 4000)
    } catch {
      setErro(`Falha ao salvar "${item.key}".`)
    } finally {
      setSalvandoKey(null)
    }
  }

  return (
    <section className="space-y-6">
      <div className="admin-card rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <h2 className="mb-2 text-base font-semibold text-slate-900">Conteúdo da interface</h2>
        <p className="mb-4 text-sm text-slate-600">
          Ajuste logotipo, textos e imagens exibidos na aplicação. As regras do{' '}
          <strong>Dicionário da IA</strong> substituem termos automaticamente em toda a interface.
        </p>

        {erro && <p className="mb-3 text-sm text-red-600">{erro}</p>}
        {sucesso && <p className="mb-3 text-sm text-emerald-700">{sucesso}</p>}

        {carregando ? (
          <p className="text-sm text-slate-500">Carregando conteúdo…</p>
        ) : (
          <div className="space-y-6">
            {UI_SECTIONS.map((secao) => (
              <SecaoConteudo
                key={secao.id}
                secao={secao}
                itens={itens}
                rascunhos={rascunhos}
                setRascunhos={setRascunhos}
                salvandoKey={salvandoKey}
                onSalvar={handleSalvar}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

export default AdminUiContent
