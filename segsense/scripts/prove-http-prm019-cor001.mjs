import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'

const here = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.resolve(here, '..', 'documents', 'evidencias', 'SEGSENSE_PRM_019_COR_001')
mkdirSync(outDir, { recursive: true })

const bff = process.env.SEGSENSE_BFF ?? 'http://127.0.0.1:19088'
const fe = process.env.SEGSENSE_FE ?? 'http://127.0.0.1:15178'
const mock = process.env.SEGSENSE_MOCK ?? 'http://127.0.0.1:19095'
const firesUrl = `${fe}/demonstracao/fontes/proximidade-incendios`
const familyUrl = `${fe}/demonstracao/fontes/continuidade-familiar`

const report = { bff, fe, mock, steps: [] }

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

function sanitizeJourney(body) {
  if (!body || typeof body !== 'object') {
    return body
  }
  return {
    id: body.id,
    status: body.status,
    mockCalled: body.mockCalled,
    mockOrigin: body.mockOrigin,
    quoteReference: body.quoteReference,
    spiderDecisionId: body.spiderDecisionId,
    capabilityId: body.capabilityId,
    providerRequestId: body.providerRequestId,
    mockResultId: body.mockResultId,
    missingContext: body.missingContext,
    missingQuestions: body.missingQuestions,
    itemsCount: Array.isArray(body.items) ? body.items.length : null,
    simulatedQuote: body.simulatedQuote
      ? {
          premiumAnnualCents: body.simulatedQuote.premiumAnnualCents,
          insuredAmountCents: body.simulatedQuote.insuredAmountCents,
          coverPeriodMonths: body.simulatedQuote.coverPeriodMonths,
          dwellingType: body.simulatedQuote.dwellingType,
          dwellingBps: body.simulatedQuote.dwellingBps,
          ratingRuleVersion: body.simulatedQuote.ratingRuleVersion,
          nearbyFiresDidNotAdjustPremium: body.simulatedQuote.nearbyFiresDidNotAdjustPremium,
        }
      : null,
  }
}

async function postJson(url, body, headers = {}) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json; charset=utf-8',
      'X-Correlation-ID': randomUUID(),
      ...headers,
    },
    body: JSON.stringify(body),
  })
  const text = await response.text()
  let json = null
  try {
    json = text ? JSON.parse(text) : null
  } catch {
    json = { parseError: true, preview: text.slice(0, 240) }
  }
  return { status: response.status, json, rawLength: text.length }
}

async function getJson(url) {
  const response = await fetch(url)
  return { status: response.status, json: await response.json() }
}

const resolve = await postJson(`${bff}/api/v1/public/demo/context-sources/resolve`, { url: firesUrl })
assert(resolve.status === 200, `resolve fires expected 200, got ${resolve.status}`)
assert(resolve.json?.sourceId || resolve.json?.id || resolve.json?.title, 'resolve did not return a governed source')
report.steps.push({
  name: 'resolve-fires',
  status: resolve.status,
  title: resolve.json?.title ?? null,
  sourceId: resolve.json?.sourceId ?? resolve.json?.id ?? null,
})

const missingKey = randomUUID()
const missing = await postJson(
  `${bff}/api/v1/public/demo/protection-journeys`,
  {
    declaredObjective: 'SIMULATE_HOME_QUOTE',
    declaredIntention: 'Quero contratar um seguro residencial',
    declaredContext: 'Houve incêndios nas proximidades',
    sourceUrl: firesUrl,
    intentionConfirmed: 'true',
  },
  { 'Idempotency-Key': missingKey },
)
assert(missing.status === 200, `missing expected 200, got ${missing.status}`)
assert(missing.json?.status === 'MISSING_CONTEXT', `expected MISSING_CONTEXT, got ${missing.json?.status}`)
assert(missing.json?.mockCalled === false, 'provider was called on MISSING_CONTEXT')
assert(!missing.json?.simulatedQuote?.premiumAnnualCents, 'premium leaked on MISSING_CONTEXT')
report.steps.push({ name: 'missing-context', ...sanitizeJourney(missing.json) })

const quoteKey = randomUUID()
const quoteBody = {
  declaredObjective: 'SIMULATE_HOME_QUOTE',
  declaredIntention: 'Quero contratar um seguro residencial',
  declaredContext: 'Houve incêndios nas proximidades',
  sourceUrl: firesUrl,
  intentionConfirmed: 'true',
  dwellingType: 'APARTMENT',
  insuredAmountCents: '30000000',
  coverPeriodMonths: '12',
}
const quote = await postJson(`${bff}/api/v1/public/demo/protection-journeys`, quoteBody, {
  'Idempotency-Key': quoteKey,
})
assert(quote.status === 200, `quote expected 200, got ${quote.status}`)
assert(quote.json?.status === 'SIMULATED_QUOTE_AVAILABLE', `expected SIMULATED_QUOTE_AVAILABLE, got ${quote.json?.status}`)
assert(quote.json?.simulatedQuote?.premiumAnnualCents === 54000, `expected 54000 cents, got ${quote.json?.simulatedQuote?.premiumAnnualCents}`)
assert(quote.json?.capabilityId === 'GENERATE_SYNTHETIC_HOME_QUOTE', `unexpected capability ${quote.json?.capabilityId}`)
report.steps.push({ name: 'quote-540', ...sanitizeJourney(quote.json) })

const replay = await postJson(`${bff}/api/v1/public/demo/protection-journeys`, quoteBody, {
  'Idempotency-Key': quoteKey,
})
assert(replay.status === 200, `replay expected 200, got ${replay.status}`)
assert(replay.json?.id === quote.json.id, 'replay changed journey id')
assert(replay.json?.quoteReference === quote.json.quoteReference, 'replay changed quoteReference')
assert(replay.json?.simulatedQuote?.premiumAnnualCents === 54000, 'replay changed premium')
report.steps.push({
  name: 'replay',
  sameId: replay.json?.id === quote.json.id,
  sameQuoteReference: replay.json?.quoteReference === quote.json.quoteReference,
})

const conflict = await postJson(
  `${bff}/api/v1/public/demo/protection-journeys`,
  { ...quoteBody, insuredAmountCents: '60000000' },
  { 'Idempotency-Key': quoteKey },
)
assert(conflict.status === 409, `material change expected 409, got ${conflict.status}`)
report.steps.push({ name: 'material-change-409', status: conflict.status })

const family = await postJson(
  `${bff}/api/v1/public/demo/protection-journeys`,
  {
    declaredObjective: 'UNDERSTAND_PROTECTION_OPTIONS',
    declaredIntention: 'entender opções ilustrativas de proteção',
    sourceUrl: familyUrl,
    intentionConfirmed: 'true',
  },
  { 'Idempotency-Key': randomUUID() },
)
assert(family.status === 200, `family expected 200, got ${family.status}`)
assert(family.json?.status === 'PRE_PROPOSAL_AVAILABLE', `family status ${family.json?.status}`)
assert(!family.json?.simulatedQuote?.premiumAnnualCents, 'illustrative journey leaked a premium')
report.steps.push({ name: 'family-illustrative', ...sanitizeJourney(family.json) })

const health = await getJson(`${mock}/health`)
assert(health.status === 200, `mock health expected 200, got ${health.status}`)
const executions = health.json?.recentExecutions ?? []
const requestIds = executions.map((item) => item.requestId).filter(Boolean)
const segsenseCaller = requestIds.some((id) => /19088|localhost:8088|:8088/i.test(String(id)))
assert(!segsenseCaller, 'mock recentExecutions looks like a SegSense caller')
assert(
  requestIds.length === 0 || requestIds.every((id) => String(id).startsWith('preq-')),
  `mock requestIds were not Spider provider requests: ${requestIds.join(',')}`,
)
report.steps.push({
  name: 'mock-health',
  executionCount: executions.length,
  requestIds: executions.map((item) => item.requestId),
  segsenseDidNotCallMock: !segsenseCaller,
})

const serialized = JSON.stringify(report)
assert(!/Bearer\s+[A-Za-z0-9\-._~+/]+/.test(serialized), 'proof JSON contained a bearer token')
assert(!/APPLICATION_SECRET|MOCK_CREDENTIAL/i.test(serialized), 'proof JSON contained secret names')

writeFileSync(path.join(outDir, 'http-proof.json'), JSON.stringify(report, null, 2))
console.log('HTTP COR_001 proof complete')
console.log(JSON.stringify({ quotePremiumCents: 54000, missing: 'MISSING_CONTEXT', replay: true, conflict: 409 }, null, 2))
