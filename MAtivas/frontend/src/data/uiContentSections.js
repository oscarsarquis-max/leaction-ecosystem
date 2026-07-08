/** Agrupamento das chaves de ui_content no painel administrativo. */

export const LOGO_KEYS = ['assets.logo', 'brand.aria_label']

export const BRAND_LEGACY_KEYS = [
  'brand.linha_superior',
  'brand.pill',
  'brand.sufixo',
  'brand.linha_inferior',
]

export const OTHER_IMAGE_KEYS = ['assets.capa_livro', 'assets.foto_andrea']

export const UI_SECTIONS = [
  {
    id: 'logo',
    title: 'Logotipo',
    description:
      'O logotipo exibido no topo das páginas vem do arquivo frontend/public/brand/logo.png. ' +
      'Use a URL abaixo apenas se quiser apontar para uma imagem externa (ela tem prioridade sobre o arquivo local). ' +
      'O texto alternativo descreve a marca para leitores de tela.',
    keys: LOGO_KEYS,
    defaultOpen: true,
  },
  {
    id: 'brand-legacy',
    title: 'Textos da marca (legado)',
    description:
      'Estes textos só aparecem se a imagem do logotipo não carregar (fallback de emergência). ' +
      'Com logo.png instalado, você pode ignorá-los.',
    keys: BRAND_LEGACY_KEYS,
    defaultOpen: false,
    muted: true,
  },
  {
    id: 'pages',
    title: 'Textos das páginas',
    description: 'Títulos, subtítulos e mensagens fixas exibidas nas telas da aplicação.',
    match: (item) =>
      item.type !== 'image_url' &&
      !LOGO_KEYS.includes(item.key) &&
      !BRAND_LEGACY_KEYS.includes(item.key),
    defaultOpen: true,
  },
  {
    id: 'images',
    title: 'Outras imagens',
    description:
      'URLs alternativas para capa do livro e foto da autora. Deixe em branco para usar as imagens padrão do aplicativo.',
    keys: OTHER_IMAGE_KEYS,
    defaultOpen: true,
  },
]

export function itensDaSecao(secao, itens) {
  if (secao.keys) {
    const mapa = new Map(itens.map((i) => [i.key, i]))
    return secao.keys.map((key) => mapa.get(key)).filter(Boolean)
  }
  if (secao.match) {
    return itens.filter(secao.match)
  }
  return []
}
