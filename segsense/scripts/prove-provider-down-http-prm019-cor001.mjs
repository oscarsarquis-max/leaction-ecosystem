import { writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'

const here = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.resolve(here, '..', 'documents', 'evidencias', 'SEGSENSE_PRM_019_COR_001')
const bff = 'http://127.0.0.1:19088'
const fe = 'http://127.0.0.1:15178'

const response = await fetch(`${bff}/api/v1/public/demo/protection-journeys`, {
  method: 'POST',
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json; charset=utf-8',
    'Idempotency-Key': randomUUID(),
    'X-Correlation-ID': randomUUID(),
  },
  body: JSON.stringify({
    declaredObjective: 'SIMULATE_HOME_QUOTE',
    declaredIntention: 'Quero contratar um seguro residencial',
    declaredContext: 'Houve incêndios nas proximidades',
    sourceUrl: `${fe}/demonstracao/fontes/proximidade-incendios`,
    intentionConfirmed: 'true',
    dwellingType: 'APARTMENT',
    insuredAmountCents: '30000000',
    coverPeriodMonths: '12',
  }),
})
const json = await response.json()
if (json.status !== 'MOCK_UNAVAILABLE') {
  throw new Error(`expected MOCK_UNAVAILABLE, got ${json.status}`)
}
if (json.simulatedQuote) {
  throw new Error('provider-down response contained simulatedQuote')
}
if (json.quoteReference) {
  throw new Error('provider-down response contained quoteReference')
}
writeFileSync(
  path.join(outDir, 'provider-down-http.json'),
  JSON.stringify(
    {
      httpStatus: response.status,
      status: json.status,
      mockCalled: json.mockCalled,
      simulatedQuote: json.simulatedQuote ?? null,
      quoteReference: json.quoteReference ?? null,
    },
    null,
    2,
  ),
)
console.log('provider-down HTTP MOCK_UNAVAILABLE without premium')
