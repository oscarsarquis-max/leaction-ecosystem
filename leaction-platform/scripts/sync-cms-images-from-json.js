/**
 * Garante que imagens referenciadas no JSON do Micro-CMS existam no S3.
 * Procura arquivos em services/gateway-api/cms-uploads/images (upload local).
 *
 * Uso:
 *   node scripts/sync-cms-images-from-json.js --file=./.deploy-secrets/cms-inove4us.json
 *   node scripts/sync-cms-images-from-json.js --file=... --dry-run
 */
'use strict';

const fs = require('fs');
const path = require('path');

require('dotenv').config({ path: path.join(__dirname, '..', '.env'), override: false });
require('dotenv').config({
  path: path.join(__dirname, '..', 'services', 'gateway-api', '.env'),
  override: false,
});

const cmsS3 = require('../services/gateway-api/lib/cms-s3-storage');

const LOCAL_IMAGES_DIR = path.join(
  __dirname,
  '..',
  'services',
  'gateway-api',
  'cms-uploads',
  'images'
);

function argValue(name) {
  const hit = process.argv.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3).trim() : null;
}

function hasFlag(name) {
  return process.argv.includes(`--${name}`);
}

function collectStrings(node, out = []) {
  if (typeof node === 'string') {
    out.push(node);
    return out;
  }
  if (Array.isArray(node)) {
    for (const item of node) collectStrings(item, out);
    return out;
  }
  if (node && typeof node === 'object') {
    for (const v of Object.values(node)) collectStrings(v, out);
  }
  return out;
}

function extractImageFilenames(payload) {
  const found = new Set();
  for (const s of collectStrings(payload)) {
    const trimmed = String(s || '').trim();
    if (!trimmed) continue;
    // /images/foo.jpg  ou  https://host/images/foo.jpg  ou  só foo.jpg em campos típicos
    let m = trimmed.match(/\/images\/([^/?#]+)/i);
    if (m) {
      found.add(path.basename(m[1]));
      continue;
    }
    if (/^https?:\/\//i.test(trimmed) && /amazonaws\.com/i.test(trimmed)) {
      const base = path.basename(trimmed.split('?')[0]);
      if (/\.(png|jpe?g|gif|webp|svg)$/i.test(base)) found.add(base);
    }
  }
  return [...found];
}

function guessMime(filename) {
  const ext = path.extname(filename).toLowerCase();
  const map = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.svg': 'image/svg+xml',
  };
  return map[ext] || 'application/octet-stream';
}

async function main() {
  const file = argValue('file');
  if (!file) {
    console.error('Uso: node scripts/sync-cms-images-from-json.js --file=cms.json [--dry-run]');
    process.exit(1);
  }
  if (!cmsS3.isCmsS3Enabled()) {
    console.error('CMS_S3_BUCKET ausente no .env — não dá para sincronizar imagens.');
    process.exit(1);
  }

  const abs = path.resolve(file);
  const payload = JSON.parse(fs.readFileSync(abs, 'utf8'));
  const names = extractImageFilenames(payload);
  console.log(`Referências de imagem no JSON: ${names.length}`);
  if (!names.length) {
    console.log('Nada a sincronizar.');
    return;
  }

  const dry = hasFlag('dry-run');
  let uploaded = 0;
  let skipped = 0;
  let missing = 0;

  for (const name of names) {
    const exists = await cmsS3.cmsObjectExists(name);
    if (exists) {
      console.log(`  skip (já no S3) ${name}`);
      skipped += 1;
      continue;
    }
    const localPath = path.join(LOCAL_IMAGES_DIR, name);
    if (!fs.existsSync(localPath)) {
      console.warn(`  MISSING local+S3 ${name}`);
      missing += 1;
      continue;
    }
    if (dry) {
      console.log(`  would-upload ${name}`);
      uploaded += 1;
      continue;
    }
    const buf = fs.readFileSync(localPath);
    const saved = await cmsS3.putCmsImageExactFilename(buf, guessMime(name), name);
    console.log(`  OK S3 ${name} → ${saved.objectKey}`);
    uploaded += 1;
  }

  console.log(
    `Resumo: uploaded/would=${uploaded} already=${skipped} missing=${missing}`
  );
  if (missing > 0) process.exitCode = 2;
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
