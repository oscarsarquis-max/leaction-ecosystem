/**
 * Certificados — validação acadêmica + PDF (pdfkit) 100% server-side.
 * Sem página pública de verificação / QR (escopo v1).
 *
 * Regra provisória (gap Assessment no SDD): averageGrade <= 0 = curso sem avaliação;
 * só progresso 100% basta. Quando Assessment existir, amarrar exigência de nota à
 * existência de avaliações no curso — não a este sentinel.
 */
import PDFDocument from 'pdfkit'
import { prisma } from './prisma.js'
import { decryptPii } from './crypto.js'

export type CertificateEligibility = {
  eligible: true
  courseId: string
  courseTitle: string
  studentName: string
  progressPct: number
  averageGrade: number
  minGrade: number
  gradeRequired: boolean
  issuedAt: Date
}

export type CertificateDenial = {
  eligible: false
  reason: 'course_not_found' | 'enrollment_required' | 'incomplete_progress' | 'grade_below_minimum'
  progress_pct: number
  average_grade: number
  min_grade: number
  grade_required: boolean
}

/**
 * Controles, overrides/isolamentos bidirecionais e espaços de largura zero —
 * evitam “parecer” outro texto no PDF sem alterar o banco.
 */
export function sanitizePdfText(input: string, maxLen = 200): string {
  return input
    .normalize('NFC')
    .replace(/[\u0000-\u001F\u007F-\u009F]/g, '')
    .replace(/[\u200E\u200F\u202A-\u202E\u2066-\u2069]/g, '')
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .replace(/[\\()]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, maxLen)
}

export function asciiFilename(base: string): string {
  return (
    base
      .normalize('NFKD')
      .replace(/[^\w.-]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 80) || 'certificate'
  )
}

export async function evaluateCertificateEligibility(
  userId: string,
  courseId: string,
): Promise<CertificateEligibility | CertificateDenial> {
  const course = await prisma.course.findFirst({
    where: { id: courseId, organizationId: 'global', isActive: true },
  })
  if (!course) {
    return {
      eligible: false,
      reason: 'course_not_found',
      progress_pct: 0,
      average_grade: 0,
      min_grade: 70,
      grade_required: false,
    }
  }

  // RN09: configurável por curso (default 70 no schema).
  const minGrade = course.minGrade

  const user = await prisma.user.findUnique({ where: { id: userId } })
  if (!user) {
    return {
      eligible: false,
      reason: 'enrollment_required',
      progress_pct: 0,
      average_grade: 0,
      min_grade: minGrade,
      grade_required: false,
    }
  }

  const enrollment = await prisma.enrollment.findUnique({
    where: { userId_courseId: { userId, courseId } },
  })
  if (!enrollment && !course.isFree) {
    return {
      eligible: false,
      reason: 'enrollment_required',
      progress_pct: 0,
      average_grade: 0,
      min_grade: minGrade,
      grade_required: false,
    }
  }

  if (enrollment?.status === 'REVOKED') {
    return {
      eligible: false,
      reason: 'enrollment_required',
      progress_pct: enrollment.progressPct,
      average_grade: enrollment.averageGrade,
      min_grade: minGrade,
      grade_required: false,
    }
  }

  const totalLessons = await prisma.lesson.count({
    where: { module: { courseId } },
  })
  const completedLessons = await prisma.lessonCompletion.count({
    where: { userId, lesson: { module: { courseId } } },
  })
  const progressPct =
    totalLessons === 0 ? 0 : Math.min(100, (completedLessons / totalLessons) * 100)

  const averageGrade = enrollment?.averageGrade ?? 0
  // Provisório: <=0 ⇒ sem avaliação registrada (ver cabeçalho do arquivo).
  const gradeRequired = averageGrade > 0

  if (progressPct < 100) {
    return {
      eligible: false,
      reason: 'incomplete_progress',
      progress_pct: progressPct,
      average_grade: averageGrade,
      min_grade: minGrade,
      grade_required: gradeRequired,
    }
  }

  if (gradeRequired && averageGrade < minGrade) {
    return {
      eligible: false,
      reason: 'grade_below_minimum',
      progress_pct: progressPct,
      average_grade: averageGrade,
      min_grade: minGrade,
      grade_required: true,
    }
  }

  const studentName = decryptPii(user.nameEnc)

  return {
    eligible: true,
    courseId: course.id,
    courseTitle: course.title,
    studentName,
    progressPct,
    averageGrade,
    minGrade,
    gradeRequired,
    issuedAt: new Date(),
  }
}

export async function generateCertificatePdf(data: CertificateEligibility): Promise<Buffer> {
  const studentName = sanitizePdfText(data.studentName, 120)
  const courseTitle = sanitizePdfText(data.courseTitle, 160)
  const issued = data.issuedAt.toISOString().slice(0, 10)
  const gradeLine = data.gradeRequired
    ? `Nota: ${Number(data.averageGrade.toFixed(1))}%  |  Minimo: ${data.minGrade}%`
    : 'Curso sem avaliacao registrada'

  return new Promise((resolve, reject) => {
    const doc = new PDFDocument({
      size: 'A4',
      layout: 'landscape',
      margin: 48,
      info: {
        Title: sanitizePdfText(`Certificado — ${courseTitle}`, 180),
        Author: 'LEACTIONA',
        Subject: 'Certificate of completion',
      },
    })
    const chunks: Buffer[] = []
    doc.on('data', (c: Buffer) => chunks.push(c))
    doc.on('end', () => resolve(Buffer.concat(chunks)))
    doc.on('error', reject)

    doc.fontSize(28).text('LEACTIONA', { align: 'center' })
    doc.moveDown(0.5)
    doc.fontSize(20).text('Certificado de Conclusao', { align: 'center' })
    doc.moveDown(1.5)
    doc.fontSize(14).text('Certificamos que', { align: 'center' })
    doc.moveDown(0.5)
    doc.fontSize(22).text(studentName || 'Aluno', { align: 'center' })
    doc.moveDown(0.8)
    doc.fontSize(14).text('concluiu com aproveitamento o curso', { align: 'center' })
    doc.moveDown(0.5)
    doc.fontSize(18).text(courseTitle, { align: 'center' })
    doc.moveDown(1.2)
    doc
      .fontSize(12)
      .text(`Progresso: 100%  |  ${gradeLine}  |  Emitido: ${issued}`, { align: 'center' })
    doc.moveDown(1.5)
    doc
      .fontSize(9)
      .fillColor('#444444')
      .text('Documento gerado sob demanda para o titular autenticado. Sem verificacao publica.', {
        align: 'center',
      })

    doc.end()
  })
}

export async function buildCertificateDownload(
  userId: string,
  courseId: string,
): Promise<{ buffer: Buffer; filename: string; filenameStar: string; courseId: string }> {
  const result = await evaluateCertificateEligibility(userId, courseId)
  if (!result.eligible) {
    throw Object.assign(new Error(result.reason), {
      statusCode: result.reason === 'course_not_found' ? 404 : 403,
      details: {
        progress_pct: result.progress_pct,
        average_grade: result.average_grade,
        min_grade: result.min_grade,
        grade_required: result.grade_required,
      },
    })
  }

  const buffer = await generateCertificatePdf(result)
  const ascii = asciiFilename(`certificate-${result.courseId}`)
  const utf8Name = `${asciiFilename(result.courseTitle)}.pdf`
  return {
    buffer,
    filename: `${ascii}.pdf`,
    filenameStar: utf8Name,
    courseId: result.courseId,
  }
}
