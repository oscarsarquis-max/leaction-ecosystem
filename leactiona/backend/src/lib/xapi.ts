/**
 * Validação/sanitização de statements xAPI (API8 / XSS).
 * Single-tenant: actor homepage fixo leactiona.com.br.
 */
import { z } from 'zod'

const MAX_STRING = 500
const MAX_IRI = 2000

const iri = z.string().url().max(MAX_IRI)

function stripHtml(input: string): string {
  return input
    .replace(/<[^>]*>/g, '')
    .replace(/javascript:/gi, '')
    .replace(/on\w+=/gi, '')
    .trim()
    .slice(0, MAX_STRING)
}

const agentSchema = z.object({
  objectType: z.literal('Agent').optional(),
  name: z.string().max(MAX_STRING).optional(),
  mbox: z
    .string()
    .regex(/^mailto:[^\s<>]+@[^\s<>]+$/i)
    .max(320)
    .optional(),
  account: z
    .object({
      homePage: z.string().url().max(MAX_IRI),
      name: z.string().min(1).max(200),
    })
    .optional(),
}).refine((a) => Boolean(a.mbox || a.account), {
  message: 'actor precisa de mbox ou account',
})

const verbSchema = z.object({
  id: iri,
  display: z.record(z.string().max(MAX_STRING)).optional(),
})

const objectSchema = z.object({
  id: iri,
  objectType: z.enum(['Activity', 'Agent', 'Group', 'SubStatement', 'StatementRef']).optional(),
  definition: z
    .object({
      name: z.record(z.string().max(MAX_STRING)).optional(),
      description: z.record(z.string().max(2000)).optional(),
      type: iri.optional(),
    })
    .optional(),
})

const resultSchema = z
  .object({
    score: z
      .object({
        scaled: z.number().min(-1).max(1).optional(),
        raw: z.number().optional(),
        min: z.number().optional(),
        max: z.number().optional(),
      })
      .optional(),
    success: z.boolean().optional(),
    completion: z.boolean().optional(),
    duration: z.string().max(64).optional(),
    response: z.string().max(2000).optional(),
  })
  .optional()

export const xapiStatementSchema = z.object({
  id: z.string().uuid().optional(),
  actor: agentSchema,
  verb: verbSchema,
  object: objectSchema,
  result: resultSchema,
  timestamp: z.string().min(10).max(40).optional(),
  context: z
    .object({
      platform: z.string().max(100).optional(),
      language: z.string().max(16).optional(),
      extensions: z.record(z.unknown()).optional(),
    })
    .optional(),
})

export type XapiStatement = z.infer<typeof xapiStatementSchema>

export function sanitizeStatement(raw: unknown): XapiStatement {
  const parsed = xapiStatementSchema.parse(raw)
  if (parsed.actor.name) parsed.actor.name = stripHtml(parsed.actor.name)
  if (parsed.verb.display) {
    for (const k of Object.keys(parsed.verb.display)) {
      parsed.verb.display[k] = stripHtml(parsed.verb.display[k]!)
    }
  }
  if (parsed.object.definition?.name) {
    for (const k of Object.keys(parsed.object.definition.name)) {
      parsed.object.definition.name[k] = stripHtml(parsed.object.definition.name[k]!)
    }
  }
  if (parsed.result?.response) {
    parsed.result.response = stripHtml(parsed.result.response)
  }
  // Single-tenant: força homepage da academia
  if (parsed.actor.account) {
    parsed.actor.account.homePage = 'https://leactiona.com.br'
  }
  return parsed
}

export const VERB_COMPLETED = 'http://adlnet.gov/expapi/verbs/completed'
export const VERB_PROGRESSED = 'http://adlnet.gov/expapi/verbs/progressed'
export const VERB_ANSWERED = 'http://adlnet.gov/expapi/verbs/answered'

export function buildVideoCompletedStatement(input: {
  userId: string
  lessonId: string
  lessonTitle: string
  durationSec?: number
}): XapiStatement {
  return sanitizeStatement({
    actor: {
      objectType: 'Agent',
      account: {
        homePage: 'https://leactiona.com.br',
        name: input.userId,
      },
    },
    verb: {
      id: VERB_COMPLETED,
      display: { 'pt-BR': 'completou', 'en-US': 'completed' },
    },
    object: {
      id: `https://leactiona.com.br/lessons/${input.lessonId}`,
      objectType: 'Activity',
      definition: {
        name: { 'pt-BR': stripHtml(input.lessonTitle) },
        type: 'http://adlnet.gov/expapi/activities/media',
      },
    },
    result: {
      completion: true,
      success: true,
      duration: input.durationSec != null ? `PT${Math.round(input.durationSec)}S` : undefined,
    },
    timestamp: new Date().toISOString(),
    context: {
      platform: 'leactiona',
      language: 'pt-BR',
      extensions: {
        'https://leactiona.com.br/xapi/ext/organization': 'global',
      },
    },
  })
}
