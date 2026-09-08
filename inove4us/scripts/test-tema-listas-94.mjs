import {
  extractBnccCodigos,
  filtraBnccPorBusca,
  joinTemasEmenta,
  montarConteudoSequencial,
  qualificadorBncc,
  rotuloBnccOption,
} from '../frontend/src/lib/ementaTopicos.js'

const geo = [
  {
    habilidade_codigo: 'EF06GE01',
    tema: 'Identidade sociocultural',
    texto_oficial:
      'Comparar modificações das paisagens nos lugares de vivência e os usos desses lugares em diferentes tempos.',
  },
  {
    habilidade_codigo: 'EF06GE02',
    tema: 'Identidade sociocultural',
    texto_oficial:
      'Analisar modificações de paisagens por diferentes tipos de sociedade, com destaque para os povos originários.',
  },
]

const q1 = qualificadorBncc(geo[0], geo)
const q2 = qualificadorBncc(geo[1], geo)
if (!q1.includes('Comparar') || !q2.includes('Analisar')) {
  throw new Error(`qualificador falhou: ${q1} / ${q2}`)
}
if (q1 === q2) throw new Error('qualificador igual nos dois códigos')

const r1 = rotuloBnccOption(geo[0], { lista: geo, max: 280 })
const r2 = rotuloBnccOption(geo[1], { lista: geo, max: 280 })
if (!r1.includes('EF06GE01') || !r1.includes('Comparar')) {
  throw new Error(`rotulo 1: ${r1}`)
}
if (!r2.includes('EF06GE02') || !r2.includes('Analisar')) {
  throw new Error(`rotulo 2: ${r2}`)
}

const frac = [
  ...geo,
  {
    habilidade_codigo: 'EF06MA07',
    tema: 'Frações no cotidiano',
    texto_oficial: 'Resolver problemas de frações.',
  },
]
const hit = filtraBnccPorBusca(frac, 'frações')
if (hit.length !== 1 || hit[0].habilidade_codigo !== 'EF06MA07') {
  throw new Error(`busca frações: ${JSON.stringify(hit)}`)
}

const seq = montarConteudoSequencial([
  { habilidade_codigo: 'EF06MA07', tema: 'Frações', texto: 'bloco A' },
  { habilidade_codigo: 'EF06MA08', tema: 'Decimais', texto: 'bloco B' },
])
if (!seq.includes('bloco A') || !seq.includes('bloco B') || !seq.includes('---')) {
  throw new Error(`sequencial: ${seq}`)
}
if (seq.indexOf('bloco A') > seq.indexOf('bloco B')) {
  throw new Error('ordem dos blocos invertida')
}
if (seq.includes('bloco A bloco B') || !seq.includes('[BNCC] EF06MA07')) {
  throw new Error('blocos devem ficar separados, não fundidos')
}

const codes = extractBnccCodigos('EF06MA07 — Frações · EF06MA08 — Decimais')
if (codes.join(',') !== 'EF06MA07,EF06MA08') {
  throw new Error(`extract: ${codes}`)
}
if (joinTemasEmenta(['Números', 'Frações']) !== 'Números · Frações') {
  throw new Error('join ementa')
}

console.log('ok')
console.log('qualificador_campo=texto_oficial (enunciado bncc_habilidades_oficial.texto)')
console.log('caso', r1)
console.log('caso', r2)
