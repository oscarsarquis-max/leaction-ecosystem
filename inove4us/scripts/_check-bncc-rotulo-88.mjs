import { rotuloBnccOption } from '../frontend/src/lib/ementaTopicos.js'

const tema =
  'Sistema de numeração decimal: características, leitura, escrita e comparação de números naturais e de números racionais representados na forma decimal'

const ef06ma01 = rotuloBnccOption({ habilidade_codigo: 'EF06MA01', tema })
const short = rotuloBnccOption({
  habilidade_codigo: 'EF06MA25',
  tema: 'Ângulos: noção, usos e medida',
})

const out = {
  ef06ma01,
  starts_with_code: ef06ma01.startsWith('EF06MA01 — '),
  len: ef06ma01.length,
  max_ok: ef06ma01.length <= 120,
  short,
  short_full: short === 'EF06MA25 — Ângulos: noção, usos e medida',
}
console.log(JSON.stringify(out, null, 2))
if (!out.starts_with_code || !out.max_ok || !out.short_full) process.exit(1)
