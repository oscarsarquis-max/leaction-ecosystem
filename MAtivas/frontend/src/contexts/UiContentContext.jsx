import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { buscarConteudoUi } from '../services/uiContentApi.js'
import { applyTerminology } from '../utils/applyTerminology.js'

const UiContentContext = createContext(null)

const REFRESH_MS = 30_000

export function UiContentProvider({ children }) {
  const [textos, setTextos] = useState({})
  const [imagens, setImagens] = useState({})
  const [substituicoes, setSubstituicoes] = useState([])
  const [versao, setVersao] = useState(0)
  const [carregando, setCarregando] = useState(true)

  const recarregar = useCallback(async () => {
    try {
      const data = await buscarConteudoUi()
      setTextos(data.textos || {})
      setImagens(data.imagens || {})
      setSubstituicoes(data.substituicoes || [])
      setVersao(data.versao || Date.now())
    } catch {
      /* mantém cache anterior em caso de falha */
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => {
    recarregar()
    const timer = window.setInterval(recarregar, REFRESH_MS)
    const onFocus = () => recarregar()
    window.addEventListener('focus', onFocus)
    return () => {
      window.clearInterval(timer)
      window.removeEventListener('focus', onFocus)
    }
  }, [recarregar])

  const formatar = useCallback(
    (texto) => applyTerminology(texto, substituicoes),
    [substituicoes],
  )

  const texto = useCallback(
    (key, fallback = '') => formatar(textos[key] ?? fallback),
    [textos, formatar],
  )

  const imagem = useCallback(
    (key, fallback) => {
      const url = (imagens[key] || '').trim()
      return url || fallback
    },
    [imagens],
  )

  const valor = useMemo(
    () => ({
      carregando,
      versao,
      texto,
      imagem,
      formatar,
      recarregar,
      substituicoes,
    }),
    [carregando, versao, texto, imagem, formatar, recarregar, substituicoes],
  )

  return (
    <UiContentContext.Provider value={valor}>{children}</UiContentContext.Provider>
  )
}

export function useUiContent() {
  const ctx = useContext(UiContentContext)
  if (!ctx) {
    throw new Error('useUiContent deve ser usado dentro de UiContentProvider')
  }
  return ctx
}

/** Atalho para texto dinâmico com fallback embutido. */
export function useUiText(key, fallback = '') {
  const { texto } = useUiContent()
  return texto(key, fallback)
}

/** Atalho para URL de imagem dinâmica. */
export function useUiImage(key, fallback) {
  const { imagem } = useUiContent()
  return imagem(key, fallback)
}
