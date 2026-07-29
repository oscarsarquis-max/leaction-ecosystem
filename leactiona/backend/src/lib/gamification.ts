/**
 * Gamificação 100% server-side — pontos/badges/ranking.
 * Idempotência via LessonCompletion @@unique + advisory lock por usuário.
 */
import { Prisma } from '@prisma/client'
import { prisma } from './prisma.js'
import { canAccessLessonContent } from './access.js'

export const POINTS_COURSE_COMPLETE_BONUS = 500
export const POINTS_PERFECT_SCORE = 50

export type CompleteLessonResult = {
  idempotent: boolean
  points_awarded: number
  total_points: number
  rank: number
  progress_pct: number
  badges_awarded: string[]
  lesson_id: string
  course_id: string
}

function courseCompleteBadgeCode(courseId: string): string {
  return `course_complete_${courseId}`
}

function perfectScoreBadgeCode(courseId: string): string {
  return `perfect_score_${courseId}`
}

async function ensureCourseBadges(
  tx: Prisma.TransactionClient,
  courseId: string,
  courseTitle: string,
): Promise<void> {
  await tx.badge.upsert({
    where: {
      organizationId_code: {
        organizationId: 'global',
        code: courseCompleteBadgeCode(courseId),
      },
    },
    create: {
      organizationId: 'global',
      code: courseCompleteBadgeCode(courseId),
      title: `Mestre do Curso — ${courseTitle}`,
      description: 'Concluiu 100% do curso',
      pointsAward: POINTS_COURSE_COMPLETE_BONUS,
    },
    update: { title: `Mestre do Curso — ${courseTitle}` },
  })
  await tx.badge.upsert({
    where: {
      organizationId_code: {
        organizationId: 'global',
        code: perfectScoreBadgeCode(courseId),
      },
    },
    create: {
      organizationId: 'global',
      code: perfectScoreBadgeCode(courseId),
      title: `Nota máxima — ${courseTitle}`,
      description: 'Atingiu 100% na avaliação do curso',
      pointsAward: POINTS_PERFECT_SCORE,
    },
    update: {},
  })
}

async function ensureProfile(tx: Prisma.TransactionClient, userId: string) {
  return tx.gamificationProfile.upsert({
    where: { userId },
    create: { userId, points: 0, rank: 0 },
    update: {},
  })
}

export async function recomputeRanks(tx: Prisma.TransactionClient): Promise<void> {
  const profiles = await tx.gamificationProfile.findMany({
    orderBy: [{ points: 'desc' }, { createdAt: 'asc' }],
    select: { id: true },
  })
  for (let i = 0; i < profiles.length; i++) {
    await tx.gamificationProfile.update({
      where: { id: profiles[i]!.id },
      data: { rank: i + 1 },
    })
  }
}

async function awardBadgeOnce(
  tx: Prisma.TransactionClient,
  userId: string,
  badgeCode: string,
): Promise<{ code: string; points: number } | null> {
  const badge = await tx.badge.findUnique({
    where: { organizationId_code: { organizationId: 'global', code: badgeCode } },
  })
  if (!badge) return null
  try {
    await tx.userBadge.create({
      data: { userId, badgeId: badge.id },
    })
    if (badge.pointsAward > 0) {
      await tx.gamificationProfile.update({
        where: { userId },
        data: { points: { increment: badge.pointsAward } },
      })
    }
    return { code: badge.code, points: badge.pointsAward }
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === 'P2002') {
      return null
    }
    throw e
  }
}

export async function completeLessonForUser(
  userId: string,
  role: string,
  lessonId: string,
): Promise<CompleteLessonResult> {
  const access = await canAccessLessonContent({ userId, role, lessonId })
  if (!access.allowed) {
    throw Object.assign(new Error('forbidden_content'), {
      statusCode: 403,
      reason: access.reason,
    })
  }

  return prisma.$transaction(
    async (tx) => {
      await tx.$executeRaw`SELECT pg_advisory_xact_lock(hashtext(${`gamification:${userId}`}))`

      const lesson = await tx.lesson.findUnique({
        where: { id: lessonId },
        include: { module: { include: { course: true } } },
      })
      if (!lesson || lesson.module.course.organizationId !== 'global') {
        throw Object.assign(new Error('lesson_not_found'), { statusCode: 404 })
      }

      const courseId = lesson.module.courseId
      const course = lesson.module.course
      await ensureCourseBadges(tx, courseId, course.title)
      await ensureProfile(tx, userId)

      const existing = await tx.lessonCompletion.findUnique({
        where: { userId_lessonId: { userId, lessonId } },
      })

      if (existing) {
        const profile = await tx.gamificationProfile.findUniqueOrThrow({ where: { userId } })
        const enrollment = await tx.enrollment.findUnique({
          where: { userId_courseId: { userId, courseId } },
        })
        return {
          idempotent: true,
          points_awarded: 0,
          total_points: profile.points,
          rank: profile.rank,
          progress_pct: enrollment?.progressPct ?? 0,
          badges_awarded: [],
          lesson_id: lessonId,
          course_id: courseId,
        }
      }

      const points = lesson.pointsOnComplete

      try {
        await tx.lessonCompletion.create({
          data: { userId, lessonId, pointsAwarded: points },
        })
      } catch (e) {
        if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === 'P2002') {
          const profile = await tx.gamificationProfile.findUniqueOrThrow({ where: { userId } })
          const enrollment = await tx.enrollment.findUnique({
            where: { userId_courseId: { userId, courseId } },
          })
          return {
            idempotent: true,
            points_awarded: 0,
            total_points: profile.points,
            rank: profile.rank,
            progress_pct: enrollment?.progressPct ?? 0,
            badges_awarded: [],
            lesson_id: lessonId,
            course_id: courseId,
          }
        }
        throw e
      }

      await tx.gamificationProfile.update({
        where: { userId },
        data: { points: { increment: points } },
      })

      const totalLessons = await tx.lesson.count({
        where: { module: { courseId } },
      })
      const completedLessons = await tx.lessonCompletion.count({
        where: { userId, lesson: { module: { courseId } } },
      })
      const progressPct =
        totalLessons === 0 ? 0 : Math.min(100, (completedLessons / totalLessons) * 100)

      let enrollment = await tx.enrollment.findUnique({
        where: { userId_courseId: { userId, courseId } },
      })
      if (!enrollment && course.isFree) {
        enrollment = await tx.enrollment.create({
          data: {
            userId,
            courseId,
            isPaidAccess: false,
            status: progressPct >= 100 ? 'COMPLETED' : 'ACTIVE',
            progressPct,
          },
        })
      } else if (enrollment) {
        enrollment = await tx.enrollment.update({
          where: { id: enrollment.id },
          data: {
            progressPct,
            status: progressPct >= 100 ? 'COMPLETED' : enrollment.status,
          },
        })
      }

      const badgesAwarded: string[] = []
      if (progressPct >= 100) {
        const awarded = await awardBadgeOnce(tx, userId, courseCompleteBadgeCode(courseId))
        if (awarded) badgesAwarded.push(awarded.code)
      }

      await recomputeRanks(tx)
      const profile = await tx.gamificationProfile.findUniqueOrThrow({ where: { userId } })

      return {
        idempotent: false,
        points_awarded: points,
        total_points: profile.points,
        rank: profile.rank,
        progress_pct: enrollment?.progressPct ?? progressPct,
        badges_awarded: badgesAwarded,
        lesson_id: lessonId,
        course_id: courseId,
      }
    },
    { isolationLevel: Prisma.TransactionIsolationLevel.ReadCommitted },
  )
}

export async function recordAssessmentScore(opts: {
  userId: string
  courseId: string
  score: number
}): Promise<{
  average_grade: number
  points_awarded: number
  total_points: number
  rank: number
  badges_awarded: string[]
}> {
  if (opts.score < 0 || opts.score > 100 || Number.isNaN(opts.score)) {
    throw Object.assign(new Error('invalid_score'), { statusCode: 400 })
  }

  return prisma.$transaction(async (tx) => {
    await tx.$executeRaw`SELECT pg_advisory_xact_lock(hashtext(${`gamification:${opts.userId}`}))`

    const course = await tx.course.findFirst({
      where: { id: opts.courseId, organizationId: 'global' },
    })
    if (!course) {
      throw Object.assign(new Error('course_not_found'), { statusCode: 404 })
    }

    await ensureCourseBadges(tx, course.id, course.title)
    await ensureProfile(tx, opts.userId)

    const enrollment = await tx.enrollment.findUnique({
      where: { userId_courseId: { userId: opts.userId, courseId: opts.courseId } },
    })
    if (!enrollment && !course.isFree) {
      throw Object.assign(new Error('enrollment_required'), { statusCode: 403 })
    }

    const previous = enrollment?.averageGrade ?? 0
    const average =
      enrollment && enrollment.averageGrade > 0 ? (previous + opts.score) / 2 : opts.score

    if (enrollment) {
      await tx.enrollment.update({
        where: { id: enrollment.id },
        data: { averageGrade: average },
      })
    } else {
      await tx.enrollment.create({
        data: {
          userId: opts.userId,
          courseId: opts.courseId,
          isPaidAccess: false,
          averageGrade: average,
          status: 'ACTIVE',
        },
      })
    }

    const badgesAwarded: string[] = []
    let pointsAwarded = 0
    if (opts.score >= 100) {
      const awarded = await awardBadgeOnce(tx, opts.userId, perfectScoreBadgeCode(course.id))
      if (awarded) {
        badgesAwarded.push(awarded.code)
        pointsAwarded = awarded.points
      }
    } else if (opts.score >= course.minGrade && previous === 0) {
      const pts = Math.floor(opts.score / 10)
      await tx.gamificationProfile.update({
        where: { userId: opts.userId },
        data: { points: { increment: pts } },
      })
      pointsAwarded = pts
    }

    await recomputeRanks(tx)
    const profile = await tx.gamificationProfile.findUniqueOrThrow({
      where: { userId: opts.userId },
    })

    return {
      average_grade: average,
      points_awarded: pointsAwarded,
      total_points: profile.points,
      rank: profile.rank,
      badges_awarded: badgesAwarded,
    }
  })
}

export async function getRanking(limit = 50) {
  const profiles = await prisma.gamificationProfile.findMany({
    orderBy: [{ points: 'desc' }, { createdAt: 'asc' }],
    take: Math.min(limit, 200),
    select: { userId: true, points: true, rank: true },
  })
  return profiles.map((p) => ({
    user_id: p.userId,
    points: p.points,
    rank: p.rank,
  }))
}

export { courseCompleteBadgeCode, perfectScoreBadgeCode }
