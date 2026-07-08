'use strict';

const path = require('path');
const { S3Client, PutObjectCommand, HeadObjectCommand } = require('@aws-sdk/client-s3');

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
    const base = path.basename(originalName || 'upload', ext)
        .replace(/[^a-zA-Z0-9._-]/g, '_')
        .slice(0, 80) || 'upload';
    return `${Date.now()}-${base}${ext}`;
}

function buildObjectKey(filename) {
    const prefix = getPrefix();
    return prefix ? `${prefix}/${filename}` : filename;
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

/**
 * URL persistida no CMS — mantém /images/... para compatibilidade com o BFF
 * (fallback S3 em GET /images/:filename).
 */
function getCmsPersistedUrl(filename) {
    return `/images/${filename}`;
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

module.exports = {
    isCmsS3Enabled,
    buildCmsFilename,
    buildObjectKey,
    getPublicUrlForFilename,
    getPublicUrlForKey,
    getCmsPersistedUrl,
    uploadCmsImage,
    cmsObjectExists,
};
