'use strict';

/**
 * Upload CMS → S3 (imagens + snapshot do site config).
 * Env: CMS_S3_BUCKET, CMS_S3_PREFIX, CMS_S3_REGION, CMS_S3_PUBLIC_URL
 *
 * Site config (landing JSON) fica em:
 *   s3://{bucket}/{prefix}/site/{config_key}.json
 * Assim o conteúdo sobrevive a redeploy / wipe acidental do Postgres.
 */

const path = require('path');
const {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
  HeadObjectCommand,
} = require('@aws-sdk/client-s3');

let s3Client = null;

function isCmsS3Enabled() {
  return Boolean((process.env.CMS_S3_BUCKET || '').trim());
}

function getBucket() {
  return (process.env.CMS_S3_BUCKET || '').trim();
}

function getRegion() {
  return (
    process.env.CMS_S3_REGION ||
    process.env.AWS_REGION ||
    process.env.AWS_DEFAULT_REGION ||
    'us-east-2'
  );
}

function getPrefix() {
  const raw = (process.env.CMS_S3_PREFIX || 'cms').trim();
  return raw.replace(/^\/+|\/+$/g, '');
}

function getS3Client() {
  if (!s3Client) {
    s3Client = new S3Client({ region: getRegion() });
  }
  return s3Client;
}

function buildCmsFilename(originalName) {
  const ext = path.extname(originalName || '').toLowerCase();
  const base =
    path
      .basename(originalName || 'upload', ext)
      .replace(/[^a-zA-Z0-9._-]/g, '_')
      .slice(0, 80) || 'upload';
  return `${Date.now()}-${base}${ext}`;
}

function buildObjectKey(filename) {
  const prefix = getPrefix();
  return prefix ? `${prefix}/${filename}` : filename;
}

function buildSiteConfigObjectKey(configKey) {
  const key = String(configKey || 'default')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._-]/g, '_');
  return buildObjectKey(`site/${key || 'default'}.json`);
}

function getPublicUrlForKey(objectKey) {
  const override = (process.env.CMS_S3_PUBLIC_URL || '').trim().replace(/\/+$/, '');
  if (override) {
    return `${override}/${objectKey}`;
  }
  const bucket = getBucket();
  const region = getRegion();
  return `https://${bucket}.s3.${region}.amazonaws.com/${objectKey}`;
}

function getPublicUrlForFilename(filename) {
  return getPublicUrlForKey(buildObjectKey(filename));
}

/** URL relativa compatível com o padrão PanelDX (/images/...). */
function getCmsPersistedUrl(filename) {
  return `/images/${filename}`;
}

async function streamToBuffer(body) {
  if (!body) return Buffer.alloc(0);
  if (Buffer.isBuffer(body)) return body;
  if (typeof body.transformToByteArray === 'function') {
    return Buffer.from(await body.transformToByteArray());
  }
  const chunks = [];
  for await (const chunk of body) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return Buffer.concat(chunks);
}

async function uploadCmsImage(buffer, mimetype, originalName) {
  if (!isCmsS3Enabled()) {
    throw new Error('CMS_S3_BUCKET não configurado.');
  }
  if (!buffer || !buffer.length) {
    throw new Error('Arquivo vazio.');
  }

  const filename = buildCmsFilename(originalName);
  const objectKey = buildObjectKey(filename);
  const bucket = getBucket();

  await getS3Client().send(
    new PutObjectCommand({
      Bucket: bucket,
      Key: objectKey,
      Body: buffer,
      ContentType: mimetype || 'application/octet-stream',
      CacheControl: 'public, max-age=31536000, immutable',
    })
  );

  return {
    filename,
    objectKey,
    publicUrl: getPublicUrlForKey(objectKey),
    persistedUrl: getCmsPersistedUrl(filename),
  };
}

async function cmsObjectExists(filename) {
  if (!isCmsS3Enabled() || !filename) {
    return false;
  }
  try {
    await getS3Client().send(
      new HeadObjectCommand({
        Bucket: getBucket(),
        Key: buildObjectKey(filename),
      })
    );
    return true;
  } catch (err) {
    if (err && (err.name === 'NotFound' || err.$metadata?.httpStatusCode === 404)) {
      return false;
    }
    throw err;
  }
}

/**
 * Snapshot durável do Micro-CMS (landing + instructions) por config_key.
 * @returns {{ objectKey: string, publicUrl: string, updated_at: string }}
 */
async function putCmsSiteConfig(configKey, payload) {
  if (!isCmsS3Enabled()) {
    throw new Error('CMS_S3_BUCKET não configurado.');
  }
  const key = String(configKey || 'default').trim().toLowerCase() || 'default';
  const updatedAt = new Date().toISOString();
  const body = {
    config_key: key,
    landing_page_data: payload?.landing_page_data ?? {},
    instructions_data:
      payload?.instructions_data == null ? null : String(payload.instructions_data),
    updated_at: updatedAt,
    schema_version: 1,
  };
  const objectKey = buildSiteConfigObjectKey(key);
  await getS3Client().send(
    new PutObjectCommand({
      Bucket: getBucket(),
      Key: objectKey,
      Body: Buffer.from(JSON.stringify(body), 'utf8'),
      ContentType: 'application/json; charset=utf-8',
      CacheControl: 'no-cache',
    })
  );
  return {
    objectKey,
    publicUrl: getPublicUrlForKey(objectKey),
    updated_at: updatedAt,
  };
}

/**
 * Lê snapshot do site config no S3.
 * @returns {null | { config_key, landing_page_data, instructions_data, updated_at }}
 */
async function getCmsSiteConfig(configKey) {
  if (!isCmsS3Enabled()) {
    return null;
  }
  const key = String(configKey || 'default').trim().toLowerCase() || 'default';
  const objectKey = buildSiteConfigObjectKey(key);
  try {
    const resp = await getS3Client().send(
      new GetObjectCommand({
        Bucket: getBucket(),
        Key: objectKey,
      })
    );
    const buf = await streamToBuffer(resp.Body);
    const parsed = JSON.parse(buf.toString('utf8'));
    if (!parsed || typeof parsed !== 'object') return null;
    return {
      config_key: parsed.config_key || key,
      landing_page_data:
        parsed.landing_page_data && typeof parsed.landing_page_data === 'object'
          ? parsed.landing_page_data
          : {},
      instructions_data:
        parsed.instructions_data == null ? null : String(parsed.instructions_data),
      updated_at: parsed.updated_at || null,
    };
  } catch (err) {
    if (
      err &&
      (err.name === 'NoSuchKey' ||
        err.name === 'NotFound' ||
        err.$metadata?.httpStatusCode === 404)
    ) {
      return null;
    }
    throw err;
  }
}

module.exports = {
  isCmsS3Enabled,
  buildCmsFilename,
  buildObjectKey,
  buildSiteConfigObjectKey,
  getPublicUrlForFilename,
  getPublicUrlForKey,
  getCmsPersistedUrl,
  uploadCmsImage,
  cmsObjectExists,
  putCmsSiteConfig,
  getCmsSiteConfig,
};
