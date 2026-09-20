import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'

const here = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.resolve(here, '..', 'documents', 'evidencias', 'SEGSENSE_PRM_020')
mkdirSync(outDir, { recursive: true })

const bff = process.env.SEGSENSE_BFF ?? 'http://127.0.0.1:19088'
const fe = process.env.SEGSENSE_FE ?? 'http://127.0.0.1:15178'
const mock = process.env.SEGSENSE_MOCK ?? 'http://127.0.0.1:19095'
const spider = process.env.SEGSENSE_SPIDER ?? 'http://127.0.0.1:19080'
const cropUrl =
  process.env.SEGSENSE_CROP_URL ??
  'https://pt.wikipedia.org/wiki/Agricultura_no_Brasil'
const firesUrl = `${fe}/demonstracao/fontes/proximidade-incendios`

const report = {
  capturedAtUtc: new Date().toISOString(),
  bff,
  fe,
  mock,
  spider,
  cropUrlRequested: cropUrl,
  steps: [],
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

function sanitizeCapture(body) {
  if (!body || typeof body !== 'object') {
    return body
  }
  const text = typeof body.normalizedText === 'string' ? body.normalizedText : ''
  const excerpt = typeof body.excerpt === 'string' ? body.excerpt : ''
  return {
    captureId: body.captureId,
    publicStatus: body.publicStatus,
    message: body.message,
    requestedUrl: body.requestedUrl,
    finalUrl: body.finalUrl,
    finalHost: body.finalHost,
    capturedAt: body.capturedAt,
    title: body.title,
    excerptLength: excerpt.length,
    excerptPreview: excerpt.slice(0, 180),
    textLength: text.length,
    containsCropFailure: /quebra de safra/i.test(`${excerpt} ${text} ${body.title ?? ''}`),
    technical: {
      resultCode: body.technical?.resultCode ?? null,
      httpStatus: body.technical?.httpStatus ?? null,
      contentType: body.technical?.contentType ?? null,
      bytesSha256Prefix: body.technical?.bytesSha256 ? String(body.technical.bytesSha256).slice(0, 12) : null,
      textSha256Prefix: body.technical?.textSha256 ? String(body.technical.textSha256).slice(0, 12) : null,
      extractorVersion: body.technical?.extractorVersion ?? null,
    },
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
    quoteReference: body.quoteReference ?? null,
    spiderDecisionId: body.spiderDecisionId,
    capabilityId: body.capabilityId ?? null,
    providerRequestId: body.providerRequestId ?? null,
    mockResultId: body.mockResultId,
    satelliteContractVersion: body.satelliteContractVersion ?? null,
    items: Array.isArray(body.items)
      ? body.items.map((item) => ({
          code: item.code,
          title: item.title,
          kind: item.kind,
          pertinence: item.pertinence,
          limits: item.limits,
        }))
      : [],
    simulatedQuote: body.simulatedQuote
      ? { premiumAnnualCents: body.simulatedQuote.premiumAnnualCents, dwellingType: body.simulatedQuote.dwellingType }
      : null,
    explanationPreview: typeof body.explanation === 'string' ? body.explanation.slice(0, 240) : null,
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
  const json = await response.json()
  return { status: response.status, json }
}

const mockHealthBefore = await getJson(`${mock}/health`)
assert(mockHealthBefore.status === 200, 'isolated mock health failed')
const executionsBefore = Array.isArray(mockHealthBefore.json?.recentExecutions)
  ? mockHealthBefore.json.recentExecutions.length
  : 0

async function capture(url) {
  return postJson(`${bff}/api/v1/public/demo/url-captures`, { url })
}

const loopback = await capture('http://127.0.0.1/')
assert(loopback.status === 200, `loopback expected 200, got ${loopback.status}`)
assert(loopback.json?.publicStatus === 'CAPTURE_FAILED', 'loopback was not failed')
assert(loopback.json?.technical?.resultCode === 'DNS_BLOCKED', `loopback code ${loopback.json?.technical?.resultCode}`)
report.steps.push({ name: 'ssrf-loopback', ...sanitizeCapture(loopback.json) })

const metadata = await capture('http://169.254.169.254/latest/meta-data')
assert(metadata.json?.technical?.resultCode === 'DNS_BLOCKED', 'metadata not blocked')
report.steps.push({ name: 'ssrf-metadata', resultCode: metadata.json?.technical?.resultCode })

const userinfo = await capture('https://user:pass@example.com/')
assert(userinfo.json?.technical?.resultCode === 'INVALID_URL', 'userinfo not rejected')
report.steps.push({ name: 'ssrf-userinfo', resultCode: userinfo.json?.technical?.resultCode })

const ipv6 = await capture('http://[::1]/')
assert(['DNS_BLOCKED', 'INVALID_URL'].includes(ipv6.json?.technical?.resultCode), 'ipv6 local not blocked')
report.steps.push({ name: 'ssrf-ipv6-local', resultCode: ipv6.json?.technical?.resultCode })

const notFound = await capture('https://example.com/segsense-prm020-missing-' + randomUUID())
assert(notFound.json?.publicStatus === 'CAPTURE_FAILED', '404/missing did not fail visibly')
assert(['HTTP_ERROR', 'NO_MEANINGFUL_TEXT', 'TIMEOUT'].includes(notFound.json?.technical?.resultCode), notFound.json?.technical?.resultCode)
report.steps.push({ name: 'http-missing', ...sanitizeCapture(notFound.json) })

const pdf = await capture('https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf')
assert(pdf.json?.publicStatus === 'CAPTURE_FAILED', 'pdf did not fail')
assert(['UNSUPPORTED_CONTENT', 'HTTP_ERROR', 'TIMEOUT'].includes(pdf.json?.technical?.resultCode), pdf.json?.technical?.resultCode)
report.steps.push({ name: 'mime-pdf', ...sanitizeCapture(pdf.json) })

const crop = await capture(cropUrl)
report.steps.push({ name: 'crop-url-capture', ...sanitizeCapture(crop.json) })
assert(crop.status === 200, `crop capture http ${crop.status}`)

let cropJourney = null
if (crop.json?.publicStatus === 'AWAITING_REVIEW' && crop.json?.captureId) {
  const excerpt = `${crop.json.excerpt ?? ''} ${crop.json.normalizedText ?? ''}`
  assert(/quebra de safra/i.test(excerpt) || /quebra de safra/i.test(crop.json.title ?? ''), 'captured text does not contain quebra de safra')
  const confirm = await postJson(`${bff}/api/v1/public/demo/url-captures/${crop.json.captureId}/confirmations`, {
    declaredNote: 'Complemento de auditoria: declaração da pessoa, distinta da extração.',
  })
  assert(confirm.status === 200, `confirm http ${confirm.status}`)
  assert(confirm.json?.publicStatus === 'CONTEXT_CONFIRMED', confirm.json?.publicStatus)
  report.steps.push({
    name: 'crop-confirm',
    confirmationId: confirm.json?.confirmationId,
    captureId: confirm.json?.captureId,
    publicStatus: confirm.json?.publicStatus,
  })

  const cropKey = randomUUID()
  cropJourney = await postJson(
    `${bff}/api/v1/public/demo/protection-journeys`,
    {
      declaredObjective: 'UNDERSTAND_PROTECTION_OPTIONS',
      declaredIntention: 'Quero entender opções de proteção para perda de produção',
      intentionConfirmed: 'true',
      captureId: crop.json.captureId,
    },
    { 'Idempotency-Key': cropKey },
  )
  assert(cropJourney.status === 200, `crop journey http ${cropJourney.status}`)
  assert(cropJourney.json?.status === 'PRE_PROPOSAL_AVAILABLE', `crop status ${cropJourney.json?.status}`)
  assert(cropJourney.json?.capabilityId === 'DISCOVER_SYNTHETIC_CROP_PROTECTION_PATHS', cropJourney.json?.capabilityId)
  assert(cropJourney.json?.mockCalled === true, 'crop mock was not called')
  assert(cropJourney.json?.capabilityId !== 'GENERATE_SYNTHETIC_HOME_QUOTE', 'crop dispatched home quote')
  assert(!cropJourney.json?.simulatedQuote?.premiumAnnualCents, 'crop returned residential premium')
  const titles = (cropJourney.json?.items ?? []).map((item) => item.title)
  assert(titles.some((title) => /demonstrativo/i.test(title)), 'crop items missing demonstrative mark')
  assert(!JSON.stringify(cropJourney.json?.items ?? []).includes('540'), 'crop items leaked 540')
  report.steps.push({ name: 'crop-journey', ...sanitizeJourney(cropJourney.json) })

  const replay = await postJson(
    `${bff}/api/v1/public/demo/protection-journeys`,
    {
      declaredObjective: 'UNDERSTAND_PROTECTION_OPTIONS',
      declaredIntention: 'Quero entender opções de proteção para perda de produção',
      intentionConfirmed: 'true',
      captureId: crop.json.captureId,
    },
    { 'Idempotency-Key': cropKey },
  )
  assert(replay.json?.id === cropJourney.json?.id, 'identical replay did not return the same journey')
  report.steps.push({ name: 'crop-replay-identical', id: replay.json?.id, status: replay.json?.status })

  const changed = await postJson(
    `${bff}/api/v1/public/demo/protection-journeys`,
    {
      declaredObjective: 'COMPARE_COVERAGE_GAPS',
      declaredIntention: 'Quero comparar lacunas ilustrativas',
      intentionConfirmed: 'true',
      captureId: crop.json.captureId,
    },
    { 'Idempotency-Key': cropKey },
  )
  assert(changed.status === 409, `material change expected 409, got ${changed.status}`)
  report.steps.push({ name: 'crop-replay-conflict', status: changed.status })

  const homeOnCrop = await postJson(
    `${bff}/api/v1/public/demo/protection-journeys`,
    {
      declaredObjective: 'SIMULATE_HOME_QUOTE',
      declaredIntention: 'Quero contratar um seguro residencial',
      intentionConfirmed: 'true',
      captureId: crop.json.captureId,
    },
    { 'Idempotency-Key': randomUUID() },
  )
  assert(homeOnCrop.json?.status === 'AMBIGUOUS', `crop+home expected AMBIGUOUS, got ${homeOnCrop.json?.status}`)
  assert(homeOnCrop.json?.mockCalled === false, 'crop+home called provider')
  assert(!homeOnCrop.json?.simulatedQuote?.premiumAnnualCents, 'crop+home leaked premium')
  report.steps.push({ name: 'crop-never-home-quote', ...sanitizeJourney(homeOnCrop.json) })
} else {
  report.steps.push({
    name: 'crop-url-capture-insufficient',
    note: 'Spider was not called. Honest capture failure.',
    publicStatus: crop.json?.publicStatus,
    resultCode: crop.json?.technical?.resultCode,
    message: crop.json?.message,
  })
}

const quoteKey = randomUUID()
const quote = await postJson(
  `${bff}/api/v1/public/demo/protection-journeys`,
  {
    declaredObjective: 'SIMULATE_HOME_QUOTE',
    declaredIntention: 'Quero contratar um seguro residencial',
    declaredContext: 'Houve incêndios nas proximidades',
    sourceUrl: firesUrl,
    intentionConfirmed: 'true',
    dwellingType: 'APARTMENT',
    insuredAmountCents: '30000000',
    coverPeriodMonths: '12',
  },
  { 'Idempotency-Key': quoteKey },
)
assert(quote.status === 200, `home quote http ${quote.status}`)
assert(quote.json?.status === 'SIMULATED_QUOTE_AVAILABLE', quote.json?.status)
assert(quote.json?.simulatedQuote?.premiumAnnualCents === 54000, `premium ${quote.json?.simulatedQuote?.premiumAnnualCents}`)
assert(quote.json?.capabilityId === 'GENERATE_SYNTHETIC_HOME_QUOTE', quote.json?.capabilityId)
report.steps.push({ name: 'home-quote-still-540', ...sanitizeJourney(quote.json) })

const unconfirmed = await postJson(
  `${bff}/api/v1/public/demo/protection-journeys`,
  {
    declaredObjective: 'UNDERSTAND_PROTECTION_OPTIONS',
    declaredIntention: 'Quero entender opções de proteção para perda de produção',
    intentionConfirmed: 'true',
    captureId: loopback.json?.captureId,
  },
  { 'Idempotency-Key': randomUUID() },
)
assert(unconfirmed.status === 400, `unconfirmed capture expected 400, got ${unconfirmed.status}`)
report.steps.push({ name: 'spider-not-called-on-failed-capture', status: unconfirmed.status })

const mockHealthAfter = await getJson(`${mock}/health`)
const executionsAfter = Array.isArray(mockHealthAfter.json?.recentExecutions)
  ? mockHealthAfter.json.recentExecutions.length
  : 0
report.steps.push({
  name: 'mock-executions-delta',
  before: executionsBefore,
  after: executionsAfter,
  note: 'SegSense capture endpoints do not increment mock executions; Spider journeys may.',
})

const segsenseInfo = await getJson(`${bff}/api/v1/system/info`)
assert(segsenseInfo.status === 200, 'segsense info failed')
report.steps.push({ name: 'segsense-info', status: segsenseInfo.status })

writeFileSync(path.join(outDir, 'http-proof.json'), JSON.stringify(report, null, 2), 'utf8')
console.log(JSON.stringify({ ok: true, out: path.join(outDir, 'http-proof.json'), cropFetched: crop.json?.publicStatus }, null, 2))
