import { useEffect, useState } from 'react'
import { useUiContent } from '../contexts/UiContentContext.jsx'
import { BRAND_LOGO_DEFAULT, BRAND_LOGO_FALLBACK } from '../config/brand.js'

function BrandTextFallback() {
  const { texto } = useUiContent()

  return (
    <span className="brand brand-text" aria-hidden="true">
      <span className="brand-top">{texto('brand.linha_superior', 'metodologias')}</span>
      <span className="brand-mid">
        <span className="brand-pill">{texto('brand.pill', 'INOV-')}</span>
        <span className="brand-ativas">{texto('brand.sufixo', 'ativas')}</span>
      </span>
      <span className="brand-bottom">{texto('brand.linha_inferior', 'na educação')}</span>
    </span>
  )
}

function Brand() {
  const { texto, imagem } = useUiContent()
  const [usarTexto, setUsarTexto] = useState(false)
  const srcPreferido = imagem('assets.logo', BRAND_LOGO_DEFAULT)
  const [srcAtual, setSrcAtual] = useState(srcPreferido)

  useEffect(() => {
    setSrcAtual(srcPreferido)
    setUsarTexto(false)
  }, [srcPreferido])

  const ariaLabel = texto('brand.aria_label', 'metodologias INOV-ativas na educação')

  if (usarTexto) {
    return (
      <span className="brand-wrap" aria-label={ariaLabel}>
        <BrandTextFallback />
      </span>
    )
  }

  const handleErro = () => {
    if (srcAtual === BRAND_LOGO_DEFAULT) {
      setSrcAtual(BRAND_LOGO_FALLBACK)
      return
    }
    if (srcAtual === BRAND_LOGO_FALLBACK) {
      setUsarTexto(true)
    }
  }

  return (
    <span className="brand-wrap">
      <img
        className="brand brand-logo"
        src={srcAtual}
        alt={ariaLabel}
        onError={handleErro}
      />
    </span>
  )
}

export default Brand
