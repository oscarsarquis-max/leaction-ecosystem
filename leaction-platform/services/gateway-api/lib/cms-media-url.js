'use strict';

/**
 * URLs de mídia do Micro-CMS.
 * Nunca persistir localhost/127.0.0.1 — satélites leem o JSON em outra origem.
 */

const path = require('path');
const cmsS3 = require('./cms-s3-storage');

const MEDIA_KEYS = new Set(['image_url', 'image_path']);
const DEFAULT_S3_BUCKET = 'paneldx-cms-assets-2026';
const DEFAULT_S3_REGION = 'us-east-2';
const DEFAULT_S3_PREFIX = 'cms';

function isLoopbackHostname(hostname) {
  return /^(localhost|127\.0\.0\.1)$/i.test(String(hostname || '').trim());
}

function isLoopbackCmsUrl(raw) {
  const s = String(raw || '').trim();
  if (!s) return false;
  if (s.startsWith('/') && !s.startsWith('//')) return false;
  try {
    const u = new URL(s);
    return isLoopbackHostname(u.hostname);
  } catch {
    return /localhost|127\.0\.0\.1/i.test(s);
  }
}

function extractCmsImageFilename(raw) {
  const s = String(raw || '').trim();
  if (!s) return '';
  const fromPath = s.match(/\/images\/([^/?#]+)/i);
  if (fromPath) {
    return path.basename(fromPath[1]);
  }
  const fromS3 = s.match(/\/cms\/([^/?#]+)$/i);
  if (fromS3 && /\.(png|jpe?g|webp|gif)$/i.test(fromS3[1])) {
    return path.basename(fromS3[1]);
  }
  const base = path.basename(s.split('?')[0]);
  if (/^\d+-[a-zA-Z0-9._-]+\.(png|jpe?g|webp|gif)$/i.test(base)) {
    return base;
  }
  return '';
}

function s3PublicUrlForFilename(filename) {
  const safe = path.basename(String(filename || ''));
  if (!safe || safe.includes('..')) return '';
  if (cmsS3.isCmsS3Enabled()) {
    return cmsS3.getPublicUrlForFilename(safe);
  }
  const bucket = (process.env.CMS_S3_BUCKET || DEFAULT_S3_BUCKET).trim();
  const region = (
    process.env.CMS_S3_REGION ||
    process.env.AWS_REGION ||
    DEFAULT_S3_REGION
  ).trim();
  const prefix = (process.env.CMS_S3_PREFIX || DEFAULT_S3_PREFIX).trim().replace(/^\/+|\/+$/g, '');
  return `https://${bucket}.s3.${region}.amazonaws.com/${prefix}/${safe}`;
}

/**
 * Converte URL de loopback em URL pública S3.
 * Em produção (CMS_S3_BUCKET), `/images/arquivo` também vira URL S3.
 */
function canonicalizeCmsMediaUrl(raw) {
  const s = String(raw || '').trim();
  if (!s) return '';
  const filename = extractCmsImageFilename(s);
  const loopback = isLoopbackCmsUrl(s);
  if (loopback && !filename) return '';
  const relativeImage = Boolean(filename && /^\/images\//i.test(s));
  if (loopback || (cmsS3.isCmsS3Enabled() && relativeImage)) {
    return s3PublicUrlForFilename(filename);
  }
  return s;
}

function rewriteLandingMedia(value) {
  if (Array.isArray(value)) {
    return value.map(rewriteLandingMedia);
  }
  if (value && typeof value === 'object') {
    const out = {};
    for (const [key, child] of Object.entries(value)) {
      if (MEDIA_KEYS.has(key) && typeof child === 'string') {
        out[key] = canonicalizeCmsMediaUrl(child);
      } else {
        out[key] = rewriteLandingMedia(child);
      }
    }
    return out;
  }
  return value;
}

function pickUploadPersistUrl(result, preferPublicUrl) {
  const publicUrl = String(result?.public_url || '').trim();
  const relative = String(result?.url || '').trim();
  const ordered = preferPublicUrl ? [publicUrl, relative] : [relative, publicUrl];
  for (const candidate of ordered) {
    if (candidate && !isLoopbackCmsUrl(candidate)) return candidate;
  }
  if (publicUrl && isLoopbackCmsUrl(publicUrl)) {
    return canonicalizeCmsMediaUrl(publicUrl);
  }
  if (relative) return canonicalizeCmsMediaUrl(relative) || relative;
  return '';
}

module.exports = {
  isLoopbackCmsUrl,
  extractCmsImageFilename,
  canonicalizeCmsMediaUrl,
  rewriteLandingMedia,
  pickUploadPersistUrl,
  s3PublicUrlForFilename,
};
