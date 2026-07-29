import type { FastifyPluginAsync } from 'fastify'
import { authenticate } from '../plugins/auth.js'
import {
  buildCertificateDownload,
  evaluateCertificateEligibility,
} from '../lib/certificates.js'

/**
 * Certificados — stream PDF autenticado (sem URL pública / QR).
 * Rate limit restrito: geração on-the-fly é custo alto (API4).
 */
export const certificateRoutes: FastifyPluginAsync = async (app) => {
  app.get<{ Params: { courseId: string } }>(
    '/api/v1/certificates/:courseId/status',
    { preHandler: authenticate },
    async (req) => {
      const result = await evaluateCertificateEligibility(
        req.authUser!.id,
        req.params.courseId,
      )
      if (!result.eligible) {
        return {
          eligible: false,
          reason: result.reason,
          progress_pct: result.progress_pct,
          average_grade: result.average_grade,
          min_grade: result.min_grade,
          grade_required: result.grade_required,
        }
      }
      return {
        eligible: true,
        progress_pct: result.progressPct,
        average_grade: result.averageGrade,
        min_grade: result.minGrade,
        grade_required: result.gradeRequired,
      }
    },
  )

  app.get<{ Params: { courseId: string } }>(
    '/api/v1/certificates/:courseId/download',
    {
      preHandler: authenticate,
      config: {
        rateLimit: {
          max: Number(process.env.CERT_RATE_LIMIT_MAX ?? 10),
          timeWindow: '1 minute',
        },
      },
    },
    async (req, reply) => {
      try {
        const { buffer, filename, filenameStar, courseId } = await buildCertificateDownload(
          req.authUser!.id,
          req.params.courseId,
        )
        req.log.info(
          { event: 'certificate_download', user_id: req.authUser!.id, course_id: courseId },
          'certificate_streamed',
        )
        const star = encodeURIComponent(filenameStar)
        return reply
          .header('Content-Type', 'application/pdf')
          .header(
            'Content-Disposition',
            `attachment; filename="${filename}"; filename*=UTF-8''${star}`,
          )
          .header('Cache-Control', 'no-store, private')
          .header('X-Content-Type-Options', 'nosniff')
          .send(buffer)
      } catch (e) {
        const err = e as Error & {
          statusCode?: number
          details?: Record<string, number | boolean>
        }
        return reply.code(err.statusCode ?? 500).send({
          error: err.message,
          ...(err.details ? { details: err.details } : {}),
        })
      }
    },
  )
}
