import type { EnrollmentStatus } from '@prisma/client'
import { prisma } from './prisma.js'

export type AccessDecision =
  | { allowed: true; reason: 'free' | 'paid_enrollment' | 'staff' }
  | { allowed: false; reason: 'no_enrollment' | 'unpaid' | 'revoked' | 'not_found' }

/**
 * BOLA — libera conteúdo se Course.is_free OU Enrollment ACTIVE com is_paid_access.
 * Staff (ADMIN/TEACHER) bypassa para gestão. Sem gateway de pagamento.
 */
export async function canAccessCourseContent(opts: {
  userId: string
  role: string
  courseId: string
}): Promise<AccessDecision> {
  const course = await prisma.course.findFirst({
    where: { id: opts.courseId, organizationId: 'global' },
  })
  if (!course || !course.isActive) {
    return { allowed: false, reason: 'not_found' }
  }

  if (opts.role === 'ADMIN' || opts.role === 'TEACHER') {
    return { allowed: true, reason: 'staff' }
  }

  if (course.isFree) {
    return { allowed: true, reason: 'free' }
  }

  const enrollment = await prisma.enrollment.findUnique({
    where: {
      userId_courseId: { userId: opts.userId, courseId: opts.courseId },
    },
  })

  if (!enrollment) {
    return { allowed: false, reason: 'no_enrollment' }
  }
  if (enrollment.status !== ('ACTIVE' satisfies EnrollmentStatus) && enrollment.status !== 'COMPLETED') {
    return { allowed: false, reason: 'revoked' }
  }
  if (!enrollment.isPaidAccess) {
    return { allowed: false, reason: 'unpaid' }
  }
  return { allowed: true, reason: 'paid_enrollment' }
}

export async function canAccessLessonContent(opts: {
  userId: string
  role: string
  lessonId: string
}): Promise<AccessDecision & { courseId?: string }> {
  const lesson = await prisma.lesson.findUnique({
    where: { id: opts.lessonId },
    include: { module: { include: { course: true } } },
  })
  if (!lesson || lesson.module.course.organizationId !== 'global') {
    return { allowed: false, reason: 'not_found' }
  }
  const decision = await canAccessCourseContent({
    userId: opts.userId,
    role: opts.role,
    courseId: lesson.module.courseId,
  })
  return { ...decision, courseId: lesson.module.courseId }
}
