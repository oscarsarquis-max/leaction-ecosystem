import { createHash } from 'node:crypto'

/** Lista offline mínima de senhas expostas/comuns (ASVS — verificação de dicionário). */
const COMMON_PASSWORDS = new Set(
  [
    'password',
    'password123',
    'password1234',
    '123456789012',
    'qwertyuiopas',
    'adminadmin12',
    'letmein12345',
    'welcome12345',
    'changeme1234',
    'leactiona123',
    'senha1234567',
    'senhaforte123',
    'abc123456789',
    'iloveyou1234',
    'monkey123456',
    'dragon123456',
    'master123456',
    'login1234567',
    'passw0rd1234',
    'p@ssw0rd1234',
  ].map((p) => p.toLowerCase()),
)

export type PasswordPolicyError = { code: string; message: string }

export function validatePasswordPolicy(password: string): PasswordPolicyError | null {
  if (typeof password !== 'string' || password.length < 12) {
    return {
      code: 'password_too_short',
      message: 'Senha deve ter no mínimo 12 caracteres (ASVS Level 3).',
    }
  }
  if (password.length > 128) {
    return { code: 'password_too_long', message: 'Senha excede o tamanho máximo permitido.' }
  }
  const lower = password.toLowerCase()
  if (COMMON_PASSWORDS.has(lower)) {
    return {
      code: 'password_compromised',
      message: 'Senha consta em dicionário de senhas expostas/comuns.',
    }
  }
  // Classes mínimas: letra + dígito
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
    return {
      code: 'password_complexity',
      message: 'Senha deve conter letras e números.',
    }
  }
  return null
}

/** SHA-256 hex — para armazenar refresh tokens (não reutilizáveis em claro). */
export function hashOpaqueToken(token: string): string {
  return createHash('sha256').update(token).digest('hex')
}
