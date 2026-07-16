const VARIANTS = {
  /** Landing / acesso — marca colorida */
  access: '/imagens/logosombra3.png',
  /** Páginas internas — versão preta 2 */
  internal: '/imagens/logosombra2.png',
  /** Fundos escuros */
  white: '/imagens/logobranco1.png',
}

/**
 * Logo oficial inove4us.
 * @param {'access'|'internal'|'white'} variant
 */
export default function BrandLogo({
  variant = 'internal',
  className = 'h-20 w-auto object-contain',
  alt = 'inove4us',
}) {
  const src = VARIANTS[variant] || VARIANTS.internal
  return <img src={src} alt={alt} className={className} />
}
