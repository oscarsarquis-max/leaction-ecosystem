import { generateKeyPair, exportPKCS8, exportSPKI, importPKCS8, importSPKI, type KeyLike } from 'jose'
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs'
import { join } from 'node:path'

const KEY_DIR = join(process.cwd(), '.keys')
const PRIV_PATH = join(KEY_DIR, 'jwt-rsa-private.pem')
const PUB_PATH = join(KEY_DIR, 'jwt-rsa-public.pem')

let privateKey: KeyLike | null = null
let publicKey: KeyLike | null = null

/**
 * Chaves RS256 — PEM via env (prod) ou arquivo local `.keys/` (dev).
 * Nunca logar o conteúdo das chaves.
 */
export async function getJwtKeys(): Promise<{ privateKey: KeyLike; publicKey: KeyLike }> {
  if (privateKey && publicKey) return { privateKey, publicKey }

  const envPriv = process.env.JWT_PRIVATE_KEY_PEM?.replace(/\\n/g, '\n')
  const envPub = process.env.JWT_PUBLIC_KEY_PEM?.replace(/\\n/g, '\n')

  if (envPriv && envPub) {
    privateKey = await importPKCS8(envPriv, 'RS256')
    publicKey = await importSPKI(envPub, 'RS256')
    return { privateKey, publicKey }
  }

  if (!existsSync(PRIV_PATH) || !existsSync(PUB_PATH)) {
    mkdirSync(KEY_DIR, { recursive: true })
    const { privateKey: priv, publicKey: pub } = await generateKeyPair('RS256', {
      modulusLength: 2048,
      extractable: true,
    })
    writeFileSync(PRIV_PATH, await exportPKCS8(priv), { mode: 0o600 })
    writeFileSync(PUB_PATH, await exportSPKI(pub), { mode: 0o644 })
  }

  privateKey = await importPKCS8(readFileSync(PRIV_PATH, 'utf8'), 'RS256')
  publicKey = await importSPKI(readFileSync(PUB_PATH, 'utf8'), 'RS256')
  return { privateKey, publicKey }
}
